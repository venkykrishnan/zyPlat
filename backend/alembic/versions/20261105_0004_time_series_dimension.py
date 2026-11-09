"""Add time-series field columns to domain_dimensions.

Revision ID: 20261105_0004
Revises: 20261031_0003
Create Date: 2026-11-05 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20261105_0004"
down_revision = "20261031_0003"
branch_labels = None
depends_on = None

TABLE = "domain_dimensions"
period_granularity_enum = postgresql.ENUM(
    "YEAR", "QUARTER", "MONTH", "DATE", name="period_granularity", create_type=False
)


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("is_time_series", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )
    op.add_column(TABLE, sa.Column("period_type", period_granularity_enum, nullable=True))
    op.create_check_constraint(
        "ck_domain_dimension_time_series_fields",
        TABLE,
        """
        (is_time_series = FALSE AND period_type IS NULL)
        OR
        (is_time_series = TRUE AND period_type IS NOT NULL AND data_type = 'DATETIME')
        """,
    )
    op.create_index(
        "uq_domain_dimensions_one_time_series",
        TABLE,
        ["domain_definition_id"],
        unique=True,
        postgresql_where=sa.text("is_time_series = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_domain_dimensions_one_time_series", table_name=TABLE)
    op.drop_constraint("ck_domain_dimension_time_series_fields", TABLE, type_="check")
    op.drop_column(TABLE, "period_type")
    op.drop_column(TABLE, "is_time_series")
