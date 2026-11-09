"""Nullable company snapshot on instance snapshots; application bind instances.

Revision ID: 20261105_0006
Revises: 20261105_0005
Create Date: 2026-11-05 14:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261105_0006"
down_revision = "20261105_0005"
branch_labels = None
depends_on = None

SNAPSHOTS = "domain_instance_snapshots"
period_granularity = postgresql.ENUM(
    "YEAR", "QUARTER", "MONTH", "DATE", name="period_granularity", create_type=False
)


def upgrade() -> None:
    op.drop_constraint("uq_domain_instance_company_snapshot", SNAPSHOTS, type_="unique")
    op.alter_column(
        SNAPSHOTS,
        "company_snapshot_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(SNAPSHOTS, sa.Column("snapshot_period_type", period_granularity, nullable=True))
    op.add_column(SNAPSHOTS, sa.Column("snapshot_period_value", sa.String(), nullable=True))
    op.create_index(
        "uq_domain_instance_company_snapshot",
        SNAPSHOTS,
        ["domain_instance_id", "company_snapshot_id"],
        unique=True,
        postgresql_where=sa.text("company_snapshot_id IS NOT NULL"),
    )
    op.create_index(
        "uq_domain_instance_independent_snapshot",
        SNAPSHOTS,
        ["domain_instance_id", "snapshot_period_type", "snapshot_period_value"],
        unique=True,
        postgresql_where=sa.text("company_snapshot_id IS NULL"),
    )
    op.create_check_constraint(
        "ck_domain_instance_snapshots_alignment",
        SNAPSHOTS,
        """
        (
          company_snapshot_id IS NOT NULL
          AND snapshot_period_type IS NULL
          AND snapshot_period_value IS NULL
        )
        OR
        (
          company_snapshot_id IS NULL
          AND snapshot_period_type IS NOT NULL
          AND snapshot_period_value IS NOT NULL
        )
        """,
    )
    op.create_check_constraint(
        "ck_domain_instance_snapshots_period_format",
        SNAPSHOTS,
        """
        snapshot_period_type IS NULL
        OR (
          (snapshot_period_type = 'YEAR' AND snapshot_period_value ~ '^[0-9]{4}$')
          OR (snapshot_period_type = 'QUARTER' AND snapshot_period_value ~ '^[0-9]{4}Q[1-4]$')
          OR (
            snapshot_period_type = 'MONTH'
            AND snapshot_period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
          )
          OR (
            snapshot_period_type = 'DATE'
            AND snapshot_period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])$'
          )
        )
        """,
    )

    op.create_table(
        "application_bind_instances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["application_version_id"], ["application_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["company_snapshot_id"], ["company_snapshots.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_version_id",
            "company_id",
            "company_snapshot_id",
            name="uq_application_bind_instances_version_company_snapshot",
        ),
    )
    op.create_index(
        "ix_application_bind_instances_version",
        "application_bind_instances",
        ["application_version_id"],
    )

    op.create_table(
        "application_bind_instance_members",
        sa.Column("bind_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_instance_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bind_instance_id"], ["application_bind_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["domain_instance_snapshot_id"],
            ["domain_instance_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["domain_definition_id"], ["domain_definitions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("bind_instance_id", "domain_instance_snapshot_id"),
    )
    op.create_index(
        "ix_application_bind_members_domain",
        "application_bind_instance_members",
        ["domain_definition_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_bind_members_domain", table_name="application_bind_instance_members"
    )
    op.drop_table("application_bind_instance_members")
    op.drop_index("ix_application_bind_instances_version", table_name="application_bind_instances")
    op.drop_table("application_bind_instances")

    op.drop_constraint("ck_domain_instance_snapshots_period_format", SNAPSHOTS, type_="check")
    op.drop_constraint("ck_domain_instance_snapshots_alignment", SNAPSHOTS, type_="check")
    op.drop_index("uq_domain_instance_independent_snapshot", table_name=SNAPSHOTS)
    op.drop_index("uq_domain_instance_company_snapshot", table_name=SNAPSHOTS)
    op.drop_column(SNAPSHOTS, "snapshot_period_value")
    op.drop_column(SNAPSHOTS, "snapshot_period_type")
    op.alter_column(
        SNAPSHOTS,
        "company_snapshot_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_domain_instance_company_snapshot",
        SNAPSHOTS,
        ["domain_instance_id", "company_snapshot_id"],
    )
