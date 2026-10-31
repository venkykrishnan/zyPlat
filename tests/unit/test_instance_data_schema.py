"""Unit tests for instance data column specs, Arrow schemas, and schema hashing."""

import pyarrow as pa
import pytest

from backend.app.models.domain import (
    DomainDefinition,
    DomainDimension,
    DomainDimensionDataType,
    DomainKind,
    DomainMetric,
    DomainMetricDataType,
)
from backend.app.models.taxonomy import DefinitionScope
from backend.app.storage.instance_data import ColumnKind, ColumnSpec, FrameSpec, schema_hash
from backend.app.storage.instance_data.schema import DECIMAL_PRECISION, DECIMAL_SCALE


def _dimension(name, data_type, required, ordinal):
    return DomainDimension(
        name=name, display_name=name, data_type=data_type, required=required, ordinal=ordinal
    )


def _metric(name, data_type, required, ordinal):
    return DomainMetric(
        name=name, display_name=name, data_type=data_type, required=required, ordinal=ordinal
    )


class TestArrowTypeMapping:
    """Each domain data type maps to one fixed Arrow type, so dtypes survive storage."""

    @pytest.mark.parametrize(
        ("data_type", "expected"),
        [
            (DomainDimensionDataType.STRING, pa.string()),
            (DomainDimensionDataType.NUMBER, pa.float64()),
            (DomainDimensionDataType.INTEGER, pa.int64()),
            (DomainDimensionDataType.BOOLEAN, pa.bool_()),
            (DomainDimensionDataType.DATE, pa.date32()),
            (DomainDimensionDataType.DATETIME, pa.timestamp("us", tz="UTC")),
            (DomainDimensionDataType.ENUM, pa.string()),
            (DomainDimensionDataType.ARRAY_STRING, pa.list_(pa.string())),
        ],
    )
    def test_dimension_type_maps_to_arrow_type(self, data_type, expected):
        """Every dimension data type must have an Arrow mapping."""
        column = ColumnSpec("c", ColumnKind.DIMENSION, data_type, required=False)

        assert column.arrow_type == expected

    @pytest.mark.parametrize(
        ("data_type", "expected"),
        [
            (DomainMetricDataType.NUMBER, pa.float64()),
            (DomainMetricDataType.INTEGER, pa.int64()),
            (DomainMetricDataType.DECIMAL, pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE)),
        ],
    )
    def test_metric_type_maps_to_arrow_type(self, data_type, expected):
        """Every metric data type must have an Arrow mapping."""
        column = ColumnSpec("m", ColumnKind.METRIC, data_type, required=False)

        assert column.arrow_type == expected

    def test_required_column_is_not_nullable(self):
        """Required-ness is recorded in the file schema, not only checked at write time."""
        required = ColumnSpec("a", ColumnKind.METRIC, DomainMetricDataType.NUMBER, True)
        optional = ColumnSpec("b", ColumnKind.METRIC, DomainMetricDataType.NUMBER, False)

        assert required.arrow_field.nullable is False
        assert optional.arrow_field.nullable is True


class TestFrameSpecFromDomain:
    """A FrameSpec fixes column order: dimensions then metrics, each by ordinal."""

    def test_orders_dimensions_then_metrics_by_ordinal(self):
        """Declaration order must not affect the stored column order."""
        definition = DomainDefinition(
            domain_id="GL",
            description="General ledger",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
            dimensions=[
                _dimension("period", DomainDimensionDataType.DATE, True, 2),
                _dimension("account", DomainDimensionDataType.STRING, True, 1),
            ],
            metrics=[
                _metric("units", DomainMetricDataType.INTEGER, False, 2),
                _metric("amount", DomainMetricDataType.DECIMAL, True, 1),
            ],
        )

        spec = FrameSpec.from_domain(definition)

        assert spec.domain_id == "GL"
        assert spec.names == ["account", "period", "amount", "units"]
        assert [c.kind for c in spec.columns] == [
            ColumnKind.DIMENSION,
            ColumnKind.DIMENSION,
            ColumnKind.METRIC,
            ColumnKind.METRIC,
        ]

    def test_treats_unset_required_flag_as_optional(self):
        """The ORM leaves ``required`` unset until flush; that must read as not required."""
        definition = DomainDefinition(
            domain_id="GL",
            description="d",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
            dimensions=[
                DomainDimension(
                    name="a",
                    display_name="a",
                    data_type=DomainDimensionDataType.STRING,
                    ordinal=1,
                )
            ],
            metrics=[],
        )

        assert FrameSpec.from_domain(definition).columns[0].required is False

    def test_arrow_schema_follows_column_order(self):
        """The Parquet schema must list columns in spec order."""
        spec = FrameSpec(
            "GL",
            (
                ColumnSpec("a", ColumnKind.DIMENSION, DomainDimensionDataType.STRING, True),
                ColumnSpec("m", ColumnKind.METRIC, DomainMetricDataType.INTEGER, False),
            ),
        )

        schema = spec.arrow_schema()

        assert schema.names == ["a", "m"]
        assert schema.field("a").nullable is False
        assert schema.field("m").type == pa.int64()

    def test_column_lookup_returns_none_for_unknown_name(self):
        """Lookup is used to guard against typos in taxonomy constraints."""
        spec = FrameSpec("GL", ())

        assert spec.column("missing") is None


class TestSchemaHash:
    """The hash tells readers which definition version wrote a file."""

    @staticmethod
    def _schema(name="a", type_=pa.int64(), nullable=True):
        return pa.schema([pa.field(name, type_, nullable=nullable)])

    def test_equal_schemas_hash_equal(self):
        """Hashes must be deterministic across processes and runs."""
        assert schema_hash(self._schema()) == schema_hash(self._schema())

    def test_hash_is_sha256_hex(self):
        """Pointer columns are sized for a 64-character hex digest."""
        assert len(schema_hash(self._schema())) == 64

    @pytest.mark.parametrize(
        "changed",
        [
            {"name": "b"},
            {"type_": pa.float64()},
            {"nullable": False},
        ],
    )
    def test_any_field_change_changes_hash(self, changed):
        """Name, type, and nullability are all part of a file's contract."""
        assert schema_hash(self._schema()) != schema_hash(self._schema(**changed))

    def test_column_order_changes_hash(self):
        """Column order is part of the contract because files are positional."""
        ab = pa.schema([pa.field("a", pa.int64()), pa.field("b", pa.int64())])
        ba = pa.schema([pa.field("b", pa.int64()), pa.field("a", pa.int64())])

        assert schema_hash(ab) != schema_hash(ba)
