"""Create application definition tables (logical app, versions, domains, companies).

Revision ID: 20261105_0005
Revises: 20261105_0004
Create Date: 2026-11-05 13:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261105_0005"
down_revision = "20261105_0004"
branch_labels = None
depends_on = None

application_status = postgresql.ENUM(
    "DRAFT", "PUBLISHED", "ARCHIVED", name="application_status", create_type=False
)
application_domain_role = postgresql.ENUM(
    "INPUT", "OUTPUT", name="application_domain_role", create_type=False
)
snapshot_alignment = postgresql.ENUM(
    "COMPANY", "INDEPENDENT", name="snapshot_alignment", create_type=False
)


def upgrade() -> None:
    for enum_type in (application_status, application_domain_role, snapshot_alignment):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            application_status,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column("default_version_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.CheckConstraint(
            "length(trim(application_id)) > 0", name="ck_applications_application_id_not_empty"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
    )

    op.create_table(
        "application_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
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
        sa.CheckConstraint(
            "length(trim(version)) > 0", name="ck_application_versions_version_not_empty"
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_application_versions_name_not_empty"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "version", name="uq_application_versions_app_version"
        ),
    )
    op.create_index(
        "ix_application_versions_application", "application_versions", ["application_id"]
    )

    op.create_foreign_key(
        "fk_applications_default_version",
        "applications",
        "application_versions",
        ["default_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "application_domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", application_domain_role, nullable=False),
        sa.Column("snapshot_alignment", snapshot_alignment, nullable=False),
        sa.Column("schema_hash", sa.String(length=64), nullable=False),
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
            ["application_version_id"], ["application_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["domain_definition_id"], ["domain_definitions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_version_id",
            "domain_definition_id",
            name="uq_application_domains_version_domain",
        ),
    )
    op.create_index(
        "ix_application_domains_version", "application_domains", ["application_version_id"]
    )

    op.create_table(
        "application_companies",
        sa.Column("application_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["application_version_id"], ["application_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("application_version_id", "company_id"),
    )


def downgrade() -> None:
    op.drop_table("application_companies")
    op.drop_index("ix_application_domains_version", table_name="application_domains")
    op.drop_table("application_domains")
    op.drop_constraint("fk_applications_default_version", "applications", type_="foreignkey")
    op.drop_index("ix_application_versions_application", table_name="application_versions")
    op.drop_table("application_versions")
    op.drop_table("applications")
    for enum_type in (snapshot_alignment, application_domain_role, application_status):
        enum_type.drop(op.get_bind(), checkfirst=True)
