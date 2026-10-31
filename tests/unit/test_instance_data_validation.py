"""Unit tests for write-time validation of instance data frames."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pytest

from backend.app.core.exceptions import ValidationError
from backend.app.models.domain import DomainDimensionDataType, DomainMetricDataType
from backend.app.storage.instance_data import ColumnKind, ColumnSpec, FrameSpec, validate_frame

D = ColumnKind.DIMENSION
M = ColumnKind.METRIC


@pytest.fixture
def spec() -> FrameSpec:
    """A spec touching every type that needs special handling."""
    dim = DomainDimensionDataType
    met = DomainMetricDataType
    return FrameSpec(
        "GL",
        (
            ColumnSpec("account", D, dim.STRING, True),
            ColumnSpec("period", D, dim.DATE, True),
            ColumnSpec("tags", D, dim.ARRAY_STRING, False),
            ColumnSpec("active", D, dim.BOOLEAN, False),
            ColumnSpec("seen_at", D, dim.DATETIME, False),
            ColumnSpec("amount", M, met.DECIMAL, True),
            ColumnSpec("units", M, met.INTEGER, False),
            ColumnSpec("ratio", M, met.NUMBER, False),
        ),
    )


@pytest.fixture
def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account": ["1000", "2000"],
            "period": [date(2026, 1, 1), date(2026, 2, 1)],
            "amount": [Decimal("10.50"), Decimal("-3.25")],
        }
    )


def _problems(error: pytest.ExceptionInfo[ValidationError]) -> str:
    return " | ".join(error.value.details)


class TestValidFrames:
    """Frames that satisfy the spec become Arrow tables in spec order."""

    def test_valid_frame_converts_to_spec_schema(self, spec, valid_frame):
        """The returned table must match the spec schema exactly, in spec column order."""
        table = validate_frame(valid_frame, spec)

        assert table.schema.equals(spec.arrow_schema())
        assert table.num_rows == 2
        assert table.column("amount").to_pylist() == [Decimal("10.5000000000"), Decimal("-3.25")]

    def test_missing_optional_columns_are_filled_with_nulls(self, spec, valid_frame):
        """Calculation engines may omit optional columns entirely."""
        table = validate_frame(valid_frame, spec)

        assert table.column("units").null_count == 2
        assert table.column("tags").null_count == 2

    def test_column_order_in_frame_does_not_matter(self, spec, valid_frame):
        """Output order follows the spec, not the caller's column order."""
        reordered = valid_frame[["amount", "period", "account"]]

        table = validate_frame(reordered, spec)

        assert table.schema.names == spec.names

    def test_dataframe_index_is_ignored(self, spec, valid_frame):
        """A leftover index must not become a column or break validation."""
        indexed = valid_frame.set_index(pd.Index([10, 20], name="row_id"))

        table = validate_frame(indexed, spec)

        assert "row_id" not in table.schema.names

    def test_empty_frame_with_required_columns_is_valid(self, spec, valid_frame):
        """An empty snapshot is legitimate, for example a period with no activity."""
        table = validate_frame(valid_frame.iloc[0:0], spec)

        assert table.num_rows == 0

    def test_pyarrow_backed_frame_is_accepted(self, spec):
        """Frames read back from storage can be written again without conversion."""
        frame = pd.DataFrame(
            {
                "account": pd.Series(["1000"], dtype=pd.ArrowDtype(pa.string())),
                "period": pd.Series([date(2026, 1, 1)], dtype=pd.ArrowDtype(pa.date32())),
                "amount": pd.Series([Decimal("1.5")], dtype=pd.ArrowDtype(pa.decimal128(38, 10))),
                "units": pd.Series([None], dtype=pd.ArrowDtype(pa.int64())),
            }
        )

        table = validate_frame(frame, spec)

        assert table.num_rows == 1

    def test_naive_datetime_is_interpreted_as_utc(self, spec, valid_frame):
        """Documented behavior: naive timestamps are treated as UTC."""
        valid_frame["seen_at"] = pd.to_datetime(["2026-01-01 10:00", "2026-01-02 11:30"])

        table = validate_frame(valid_frame, spec)

        first = table.column("seen_at").to_pylist()[0]
        assert first == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    def test_midnight_datetimes_are_accepted_for_date_columns(self, spec, valid_frame):
        """Pandas often stores dates as midnight datetimes; those lose nothing."""
        valid_frame["period"] = pd.to_datetime(["2026-01-01", "2026-02-01"])

        table = validate_frame(valid_frame, spec)

        assert table.column("period").to_pylist() == [date(2026, 1, 1), date(2026, 2, 1)]


class TestStructuralErrors:
    """Wrong columns are rejected before any value is looked at."""

    def test_non_dataframe_is_rejected(self, spec):
        """Passing a dict or list is a caller bug, reported clearly."""
        with pytest.raises(ValidationError, match="Expected a pandas DataFrame"):
            validate_frame({"account": ["1"]}, spec)  # type: ignore[arg-type]

    def test_missing_required_column_is_reported(self, spec, valid_frame):
        """The message must name the column the caller forgot."""
        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame.drop(columns=["amount"]), spec)

        assert "missing required columns ['amount']" in _problems(error)

    def test_unknown_column_is_reported(self, spec, valid_frame):
        """Typos must fail loudly instead of being silently dropped."""
        valid_frame["extra"] = 1

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "unknown columns ['extra']" in _problems(error)

    def test_duplicate_columns_are_reported(self, spec, valid_frame):
        """Duplicate names make column lookup ambiguous."""
        duplicated = pd.concat([valid_frame, valid_frame[["account"]]], axis=1)

        with pytest.raises(ValidationError) as error:
            validate_frame(duplicated, spec)

        assert "duplicate columns: ['account']" in _problems(error)

    def test_error_names_the_domain(self, spec, valid_frame):
        """Operators need to know which domain rejected the frame."""
        with pytest.raises(ValidationError, match="domain 'GL'"):
            validate_frame(valid_frame.drop(columns=["account"]), spec)


class TestValueErrors:
    """Values must convert losslessly to the declared type."""

    def test_null_in_required_column_is_reported_with_count(self, spec, valid_frame):
        """Required columns may not contain nulls."""
        valid_frame.loc[0, "account"] = None

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "column 'account' is required but has 1 nulls" in _problems(error)

    def test_string_in_numeric_column_is_rejected(self, spec, valid_frame):
        """No implicit string-to-number coercion."""
        valid_frame["ratio"] = ["high", "low"]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "column 'ratio' (NUMBER)" in _problems(error)

    def test_lossy_float_to_integer_is_rejected(self, spec, valid_frame):
        """1.5 must not silently become 1."""
        valid_frame["units"] = [1.5, 2.0]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "column 'units' (INTEGER)" in _problems(error)

    def test_integral_floats_are_accepted_for_integer_columns(self, spec, valid_frame):
        """Pandas upcasts integers with nulls to float; integral values are safe to store."""
        valid_frame["units"] = [1.0, float("nan")]

        table = validate_frame(valid_frame, spec)

        assert table.column("units").to_pylist() == [1, None]

    def test_float_in_decimal_column_is_rejected_with_hint(self, spec, valid_frame):
        """Floats would reintroduce binary rounding into monetary values."""
        valid_frame["amount"] = [10.5, -3.25]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "use decimal.Decimal values" in _problems(error)

    def test_decimal_with_too_many_places_is_rejected(self, spec, valid_frame):
        """Rescaling would silently drop digits."""
        valid_frame["amount"] = [Decimal("1.12345678901"), Decimal("2")]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "at most 10 decimal places" in _problems(error)

    def test_integers_in_boolean_column_are_rejected(self, spec, valid_frame):
        """Arrow would accept 0/1 as booleans; a stray 2 would be a data bug."""
        valid_frame["active"] = [1, 0]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "column 'active' (BOOLEAN) must contain booleans" in _problems(error)

    def test_datetime_with_time_of_day_in_date_column_is_rejected(self, spec, valid_frame):
        """Arrow would silently truncate the time of day."""
        valid_frame["period"] = pd.to_datetime(["2026-01-01 10:00", "2026-02-01 00:00"])

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert "contains datetimes with a time of day" in _problems(error)

    def test_all_problems_are_reported_together(self, spec, valid_frame):
        """One round trip should reveal every issue, not just the first."""
        valid_frame["ratio"] = ["high", "low"]
        valid_frame["units"] = [1.5, 2.0]
        valid_frame.loc[0, "account"] = None

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec)

        assert len(error.value.details) == 3


class TestTaxonomyValues:
    """Taxonomy-bound dimensions may only contain values the taxonomy allows."""

    def test_disallowed_values_are_reported(self, spec, valid_frame):
        """The message lists offending values so they can be fixed."""
        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec, allowed_values={"account": {"1000"}})

        assert "dimension 'account' has values not in its taxonomy: ['2000']" in _problems(error)

    def test_allowed_values_pass(self, spec, valid_frame):
        """A frame within the taxonomy is accepted."""
        table = validate_frame(valid_frame, spec, allowed_values={"account": {"1000", "2000"}})

        assert table.num_rows == 2

    def test_nulls_are_not_treated_as_disallowed_values(self, spec, valid_frame):
        """Null handling belongs to the required check, not the taxonomy check."""
        valid_frame["tags"] = [None, ["a"]]

        table = validate_frame(valid_frame, spec, allowed_values={"tags": {"a"}})

        assert table.num_rows == 2

    def test_array_dimension_values_are_checked_individually(self, spec, valid_frame):
        """Each element of an array dimension must be in the taxonomy."""
        valid_frame["tags"] = [["a", "b"], ["a", "zzz"]]

        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec, allowed_values={"tags": {"a", "b"}})

        assert "['zzz']" in _problems(error)

    def test_reported_values_are_capped(self, spec):
        """A huge bad frame must not produce a huge error message."""
        frame = pd.DataFrame(
            {
                "account": [f"bad-{i}" for i in range(20)],
                "period": [date(2026, 1, 1)] * 20,
                "amount": [Decimal("1")] * 20,
            }
        )

        with pytest.raises(ValidationError) as error:
            validate_frame(frame, spec, allowed_values={"account": {"ok"}})

        assert "(and 15 more)" in _problems(error)

    def test_allowed_values_for_unknown_column_are_rejected(self, spec, valid_frame):
        """A typo in the constraint must not silently disable the check."""
        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec, allowed_values={"acount": {"1000"}})

        assert "'acount', which is not a dimension" in _problems(error)

    def test_allowed_values_for_metric_are_rejected(self, spec, valid_frame):
        """Only dimensions are taxonomy-bound."""
        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec, allowed_values={"amount": {"1"}})

        assert "'amount', which is not a dimension" in _problems(error)

    def test_non_string_dimension_cannot_be_taxonomy_bound(self, spec, valid_frame):
        """Taxonomy entity ids are strings; other types cannot be checked."""
        with pytest.raises(ValidationError) as error:
            validate_frame(valid_frame, spec, allowed_values={"period": {"2026-01-01"}})

        assert "taxonomy values must be strings" in _problems(error)

    def test_absent_optional_dimension_skips_taxonomy_check(self, spec, valid_frame):
        """An omitted optional column has no values to check."""
        table = validate_frame(valid_frame, spec, allowed_values={"tags": {"a"}})

        assert table.num_rows == 2
