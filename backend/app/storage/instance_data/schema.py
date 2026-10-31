"""Column specifications and Arrow schemas for time-series domain instance data.

A domain definition (dimensions and metrics) is turned into a ``FrameSpec``, which fixes the
column order, required-ness, and Arrow types of the Parquet file for every snapshot.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import pyarrow as pa

from ...models.domain import DomainDimensionDataType, DomainMetricDataType

if TYPE_CHECKING:
    from ...models.domain import DomainDefinition

# Decimal128 holds at most 38 digits; scale 10 leaves 28 integer digits for monetary amounts.
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 10

_DIMENSION_ARROW_TYPES: dict[DomainDimensionDataType, pa.DataType] = {
    DomainDimensionDataType.STRING: pa.string(),
    DomainDimensionDataType.NUMBER: pa.float64(),
    DomainDimensionDataType.INTEGER: pa.int64(),
    DomainDimensionDataType.BOOLEAN: pa.bool_(),
    DomainDimensionDataType.DATE: pa.date32(),
    DomainDimensionDataType.DATETIME: pa.timestamp("us", tz="UTC"),
    DomainDimensionDataType.ENUM: pa.string(),
    DomainDimensionDataType.ARRAY_STRING: pa.list_(pa.string()),
}

_METRIC_ARROW_TYPES: dict[DomainMetricDataType, pa.DataType] = {
    DomainMetricDataType.NUMBER: pa.float64(),
    DomainMetricDataType.INTEGER: pa.int64(),
    DomainMetricDataType.DECIMAL: pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE),
}


class ColumnKind(str, Enum):
    DIMENSION = "DIMENSION"
    METRIC = "METRIC"


@dataclass(frozen=True)
class ColumnSpec:
    """One column of an instance data frame."""

    name: str
    kind: ColumnKind
    data_type: DomainDimensionDataType | DomainMetricDataType
    required: bool

    @property
    def arrow_type(self) -> pa.DataType:
        if self.kind is ColumnKind.DIMENSION:
            return _DIMENSION_ARROW_TYPES[DomainDimensionDataType(self.data_type)]
        return _METRIC_ARROW_TYPES[DomainMetricDataType(self.data_type)]

    @property
    def arrow_field(self) -> pa.Field:
        return pa.field(self.name, self.arrow_type, nullable=not self.required)


@dataclass(frozen=True)
class FrameSpec:
    """Ordered column specification: dimensions first, then metrics, each by ordinal."""

    domain_id: str
    columns: tuple[ColumnSpec, ...]

    @classmethod
    def from_domain(cls, definition: DomainDefinition) -> FrameSpec:
        """Build a spec from a domain definition and its loaded dimensions and metrics."""
        dimensions = sorted(definition.dimensions, key=lambda d: d.ordinal)
        metrics = sorted(definition.metrics, key=lambda m: m.ordinal)
        columns = [
            ColumnSpec(d.name, ColumnKind.DIMENSION, d.data_type, bool(d.required))
            for d in dimensions
        ] + [ColumnSpec(m.name, ColumnKind.METRIC, m.data_type, bool(m.required)) for m in metrics]
        return cls(domain_id=str(definition.domain_id), columns=tuple(columns))

    @property
    def names(self) -> list[str]:
        return [column.name for column in self.columns]

    def column(self, name: str) -> ColumnSpec | None:
        return next((column for column in self.columns if column.name == name), None)

    def arrow_schema(self) -> pa.Schema:
        return pa.schema([column.arrow_field for column in self.columns])


def schema_hash(schema: pa.Schema) -> str:
    """Return a stable SHA-256 fingerprint of column names, order, types, and nullability.

    Stored with each snapshot so readers can tell which definition version wrote a file.

    Example:
        >>> schema_hash(pa.schema([pa.field("a", pa.int64())])) == schema_hash(
        ...     pa.schema([pa.field("a", pa.int64())])
        ... )
        True
    """
    fields: Iterable[list[object]] = (
        [field.name, str(field.type), field.nullable] for field in schema
    )
    payload = json.dumps(list(fields), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
