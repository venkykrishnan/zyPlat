"""Integration tests for InstanceDataService: Postgres pointer plus Parquet file."""

import logging
import uuid
from decimal import Decimal

import pytest

from backend.app.core.exceptions import (
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)
from backend.app.models.domain import DomainKind
from backend.app.services.instance_data import InstanceDataService, SnapshotWriteOptions
from backend.app.storage.instance_data import LocalParquetStore


@pytest.fixture
def store(tmp_path) -> LocalParquetStore:
    return LocalParquetStore(tmp_path / "data")


@pytest.fixture
def service(store) -> InstanceDataService:
    return InstanceDataService(store)


class TestWriteSnapshotFrame:
    """Writing stores the file and records its pointer on the snapshot."""

    def test_write_populates_storage_pointer(self, service, snapshot_factory, db_session, gl_frame):
        """The snapshot row must describe the file that was written."""
        snapshot = snapshot_factory()

        result = service.write_snapshot_frame(
            db_session, snapshot.id, gl_frame, SnapshotWriteOptions(calc_run_id="run-7")
        )

        assert result.storage_uri.startswith("local://")
        assert result.row_count == 2
        assert len(result.schema_hash) == 64
        assert len(result.checksum) == 64
        assert result.calc_run_id == "run-7"

    def test_key_is_built_from_ids(self, service, snapshot_factory, db_session, gl_frame):
        """Ids, not names, keep files valid when definitions are renamed."""
        snapshot = snapshot_factory()

        result = service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        instance_id = str(snapshot.domain_instance_id)
        assert instance_id in result.storage_uri
        assert result.storage_uri.endswith(f"{snapshot.id}.parquet")

    def test_round_trip_preserves_values_and_types(
        self, service, snapshot_factory, db_session, gl_frame
    ):
        """Data read back must equal what was written, with exact decimals and nullable ints."""
        snapshot = snapshot_factory()
        service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        frame = service.read_snapshot_frame(db_session, snapshot.id)

        assert frame["account"].tolist() == ["1000", "2000"]
        assert frame["amount"].tolist() == [Decimal("10.5"), Decimal("-3.25")]
        assert frame["units"].isna().tolist() == [False, True]
        assert str(frame["units"].dtype) == "int64[pyarrow]"

    def test_second_write_to_same_snapshot_is_a_conflict(
        self, service, snapshot_factory, db_session, gl_frame
    ):
        """Corrections require a new snapshot, so history stays reproducible."""
        snapshot = snapshot_factory()
        service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        with pytest.raises(ConflictError, match="create a new snapshot"):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

    def test_unknown_snapshot_raises_not_found(self, service, db_session, gl_frame):
        """Writing to a missing snapshot is a not-found condition."""
        with pytest.raises(NotFoundError):
            service.write_snapshot_frame(db_session, uuid.uuid4(), gl_frame)

    def test_scalar_domain_is_rejected(self, service, snapshot_factory, db_session, gl_frame):
        """Only TIME_SERIES domains store data as files."""
        snapshot = snapshot_factory(kind=DomainKind.SCALAR)

        with pytest.raises(ValidationError, match="only TIME_SERIES"):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

    def test_invalid_frame_is_rejected_without_writing_a_file(
        self, service, snapshot_factory, db_session, gl_frame, tmp_path
    ):
        """Validation must happen before anything touches the disk."""
        snapshot = snapshot_factory()

        with pytest.raises(ValidationError):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame.drop(columns=["amount"]))

        assert (
            not (tmp_path / "data").exists() or list((tmp_path / "data").rglob("*.parquet")) == []
        )
        assert snapshot.storage_uri is None

    def test_taxonomy_values_are_enforced(self, service, snapshot_factory, db_session, gl_frame):
        """Allowed values supplied by the caller restrict dimension contents."""
        snapshot = snapshot_factory()
        options = SnapshotWriteOptions(allowed_values={"account": {"1000"}})

        with pytest.raises(ValidationError, match="not in its taxonomy"):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame, options)

    def test_write_logs_structured_fields(
        self, service, snapshot_factory, db_session, gl_frame, caplog
    ):
        """Logs must carry the identifiers operators search by."""
        snapshot = snapshot_factory()

        with caplog.at_level(logging.INFO, logger="backend.app.services.instance_data"):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        record = next(r for r in caplog.records if r.getMessage().startswith("Stored instance"))
        assert record.operation == "write_snapshot_frame"
        assert record.snapshot_id == str(snapshot.id)
        assert record.row_count == 2


class TestCommitFailure:
    """A failed commit must not leave a file that no snapshot points to."""

    def test_file_is_removed_when_commit_fails(
        self, service, snapshot_factory, db_session, gl_frame, tmp_path, monkeypatch
    ):
        """Otherwise the key would be blocked forever by an orphan."""
        snapshot = snapshot_factory()
        snapshot_id = snapshot.id

        def failing_commit():
            raise RuntimeError("commit failed")

        monkeypatch.setattr(db_session, "commit", failing_commit)

        with pytest.raises(RuntimeError, match="commit failed"):
            service.write_snapshot_frame(db_session, snapshot_id, gl_frame)

        assert list((tmp_path / "data").rglob("*.parquet")) == []

    def test_cleanup_failure_does_not_mask_original_error(
        self, snapshot_factory, db_session, gl_frame, store, monkeypatch
    ):
        """The root cause is the commit failure, not the cleanup failure."""
        service = InstanceDataService(store)
        snapshot = snapshot_factory()

        def failing_commit():
            raise RuntimeError("commit failed")

        def failing_delete(uri):
            raise InfrastructureError("cannot delete")

        monkeypatch.setattr(db_session, "commit", failing_commit)
        monkeypatch.setattr(store, "delete", failing_delete)

        with pytest.raises(RuntimeError, match="commit failed"):
            service.write_snapshot_frame(db_session, snapshot.id, gl_frame)


class TestReadSnapshotFrame:
    """Reads go through the pointer and support column projection and filters."""

    def test_snapshot_without_data_raises_not_found(self, service, snapshot_factory, db_session):
        """A snapshot that was never populated has nothing to read."""
        snapshot = snapshot_factory()

        with pytest.raises(NotFoundError, match="no stored instance data"):
            service.read_snapshot_frame(db_session, snapshot.id)

    def test_unknown_snapshot_raises_not_found(self, service, db_session):
        """Reading a missing snapshot is a not-found condition."""
        with pytest.raises(NotFoundError, match="not found"):
            service.read_snapshot_frame(db_session, uuid.uuid4())

    def test_column_projection(self, service, snapshot_factory, db_session, gl_frame):
        """Callers can load only the columns they need."""
        snapshot = snapshot_factory()
        service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        frame = service.read_snapshot_frame(db_session, snapshot.id, columns=["account", "amount"])

        assert list(frame.columns) == ["account", "amount"]

    def test_row_filters(self, service, snapshot_factory, db_session, gl_frame):
        """Filters are pushed down to Parquet."""
        snapshot = snapshot_factory()
        service.write_snapshot_frame(db_session, snapshot.id, gl_frame)

        frame = service.read_snapshot_frame(
            db_session, snapshot.id, filters=[("account", "=", "2000")]
        )

        assert frame["account"].tolist() == ["2000"]

    def test_missing_file_behind_pointer_raises_not_found(
        self, service, snapshot_factory, db_session, gl_frame, tmp_path
    ):
        """A dangling pointer is reported, not hidden."""
        snapshot = snapshot_factory()
        service.write_snapshot_frame(db_session, snapshot.id, gl_frame)
        for file in (tmp_path / "data").rglob("*.parquet"):
            file.unlink()

        with pytest.raises(NotFoundError):
            service.read_snapshot_frame(db_session, snapshot.id)
