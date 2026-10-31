"""Columnar storage of time-series domain instance data (Parquet + pandas)."""

from __future__ import annotations

from functools import lru_cache

from ...core.config import settings
from .schema import ColumnKind, ColumnSpec, FrameSpec, schema_hash
from .store import (
    InstanceDataStore,
    LocalParquetStore,
    StoredFrameInfo,
    build_snapshot_key,
    table_to_frame,
)
from .validation import validate_frame

__all__ = [
    "ColumnKind",
    "ColumnSpec",
    "FrameSpec",
    "InstanceDataStore",
    "LocalParquetStore",
    "StoredFrameInfo",
    "build_snapshot_key",
    "get_instance_data_store",
    "schema_hash",
    "table_to_frame",
    "validate_frame",
]


@lru_cache(maxsize=1)
def get_instance_data_store() -> InstanceDataStore:
    """Return the process-wide store configured by ``INSTANCE_DATA_DIR``."""
    return LocalParquetStore(settings.INSTANCE_DATA_DIR)
