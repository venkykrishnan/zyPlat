"""Add storage pointer columns to domain_instance_snapshots.

TIME_SERIES instance data moves from per-row JSONB to one immutable Parquet file per snapshot.
These columns locate and fingerprint that file. See docs/plans/instance-data-storage.md.

Revision ID: 20261031_0002
Revises: 20261024_0001
Create Date: 2026-10-31 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261031_0002"
down_revision = "20261024_0001"
branch_labels = None
depends_on = None

TABLE = "domain_instance_snapshots"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("storage_uri", sa.Text(), nullable=True))
    op.add_column(TABLE, sa.Column("row_count", sa.BigInteger(), nullable=True))
    op.add_column(TABLE, sa.Column("schema_hash", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("checksum", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("calc_run_id", sa.String(), nullable=True))

    op.create_unique_constraint("uq_domain_instance_snapshots_storage_uri", TABLE, ["storage_uri"])
    op.create_check_constraint(
        "ck_domain_instance_snapshots_storage_pointer_complete",
        TABLE,
        """
        (storage_uri IS NULL) = (row_count IS NULL)
        AND (storage_uri IS NULL) = (schema_hash IS NULL)
        AND (storage_uri IS NULL) = (checksum IS NULL)
        """,
    )
    op.create_check_constraint(
        "ck_domain_instance_snapshots_row_count_non_negative",
        TABLE,
        "row_count IS NULL OR row_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_domain_instance_snapshots_row_count_non_negative", TABLE, type_="check")
    op.drop_constraint(
        "ck_domain_instance_snapshots_storage_pointer_complete", TABLE, type_="check"
    )
    op.drop_constraint("uq_domain_instance_snapshots_storage_uri", TABLE, type_="unique")

    op.drop_column(TABLE, "calc_run_id")
    op.drop_column(TABLE, "checksum")
    op.drop_column(TABLE, "schema_hash")
    op.drop_column(TABLE, "row_count")
    op.drop_column(TABLE, "storage_uri")
