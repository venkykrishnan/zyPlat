"""File storage for time-series instance data.

``InstanceDataStore`` is the seam between services and the physical backend. The local Parquet
implementation is meant for development, tests, and single-node deployments; an object-store
implementation (S3) can be added behind the same protocol.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ...core.exceptions import ConflictError, InfrastructureError, NotFoundError, ValidationError
from .schema import schema_hash

PARQUET_COMPRESSION = "zstd"
_HASH_CHUNK_BYTES = 1024 * 1024

Filters = list[tuple[str, str, Any]]


@dataclass(frozen=True)
class StoredFrameInfo:
    """Facts about a stored file, persisted on the snapshot row as its storage pointer."""

    uri: str
    row_count: int
    size_bytes: int
    checksum: str
    schema_hash: str


class InstanceDataStore(Protocol):
    """Immutable, write-once storage of one Arrow table per snapshot."""

    def write(self, key: str, table: pa.Table) -> StoredFrameInfo:
        """Store ``table`` under ``key``; raises ``ConflictError`` if ``key`` already exists."""

    def read(
        self, uri: str, columns: Sequence[str] | None = None, filters: Filters | None = None
    ) -> pa.Table:
        """Read a stored table, optionally projecting columns and filtering rows."""

    def delete(self, uri: str) -> None:
        """Remove a stored table; does nothing if it is already gone."""


def table_to_frame(table: pa.Table) -> pd.DataFrame:
    """Convert to a DataFrame with pyarrow-backed dtypes, preserving types such as decimals.

    Plain NumPy dtypes would turn nullable integers into floats and decimals into objects.
    """
    frame: pd.DataFrame = table.to_pandas(types_mapper=pd.ArrowDtype)
    return frame


def build_snapshot_key(
    domain_definition_id: object, instance_id: object, snapshot_id: object
) -> str:
    """Return the storage key for a snapshot's data file.

    Keys use immutable surrogate ids rather than business identifiers, so correcting a company
    id or period never orphans a file.

    Example:
        >>> build_snapshot_key("d", "i", "s")
        'd/i/s.parquet'
    """
    return f"{domain_definition_id}/{instance_id}/{snapshot_id}.parquet"


class LocalParquetStore:
    """``InstanceDataStore`` backed by Parquet files under a root directory.

    URIs look like ``local://<key>`` and are relative to ``root``, so the directory can be
    moved without invalidating pointers stored in the database.
    """

    _SCHEME_PREFIX = "local://"

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).resolve()

    def write(self, key: str, table: pa.Table) -> StoredFrameInfo:
        final_path = self._path_for_key(key)
        temp_path = final_path.with_name(f".{final_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, temp_path, compression=PARQUET_COMPRESSION)
            checksum = _sha256_of(temp_path)
            size_bytes = temp_path.stat().st_size
            # A hard link fails if the target exists, which makes the claim atomic and
            # prevents two concurrent writers from overwriting each other's snapshot.
            os.link(temp_path, final_path)
        except FileExistsError as error:
            raise ConflictError(
                f"Instance data already exists for key '{key}'; snapshots are immutable."
            ) from error
        except (OSError, pa.ArrowException) as error:
            raise InfrastructureError(f"Failed to write instance data '{key}': {error}") from error
        finally:
            temp_path.unlink(missing_ok=True)

        return StoredFrameInfo(
            uri=f"{self._SCHEME_PREFIX}{key}",
            row_count=table.num_rows,
            size_bytes=size_bytes,
            checksum=checksum,
            schema_hash=schema_hash(table.schema),
        )

    def read(
        self, uri: str, columns: Sequence[str] | None = None, filters: Filters | None = None
    ) -> pa.Table:
        path = self._path_for_uri(uri)
        # Reading the schema first separates a damaged file (our problem) from bad
        # columns or filters (the caller's problem); Arrow raises ArrowInvalid for both.
        try:
            pq.read_schema(path)
        except FileNotFoundError as error:
            raise NotFoundError(f"Instance data file not found for '{uri}'.") from error
        except (OSError, pa.ArrowException) as error:
            raise InfrastructureError(f"Failed to read instance data '{uri}': {error}") from error

        try:
            return pq.read_table(
                path, columns=list(columns) if columns is not None else None, filters=filters
            )
        except (pa.ArrowInvalid, KeyError, ValueError) as error:
            raise ValidationError(f"Invalid columns or filters for '{uri}': {error}") from error
        except (OSError, pa.ArrowException) as error:
            raise InfrastructureError(f"Failed to read instance data '{uri}': {error}") from error

    def delete(self, uri: str) -> None:
        try:
            self._path_for_uri(uri).unlink(missing_ok=True)
        except OSError as error:
            raise InfrastructureError(f"Failed to delete instance data '{uri}': {error}") from error

    def _path_for_uri(self, uri: str) -> Path:
        if not uri.startswith(self._SCHEME_PREFIX):
            raise ValidationError(f"Unsupported storage URI '{uri}'; expected local://<key>.")
        return self._path_for_key(uri.removeprefix(self._SCHEME_PREFIX))

    def _path_for_key(self, key: str) -> Path:
        parts = PurePosixPath(key).parts
        if not parts or PurePosixPath(key).is_absolute() or ".." in parts:
            raise ValidationError(f"Invalid storage key '{key}'; it must be a relative path.")
        path = (self._root / key).resolve()
        # Resolving catches symlinks that would otherwise escape the root.
        if not path.is_relative_to(self._root):
            raise ValidationError(f"Invalid storage key '{key}'; it escapes the storage root.")
        return path


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
