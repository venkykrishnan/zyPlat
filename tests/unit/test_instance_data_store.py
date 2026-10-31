"""Unit tests for the local Parquet instance data store."""

import hashlib
from datetime import date
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from backend.app.core.exceptions import (
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)
from backend.app.storage.instance_data import (
    LocalParquetStore,
    build_snapshot_key,
    schema_hash,
    table_to_frame,
)
from backend.app.storage.instance_data import store as store_module

KEY = "domain-1/instance-1/snapshot-1.parquet"


@pytest.fixture
def store(tmp_path) -> LocalParquetStore:
    return LocalParquetStore(tmp_path / "root")


@pytest.fixture
def table() -> pa.Table:
    return pa.table(
        {
            "account": pa.array(["1000", "2000", "3000"], pa.string()),
            "amount": pa.array([Decimal("1.5"), Decimal("2"), None], pa.decimal128(38, 10)),
            "units": pa.array([1, None, 3], pa.int64()),
            "period": pa.array([date(2026, 1, 1)] * 3, pa.date32()),
        }
    )


def _leftover_temp_files(store_root) -> list:
    return [p for p in store_root.rglob("*") if p.name.endswith(".tmp")]


class TestWriteAndRead:
    """Round trips must preserve every value and type."""

    def test_write_then_read_returns_equal_table(self, store, table):
        """Storage must be lossless, including nulls and decimals."""
        info = store.write(KEY, table)

        assert store.read(info.uri).equals(table)

    def test_write_returns_pointer_facts(self, store, table, tmp_path):
        """The returned info becomes the snapshot's storage pointer."""
        info = store.write(KEY, table)
        on_disk = (tmp_path / "root" / KEY).read_bytes()

        assert info.uri == f"local://{KEY}"
        assert info.row_count == 3
        assert info.size_bytes == len(on_disk)
        assert info.checksum == hashlib.sha256(on_disk).hexdigest()
        assert info.schema_hash == schema_hash(table.schema)

    def test_read_projects_requested_columns_only(self, store, table):
        """Columnar reads must only load what the caller asks for."""
        info = store.write(KEY, table)

        result = store.read(info.uri, columns=["account", "units"])

        assert result.column_names == ["account", "units"]

    def test_read_applies_row_filters(self, store, table):
        """Filters let callers avoid loading unneeded rows."""
        info = store.write(KEY, table)

        result = store.read(info.uri, filters=[("account", "=", "2000")])

        assert result.column("account").to_pylist() == ["2000"]

    def test_write_creates_parent_directories(self, store, table, tmp_path):
        """Keys include directories that do not exist yet."""
        store.write("a/b/c/file.parquet", table)

        assert (tmp_path / "root" / "a" / "b" / "c" / "file.parquet").is_file()

    def test_uri_survives_moving_the_storage_root(self, tmp_path, table):
        """URIs are relative, so pointers in the database outlive a disk migration."""
        original = LocalParquetStore(tmp_path / "old")
        info = original.write(KEY, table)
        (tmp_path / "old").rename(tmp_path / "new")

        assert LocalParquetStore(tmp_path / "new").read(info.uri).equals(table)


class TestImmutability:
    """A snapshot's data can be written exactly once."""

    def test_second_write_to_same_key_raises_conflict(self, store, table):
        """Overwriting would silently change historical results."""
        store.write(KEY, table)

        with pytest.raises(ConflictError, match="immutable"):
            store.write(KEY, table)

    def test_conflicting_write_leaves_original_intact(self, store, table):
        """The losing writer must not corrupt the winner's file."""
        info = store.write(KEY, table)
        different = pa.table({"x": pa.array([1], pa.int64())})

        with pytest.raises(ConflictError):
            store.write(KEY, different)

        assert store.read(info.uri).equals(table)

    def test_conflicting_write_leaves_no_temp_files(self, store, table, tmp_path):
        """Failed writes must clean up after themselves."""
        store.write(KEY, table)

        with pytest.raises(ConflictError):
            store.write(KEY, table)

        assert _leftover_temp_files(tmp_path / "root") == []

    def test_failed_write_raises_infrastructure_error_and_cleans_up(
        self, store, table, tmp_path, monkeypatch
    ):
        """Disk errors surface as typed errors and leave nothing behind."""

        def explode(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(store_module.pq, "write_table", explode)

        with pytest.raises(InfrastructureError, match="disk full"):
            store.write(KEY, table)

        assert not (tmp_path / "root" / KEY).exists()
        assert _leftover_temp_files(tmp_path / "root") == []


class TestKeySafety:
    """Keys come from ids, but the store must not trust its callers."""

    @pytest.mark.parametrize(
        "key",
        ["", "../escape.parquet", "a/../../escape.parquet", "/etc/passwd", "a/.."],
    )
    def test_unsafe_keys_are_rejected(self, store, table, key):
        """Path traversal must never reach the filesystem."""
        with pytest.raises(ValidationError, match="Invalid storage key"):
            store.write(key, table)

    def test_symlink_escaping_the_root_is_rejected(self, store, table, tmp_path):
        """A symlink inside the root must not redirect writes outside it."""
        (tmp_path / "root").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (tmp_path / "root" / "link").symlink_to(outside, target_is_directory=True)

        with pytest.raises(ValidationError, match="escapes the storage root"):
            store.write("link/file.parquet", table)

        assert list(outside.iterdir()) == []


class TestReadErrors:
    """Read failures map to the typed exception taxonomy."""

    def test_missing_file_raises_not_found(self, store):
        """A pointer to a missing file is a not-found condition."""
        with pytest.raises(NotFoundError):
            store.read("local://does/not/exist.parquet")

    def test_foreign_uri_scheme_is_rejected(self, store):
        """A store must not guess how to read another backend's URI."""
        with pytest.raises(ValidationError, match="Unsupported storage URI"):
            store.read("s3://bucket/key.parquet")

    def test_unknown_column_raises_validation_error(self, store, table):
        """Asking for a column that is not in the file is a caller error."""
        info = store.write(KEY, table)

        with pytest.raises(ValidationError, match="Invalid columns or filters"):
            store.read(info.uri, columns=["nope"])

    def test_corrupt_file_raises_infrastructure_error(self, store, tmp_path):
        """Unreadable files are a storage problem, not a caller problem."""
        path = tmp_path / "root" / KEY
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a parquet file")

        with pytest.raises(InfrastructureError):
            store.read(f"local://{KEY}")


class TestDelete:
    """Deletion backs cleanup after failed commits."""

    def test_delete_removes_the_file(self, store, table, tmp_path):
        """The file must be gone afterwards."""
        info = store.write(KEY, table)

        store.delete(info.uri)

        assert not (tmp_path / "root" / KEY).exists()

    def test_delete_is_idempotent(self, store):
        """Cleanup may run twice; the second run must not fail."""
        store.delete(f"local://{KEY}")

    def test_deleted_key_can_be_written_again(self, store, table):
        """Cleanup after a failed commit must free the key for a retry."""
        info = store.write(KEY, table)
        store.delete(info.uri)

        assert store.write(KEY, table).row_count == 3


class TestFrameConversion:
    """Frames keep pyarrow-backed dtypes so types survive a round trip."""

    def test_nullable_integers_stay_integers(self, store, table):
        """NumPy dtypes would turn integers with nulls into floats."""
        frame = table_to_frame(store.read(store.write(KEY, table).uri))

        assert str(frame["units"].dtype) == "int64[pyarrow]"
        assert frame["units"].isna().tolist() == [False, True, False]

    def test_decimals_stay_decimals(self, store, table):
        """Monetary values must not degrade to floats or untyped objects."""
        frame = table_to_frame(store.read(store.write(KEY, table).uri))

        assert str(frame["amount"].dtype) == "decimal128(38, 10)[pyarrow]"
        assert frame["amount"].iloc[0] == Decimal("1.5")

    def test_dates_stay_dates(self, store, table):
        """Dates must not turn into timestamps."""
        frame = table_to_frame(store.read(store.write(KEY, table).uri))

        assert str(frame["period"].dtype) == "date32[day][pyarrow]"


class TestParquetFile:
    """The on-disk format is plain Parquet so other tools can read it."""

    def test_file_is_readable_by_plain_pyarrow(self, store, table, tmp_path):
        """Interoperability is the point of choosing Parquet."""
        store.write(KEY, table)

        assert pq.read_table(tmp_path / "root" / KEY).equals(table)

    def test_file_uses_zstd_compression(self, store, table, tmp_path):
        """Compression keeps long-lived snapshots small."""
        store.write(KEY, table)

        metadata = pq.ParquetFile(tmp_path / "root" / KEY).metadata
        assert metadata.row_group(0).column(0).compression == "ZSTD"


def test_build_snapshot_key_uses_ids_only():
    """Keys are derived from surrogate ids so renames never orphan files."""
    assert build_snapshot_key("d", "i", "s") == "d/i/s.parquet"
