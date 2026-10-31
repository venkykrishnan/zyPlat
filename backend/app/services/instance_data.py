"""Write and read time-series domain instance data for a snapshot.

Postgres stores only the snapshot's storage pointer; the rows live in an immutable Parquet file
(see ``docs/plans/instance-data-storage.md``). A correction is a new snapshot, never an edit.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from ..core.exceptions import (
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)
from ..models.domain import (
    DomainDefinition,
    DomainInstance,
    DomainInstanceSnapshot,
    DomainKind,
)
from ..storage.instance_data import (
    FrameSpec,
    InstanceDataStore,
    StoredFrameInfo,
    build_snapshot_key,
    table_to_frame,
    validate_frame,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotWriteOptions:
    """Optional inputs to ``InstanceDataService.write_snapshot_frame``.

    Attributes:
        calc_run_id: Identifier of the calculation run that produced the data.
        allowed_values: Dimension name to the taxonomy values it may contain. Taxonomy
            version resolution is not implemented yet, so callers resolve these themselves.
    """

    calc_run_id: str | None = None
    allowed_values: Mapping[str, Collection[str]] | None = None


class InstanceDataService:
    """Orchestrates validation, file storage, and the snapshot's storage pointer."""

    def __init__(self, store: InstanceDataStore) -> None:
        self._store = store

    def write_snapshot_frame(
        self,
        db: Session,
        snapshot_id: UUID,
        frame: pd.DataFrame,
        options: SnapshotWriteOptions | None = None,
    ) -> DomainInstanceSnapshot:
        """Validate ``frame`` and store it as the data of ``snapshot_id``.

        The snapshot row is locked for the duration so concurrent writers serialize. The file
        is written before the pointer is committed; if the commit fails the file is removed.

        Args:
            db: Database session; committed on success.
            snapshot_id: Target ``domain_instance_snapshots.id``.
            frame: Rows to store, with one column per domain dimension and metric.
            options: Calculation run id and taxonomy value constraints.

        Returns:
            The snapshot with its storage pointer populated.

        Raises:
            NotFoundError: If the snapshot does not exist.
            ValidationError: If the domain is not TIME_SERIES or the frame is invalid.
            ConflictError: If the snapshot already has data.
        """
        options = options or SnapshotWriteOptions()
        snapshot, instance, definition = self._load_context(db, snapshot_id, for_update=True)
        if definition.kind != DomainKind.TIME_SERIES:
            raise ValidationError(
                f"Domain '{definition.domain_id}' is {definition.kind.value}; only TIME_SERIES "
                "domains store instance data as files."
            )
        if snapshot.storage_uri is not None:
            raise ConflictError(
                f"Snapshot {snapshot_id} already has data; create a new snapshot to correct it."
            )

        table = validate_frame(
            frame, FrameSpec.from_domain(definition), allowed_values=options.allowed_values
        )
        key = build_snapshot_key(definition.id, instance.id, snapshot.id)
        info = self._store.write(key, table)
        self._commit_pointer(db, snapshot, info, options.calc_run_id)

        logger.info(
            "Stored instance data for snapshot",
            extra={
                "operation": "write_snapshot_frame",
                "domain_id": definition.domain_id,
                "instance_id": str(instance.id),
                "snapshot_id": str(snapshot.id),
                "row_count": info.row_count,
                "size_bytes": info.size_bytes,
            },
        )
        return snapshot

    def read_snapshot_frame(
        self,
        db: Session,
        snapshot_id: UUID,
        columns: Sequence[str] | None = None,
        filters: list[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        """Return a snapshot's data as a DataFrame with pyarrow-backed dtypes.

        Args:
            db: Database session.
            snapshot_id: Source ``domain_instance_snapshots.id``.
            columns: Columns to load; all when omitted. Loading fewer columns reads less data.
            filters: Optional Parquet row filters, such as ``[("account", "=", "1000")]``.

        Raises:
            NotFoundError: If the snapshot does not exist or has no stored data.
        """
        snapshot = db.get(DomainInstanceSnapshot, snapshot_id)
        if snapshot is None:
            raise NotFoundError(f"Snapshot {snapshot_id} not found.")
        if snapshot.storage_uri is None:
            raise NotFoundError(f"Snapshot {snapshot_id} has no stored instance data.")
        return table_to_frame(self._store.read(snapshot.storage_uri, columns, filters))

    def _load_context(
        self, db: Session, snapshot_id: UUID, *, for_update: bool
    ) -> tuple[DomainInstanceSnapshot, DomainInstance, DomainDefinition]:
        snapshot = db.get(DomainInstanceSnapshot, snapshot_id, with_for_update=for_update)
        if snapshot is None:
            raise NotFoundError(f"Snapshot {snapshot_id} not found.")
        instance = db.get(DomainInstance, snapshot.domain_instance_id)
        if instance is None:
            raise NotFoundError(f"Domain instance for snapshot {snapshot_id} not found.")
        definition = db.get(DomainDefinition, instance.domain_definition_id)
        if definition is None:
            raise NotFoundError(f"Domain definition for snapshot {snapshot_id} not found.")
        return snapshot, instance, definition

    def _commit_pointer(
        self,
        db: Session,
        snapshot: DomainInstanceSnapshot,
        info: StoredFrameInfo,
        calc_run_id: str | None,
    ) -> None:
        snapshot.storage_uri = info.uri
        snapshot.row_count = info.row_count
        snapshot.schema_hash = info.schema_hash
        snapshot.checksum = info.checksum
        snapshot.calc_run_id = calc_run_id
        try:
            db.commit()
        except Exception:
            db.rollback()
            self._discard_file(info.uri)
            raise

    def _discard_file(self, uri: str) -> None:
        """Remove a file whose pointer never committed, without masking the original error."""
        try:
            self._store.delete(uri)
        except InfrastructureError:
            # TODO(venky, 2026-10-31): Rely on the orphan-file cleanup job once it exists.
            logger.exception(
                "Could not remove uncommitted instance data file",
                extra={"operation": "discard_file", "uri": uri},
            )
