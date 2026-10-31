"""Initial company/taxonomy/domain schema (draft).

Revision ID: 20261024_0001
Revises:
Create Date: 2026-10-24 16:58:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20261024_0001"
down_revision = None
branch_labels = None
depends_on = None


# create_type=False: upgrade() creates these types explicitly, so create_table must not try to
# create them a second time (that raises DuplicateObject on a fresh database).
definition_scope_enum = postgresql.ENUM(
    "GLOBAL", "COMPANY", name="definition_scope", create_type=False
)
company_type_enum = postgresql.ENUM(
    "LENDER", "BORROWER", "PARTICIPANT", name="company_type", create_type=False
)
domain_kind_enum = postgresql.ENUM("TIME_SERIES", "SCALAR", name="domain_kind", create_type=False)
period_granularity_enum = postgresql.ENUM(
    "YEAR", "QUARTER", "MONTH", "DATE", name="period_granularity", create_type=False
)
domain_dimension_data_type_enum = postgresql.ENUM(
    "STRING",
    "NUMBER",
    "INTEGER",
    "BOOLEAN",
    "DATE",
    "DATETIME",
    "ENUM",
    "ARRAY_STRING",
    name="domain_dimension_data_type",
    create_type=False,
)
domain_metric_data_type_enum = postgresql.ENUM(
    "NUMBER", "INTEGER", "DECIMAL", name="domain_metric_data_type", create_type=False
)
taxonomy_version_strategy_enum = postgresql.ENUM(
    "LATEST_PUBLISHED", "PINNED", name="taxonomy_version_strategy", create_type=False
)


TRIGGER_TABLES = [
    "companies",
    "company_snapshots",
    "taxonomy_definitions",
    "taxonomy_entities",
    "domain_definitions",
    "domain_dimensions",
    "domain_metrics",
    "domain_instances",
    "domain_instance_snapshots",
    "domain_instance_entities",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    bind = op.get_bind()
    for enum_type in (
        definition_scope_enum,
        company_type_enum,
        domain_kind_enum,
        period_granularity_enum,
        domain_dimension_data_type_enum,
        domain_metric_data_type_enum,
        taxonomy_version_strategy_enum,
    ):
        enum_type.create(bind, checkfirst=True)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("company_type", company_type_enum, nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("naics_code", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column(
            "report_info",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
            "length(trim(company_id)) > 0", name="ck_companies_company_id_not_empty"
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_companies_name_not_empty"),
        sa.CheckConstraint(
            "jsonb_typeof(report_info) = 'array'", name="ck_companies_report_info_array"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'", name="ck_companies_metadata_object"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_companies_customer_id", "companies", ["customer_id"], unique=False)
    op.create_index("ix_companies_is_enabled", "companies", ["is_enabled"], unique=False)
    op.create_index("ix_companies_is_test", "companies", ["is_test"], unique=False)
    op.create_index("ix_companies_naics_code", "companies", ["naics_code"], unique=False)
    op.create_index("ix_companies_state", "companies", ["state"], unique=False)
    op.create_index("ix_companies_company_type", "companies", ["company_type"], unique=False)

    op.create_table(
        "company_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_type", period_granularity_enum, nullable=False),
        sa.Column("period_value", sa.Text(), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("ord > 0", name="ck_company_snapshot_ord_positive"),
        sa.CheckConstraint(
            """
            (period_type = 'YEAR'    AND period_value ~ '^[0-9]{4}$') OR
            (period_type = 'QUARTER' AND period_value ~ '^[0-9]{4}Q[1-4]$') OR
            (period_type = 'MONTH'   AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])$') OR
            (period_type = 'DATE'    AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])$')
            """,
            name="ck_company_snapshot_period_format",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "period_type",
            "period_value",
            "ord",
            name="uq_company_snapshot_tuple",
        ),
    )
    op.create_index(
        "ix_company_snapshot_default_lookup",
        "company_snapshots",
        ["company_id", "period_type", "period_value", "ord"],
        unique=False,
        postgresql_using="btree",
    )

    op.create_table(
        "company_snapshot_heads",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_type", period_granularity_enum, nullable=False),
        sa.Column("period_value", sa.Text(), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["company_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "period_type", "period_value"),
    )

    op.create_table(
        "taxonomy_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("taxonomy_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("scope_type", definition_scope_enum, nullable=False),
        sa.Column("owner_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_hierarchical", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column(
            "allowed_classifications",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
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
            """
            (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
            OR
            (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
            """,
            name="ck_taxonomy_scope_owner",
        ),
        sa.CheckConstraint(
            """
            (is_published = FALSE AND published_at IS NULL)
            OR
            (is_published = TRUE)
            """,
            name="ck_taxonomy_published_fields",
        ),
        sa.ForeignKeyConstraint(["owner_company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_taxonomy_definitions_global_taxonomy_version",
        "taxonomy_definitions",
        ["taxonomy_id", "version"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'GLOBAL'"),
    )
    op.create_index(
        "uq_taxonomy_definitions_company_taxonomy_version",
        "taxonomy_definitions",
        ["owner_company_id", "taxonomy_id", "version"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'COMPANY'"),
    )
    op.create_index(
        "uq_taxonomy_default_per_scope",
        "taxonomy_definitions",
        ["scope_type", "owner_company_id", "taxonomy_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE"),
    )
    op.create_index(
        "ix_taxonomy_lookup",
        "taxonomy_definitions",
        [
            "taxonomy_id",
            "scope_type",
            "owner_company_id",
            "is_published",
            "is_default",
            "updated_at",
        ],
        unique=False,
    )

    op.create_table(
        "taxonomy_entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("taxonomy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parent_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "explicit_classifications",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("is_base_entity", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
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
            "length(trim(entity_id)) > 0", name="ck_taxonomy_entities_entity_id_not_empty"
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_definition_id"], ["taxonomy_definitions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_entity_id"], ["taxonomy_entities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "taxonomy_definition_id",
            "entity_id",
            name="uq_taxonomy_entities_definition_entity",
        ),
    )
    op.create_index(
        "ix_taxonomy_entities_definition",
        "taxonomy_entities",
        ["taxonomy_definition_id"],
        unique=False,
    )
    op.create_index(
        "ix_taxonomy_entities_parent",
        "taxonomy_entities",
        ["taxonomy_definition_id", "parent_entity_id"],
        unique=False,
    )

    op.create_table(
        "domain_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_id", sa.Text(), nullable=False),
        sa.Column("scope_type", definition_scope_enum, nullable=False),
        sa.Column("owner_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", domain_kind_enum, nullable=False),
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
            """
            (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
            OR
            (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
            """,
            name="ck_domain_scope_owner",
        ),
        sa.CheckConstraint("length(trim(domain_id)) > 0", name="ck_domain_id_not_empty"),
        sa.ForeignKeyConstraint(["owner_company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_domain_definitions_global_domain",
        "domain_definitions",
        ["domain_id"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'GLOBAL'"),
    )
    op.create_index(
        "uq_domain_definitions_company_domain",
        "domain_definitions",
        ["owner_company_id", "domain_id"],
        unique=True,
        postgresql_where=sa.text("scope_type = 'COMPANY'"),
    )
    op.create_index("ix_domain_definitions_kind", "domain_definitions", ["kind"], unique=False)

    op.create_table(
        "domain_dimensions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("data_type", domain_dimension_data_type_enum, nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_filter", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("taxonomy_id", sa.Text(), nullable=True),
        sa.Column("taxonomy_version_strategy", taxonomy_version_strategy_enum, nullable=True),
        sa.Column("taxonomy_version", sa.Text(), nullable=True),
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
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_domain_dimension_name_not_empty"),
        sa.CheckConstraint(
            """
            (taxonomy_id IS NULL AND taxonomy_version_strategy IS NULL AND taxonomy_version IS NULL)
            OR
            (
              taxonomy_id IS NOT NULL
              AND taxonomy_version_strategy IS NOT NULL
              AND (
                (taxonomy_version_strategy = 'PINNED' AND taxonomy_version IS NOT NULL)
                OR
                (taxonomy_version_strategy = 'LATEST_PUBLISHED' AND taxonomy_version IS NULL)
              )
            )
            """,
            name="ck_domain_dimensions_taxonomy_binding",
        ),
        sa.ForeignKeyConstraint(
            ["domain_definition_id"], ["domain_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_definition_id", "name", name="uq_domain_dimensions_name"),
        sa.UniqueConstraint("domain_definition_id", "ordinal", name="uq_domain_dimensions_ordinal"),
    )
    op.create_index(
        "ix_domain_dimensions_taxonomy_lookup",
        "domain_dimensions",
        ["taxonomy_id", "taxonomy_version_strategy", "taxonomy_version"],
        unique=False,
    )

    op.create_table(
        "domain_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("data_type", domain_metric_data_type_enum, nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "is_point_in_time", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")
        ),
        sa.Column("is_end_value", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
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
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_domain_metric_name_not_empty"),
        sa.ForeignKeyConstraint(
            ["domain_definition_id"], ["domain_definitions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_definition_id", "name", name="uq_domain_metrics_name"),
        sa.UniqueConstraint("domain_definition_id", "ordinal", name="uq_domain_metrics_ordinal"),
    )

    op.create_table(
        "domain_instances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "classification_scope",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
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
            ["domain_definition_id"], ["domain_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "domain_definition_id", "company_id", name="uq_domain_instance_domain_company"
        ),
    )
    op.create_index("ix_domain_instances_company", "domain_instances", ["company_id"], unique=False)

    op.create_table(
        "domain_instance_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["domain_instance_id"], ["domain_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["company_snapshot_id"], ["company_snapshots.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "domain_instance_id",
            "company_snapshot_id",
            name="uq_domain_instance_company_snapshot",
        ),
    )
    op.create_index(
        "ix_domain_instance_snapshots_company_snapshot",
        "domain_instance_snapshots",
        ["company_snapshot_id"],
        unique=False,
    )

    op.create_table(
        "domain_instance_entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain_instance_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "jsonb_typeof(data) = 'object'", name="ck_domain_instance_entities_data_object"
        ),
        sa.ForeignKeyConstraint(
            ["domain_instance_id"], ["domain_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["domain_instance_snapshot_id"],
            ["domain_instance_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_domain_instance_entities_instance",
        "domain_instance_entities",
        ["domain_instance_id"],
        unique=False,
    )
    op.create_index(
        "ix_domain_instance_entities_snapshot",
        "domain_instance_entities",
        ["domain_instance_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_domain_instance_entities_data_gin",
        "domain_instance_entities",
        ["data"],
        unique=False,
        postgresql_using="gin",
    )

    for table_name in TRIGGER_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table_name in reversed(TRIGGER_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON {table_name};")

    op.drop_index("ix_domain_instance_entities_data_gin", table_name="domain_instance_entities")
    op.drop_index("ix_domain_instance_entities_snapshot", table_name="domain_instance_entities")
    op.drop_index("ix_domain_instance_entities_instance", table_name="domain_instance_entities")
    op.drop_table("domain_instance_entities")

    op.drop_index(
        "ix_domain_instance_snapshots_company_snapshot", table_name="domain_instance_snapshots"
    )
    op.drop_table("domain_instance_snapshots")

    op.drop_index("ix_domain_instances_company", table_name="domain_instances")
    op.drop_table("domain_instances")

    op.drop_table("domain_metrics")

    op.drop_index("ix_domain_dimensions_taxonomy_lookup", table_name="domain_dimensions")
    op.drop_table("domain_dimensions")

    op.drop_index("ix_domain_definitions_kind", table_name="domain_definitions")
    op.drop_index("uq_domain_definitions_company_domain", table_name="domain_definitions")
    op.drop_index("uq_domain_definitions_global_domain", table_name="domain_definitions")
    op.drop_table("domain_definitions")

    op.drop_index("ix_taxonomy_entities_parent", table_name="taxonomy_entities")
    op.drop_index("ix_taxonomy_entities_definition", table_name="taxonomy_entities")
    op.drop_table("taxonomy_entities")

    op.drop_index("ix_taxonomy_lookup", table_name="taxonomy_definitions")
    op.drop_index("uq_taxonomy_default_per_scope", table_name="taxonomy_definitions")
    op.drop_index(
        "uq_taxonomy_definitions_company_taxonomy_version", table_name="taxonomy_definitions"
    )
    op.drop_index(
        "uq_taxonomy_definitions_global_taxonomy_version", table_name="taxonomy_definitions"
    )
    op.drop_table("taxonomy_definitions")

    op.drop_table("company_snapshot_heads")

    op.drop_index("ix_company_snapshot_default_lookup", table_name="company_snapshots")
    op.drop_table("company_snapshots")

    op.drop_index("ix_companies_company_type", table_name="companies")
    op.drop_index("ix_companies_state", table_name="companies")
    op.drop_index("ix_companies_naics_code", table_name="companies")
    op.drop_index("ix_companies_is_test", table_name="companies")
    op.drop_index("ix_companies_is_enabled", table_name="companies")
    op.drop_index("ix_companies_customer_id", table_name="companies")
    op.drop_table("companies")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    bind = op.get_bind()
    for enum_type in (
        taxonomy_version_strategy_enum,
        domain_metric_data_type_enum,
        domain_dimension_data_type_enum,
        period_granularity_enum,
        domain_kind_enum,
        company_type_enum,
        definition_scope_enum,
    ):
        enum_type.drop(bind, checkfirst=True)
