"""Write-time validation of instance data frames against a domain definition.

Validation lives here, not in the database, because the data is stored as Parquet files and no
longer subject to table constraints. Conversion to Arrow is strict (``safe=True``): lossy casts
such as ``1.5 -> int64`` or ``Decimal`` values that need more than the allowed scale are rejected.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import TypeAlias

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ...core.exceptions import ValidationError
from ...models.domain import DomainDimensionDataType
from .schema import DECIMAL_SCALE, ColumnKind, ColumnSpec, FrameSpec

MAX_REPORTED_VALUES = 5

_CONVERSION_ERRORS = (
    pa.ArrowInvalid,
    pa.ArrowTypeError,
    pa.ArrowNotImplementedError,
    TypeError,
    ValueError,
    OverflowError,
)

# Explicit alias: pyarrow has no stubs, so mypy would otherwise treat this as a plain variable.
ArrowColumn: TypeAlias = pa.Array | pa.ChunkedArray


def validate_frame(
    frame: pd.DataFrame,
    spec: FrameSpec,
    *,
    allowed_values: Mapping[str, Collection[str]] | None = None,
) -> pa.Table:
    """Validate ``frame`` against ``spec`` and return it as an Arrow table in spec order.

    The DataFrame index is ignored. Optional columns missing from the frame are filled with
    nulls. Timezone-naive datetimes are interpreted as UTC.

    Args:
        frame: Candidate instance data.
        spec: Column specification derived from the domain definition.
        allowed_values: Optional mapping of dimension name to the values its taxonomy allows.

    Returns:
        Arrow table whose schema equals ``spec.arrow_schema()``.

    Raises:
        ValidationError: If any column is missing, unknown, mistyped, or has disallowed nulls
            or values. ``details`` lists every problem found.
    """
    if not isinstance(frame, pd.DataFrame):
        raise ValidationError(f"Expected a pandas DataFrame, got {type(frame).__name__}.")

    problems = _structural_problems(frame, spec)
    if problems:
        raise _validation_error(spec, problems)

    arrays, problems = _convert_columns(frame, spec)
    if allowed_values:
        problems += _taxonomy_problems(arrays, spec, allowed_values)
    if problems:
        raise _validation_error(spec, problems)

    return pa.Table.from_arrays([arrays[name] for name in spec.names], schema=spec.arrow_schema())


def _validation_error(spec: FrameSpec, problems: list[str]) -> ValidationError:
    summary = f"Frame does not match domain '{spec.domain_id}': " + "; ".join(problems)
    return ValidationError(summary, details=problems)


def _structural_problems(frame: pd.DataFrame, spec: FrameSpec) -> list[str]:
    problems: list[str] = []
    if not frame.columns.is_unique:
        duplicates = sorted({str(c) for c in frame.columns[frame.columns.duplicated()]})
        problems.append(f"duplicate columns: {duplicates}")

    provided = {str(column) for column in frame.columns}
    unknown = sorted(provided - set(spec.names))
    if unknown:
        problems.append(f"unknown columns {unknown}; expected a subset of {spec.names}")

    missing = [c.name for c in spec.columns if c.required and c.name not in provided]
    if missing:
        problems.append(f"missing required columns {missing}")
    return problems


def _convert_columns(
    frame: pd.DataFrame, spec: FrameSpec
) -> tuple[dict[str, ArrowColumn], list[str]]:
    arrays: dict[str, ArrowColumn] = {}
    problems: list[str] = []
    for column in spec.columns:
        if column.name not in frame.columns:
            arrays[column.name] = pa.nulls(len(frame), type=column.arrow_type)
            continue
        try:
            array = _convert_column(frame[column.name], column)
        except ValueError as error:
            problems.append(str(error))
            continue
        if column.required and array.null_count:
            problems.append(f"column '{column.name}' is required but has {array.null_count} nulls")
        arrays[column.name] = array
    return arrays, problems


def _convert_column(series: pd.Series, column: ColumnSpec) -> ArrowColumn:
    """Convert one column strictly, raising ``ValueError`` with a column-specific message."""
    _reject_lossy_inputs(series, column)
    try:
        return pa.array(series, type=column.arrow_type, from_pandas=True)
    except _CONVERSION_ERRORS as error:
        raise ValueError(_conversion_message(column, error)) from error


def _reject_lossy_inputs(series: pd.Series, column: ColumnSpec) -> None:
    """Reject inputs that Arrow would convert silently but lossily.

    Arrow accepts ``int -> bool`` and ``datetime -> date32`` (dropping the time of day) even
    in safe mode, so those cases are checked on the naturally inferred type.
    """
    data_type = column.data_type
    if column.kind is not ColumnKind.DIMENSION or data_type not in (
        DomainDimensionDataType.BOOLEAN,
        DomainDimensionDataType.DATE,
    ):
        return

    try:
        inferred = pa.array(series, from_pandas=True)
    except _CONVERSION_ERRORS:
        return  # The typed conversion reports the real error with better context.
    if inferred.null_count == len(inferred):
        return

    if data_type is DomainDimensionDataType.BOOLEAN and not pa.types.is_boolean(inferred.type):
        raise ValueError(
            f"column '{column.name}' (BOOLEAN) must contain booleans, got {inferred.type}"
        )
    if (
        data_type is DomainDimensionDataType.DATE
        and pa.types.is_timestamp(inferred.type)
        and not pc.all(pc.equal(pc.floor_temporal(inferred, unit="day"), inferred)).as_py()
    ):
        raise ValueError(
            f"column '{column.name}' (DATE) contains datetimes with a time of day; "
            "convert them to dates first"
        )


def _conversion_message(column: ColumnSpec, error: Exception) -> str:
    base = (
        f"column '{column.name}' ({column.data_type.value}) cannot be stored as {column.arrow_type}"
    )
    if pa.types.is_decimal(column.arrow_type):
        return (
            f"{base}: use decimal.Decimal values with at most {DECIMAL_SCALE} decimal places "
            f"({error})"
        )
    return f"{base}: {error}"


def _taxonomy_problems(
    arrays: Mapping[str, ArrowColumn],
    spec: FrameSpec,
    allowed_values: Mapping[str, Collection[str]],
) -> list[str]:
    problems: list[str] = []
    for name, allowed in allowed_values.items():
        column = spec.column(name)
        if column is None or column.kind is not ColumnKind.DIMENSION:
            problems.append(f"allowed values given for '{name}', which is not a dimension")
            continue
        if name not in arrays:
            continue
        problem = _disallowed_values_problem(name, arrays[name], allowed)
        if problem:
            problems.append(problem)
    return problems


def _disallowed_values_problem(
    name: str, array: ArrowColumn, allowed: Collection[str]
) -> str | None:
    values: ArrowColumn = array
    if pa.types.is_list(array.type):
        values = pc.list_flatten(array)
    if not pa.types.is_string(values.type):
        return f"dimension '{name}' has type {array.type}; taxonomy values must be strings"

    candidates = values.drop_null()
    in_taxonomy = pc.is_in(candidates, value_set=pa.array(sorted(allowed), type=pa.string()))
    disallowed = pc.unique(pc.filter(candidates, pc.invert(in_taxonomy))).to_pylist()
    if not disallowed:
        return None
    shown = sorted(disallowed)[:MAX_REPORTED_VALUES]
    more = len(disallowed) - len(shown)
    suffix = f" (and {more} more)" if more > 0 else ""
    return f"dimension '{name}' has values not in its taxonomy: {shown}{suffix}"
