"""Database constraint tests for the snapshot storage pointer columns."""

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.domain import DomainInstanceSnapshot

POINTER = {
    "storage_uri": "local://d/i/s.parquet",
    "row_count": 2,
    "schema_hash": "a" * 64,
    "checksum": "b" * 64,
}


def _set(snapshot, **values):
    for name, value in values.items():
        setattr(snapshot, name, value)


class TestSnapshotIdentity:
    """A domain instance has one snapshot per company snapshot."""

    def test_duplicate_snapshot_for_company_snapshot_is_rejected(
        self, snapshot_factory, db_session
    ):
        """Two snapshots for the same (instance, company snapshot) would be ambiguous."""
        existing = snapshot_factory()
        duplicate = DomainInstanceSnapshot(
            domain_instance_id=existing.domain_instance_id,
            company_snapshot_id=existing.company_snapshot_id,
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError, match="uq_domain_instance_company_snapshot"):
            db_session.flush()

    def test_snapshot_requires_a_company_snapshot(self, snapshot_factory, db_session):
        """Every domain instance snapshot belongs to a company snapshot."""
        existing = snapshot_factory()
        orphan = DomainInstanceSnapshot(domain_instance_id=existing.domain_instance_id)
        db_session.add(orphan)

        with pytest.raises(IntegrityError, match="company_snapshot_id"):
            db_session.flush()


class TestStoragePointer:
    """A snapshot either has a complete storage pointer or none at all."""

    def test_new_snapshot_has_no_pointer(self, snapshot_factory):
        """Snapshots exist before their data is written."""
        snapshot = snapshot_factory()

        assert snapshot.storage_uri is None
        assert snapshot.row_count is None

    def test_complete_pointer_is_accepted(self, snapshot_factory, db_session):
        """All pointer columns set together is the normal state after a write."""
        snapshot = snapshot_factory()

        _set(snapshot, **POINTER, calc_run_id="run-1")
        db_session.flush()

        assert snapshot.calc_run_id == "run-1"

    @pytest.mark.parametrize("missing", ["storage_uri", "row_count", "schema_hash", "checksum"])
    def test_partial_pointer_is_rejected(self, snapshot_factory, db_session, missing):
        """A half-written pointer would make a snapshot unreadable and unverifiable."""
        snapshot = snapshot_factory()
        _set(snapshot, **{k: v for k, v in POINTER.items() if k != missing})

        with pytest.raises(IntegrityError, match="storage_pointer_complete"):
            db_session.flush()

    def test_negative_row_count_is_rejected(self, snapshot_factory, db_session):
        """Row counts cannot be negative."""
        snapshot = snapshot_factory()
        _set(snapshot, **{**POINTER, "row_count": -1})

        with pytest.raises(IntegrityError, match="row_count_non_negative"):
            db_session.flush()

    def test_zero_row_count_is_accepted(self, snapshot_factory, db_session):
        """An empty snapshot is valid."""
        snapshot = snapshot_factory()

        _set(snapshot, **{**POINTER, "row_count": 0})
        db_session.flush()

        assert snapshot.row_count == 0

    def test_two_snapshots_cannot_share_a_file(self, snapshot_factory, db_session):
        """Sharing a file would let one snapshot's cleanup delete another's data."""
        first = snapshot_factory()
        second = snapshot_factory()
        _set(first, **POINTER)
        db_session.flush()
        _set(second, **POINTER)

        with pytest.raises(IntegrityError, match="storage_uri"):
            db_session.flush()

    def test_many_snapshots_without_pointers_are_allowed(self, snapshot_factory, db_session):
        """NULL pointers must not collide on the unique constraint."""
        snapshot_factory()
        snapshot_factory()

        db_session.flush()
