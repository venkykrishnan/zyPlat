"""Enforce one default taxonomy version per scope, including global scope.

The original index ``uq_taxonomy_default_per_scope`` was unique on
``(scope_type, owner_company_id, taxonomy_id)``. Global taxonomies have a NULL owner, and
Postgres treats NULLs as distinct in a unique index, so any number of global versions of one
taxonomy could be marked default. It is replaced by one partial unique index per scope.

Revision ID: 20261031_0003
Revises: 20261031_0002
Create Date: 2026-10-31 13:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20261031_0003"
down_revision = "20261031_0002"
branch_labels = None
depends_on = None

TABLE = "taxonomy_definitions"


def upgrade() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT taxonomy_id FROM {TABLE} "
                "WHERE is_default AND scope_type = 'GLOBAL' "
                "GROUP BY taxonomy_id HAVING count(*) > 1"
            )
        )
        .scalars()
        .all()
    )
    if duplicates:
        raise RuntimeError(
            f"Cannot enforce one global default per taxonomy; these taxonomy_ids have several "
            f"default versions: {sorted(duplicates)}. Unset is_default on all but one of each."
        )

    op.drop_index("uq_taxonomy_default_per_scope", table_name=TABLE)
    op.create_index(
        "uq_taxonomy_default_global",
        TABLE,
        ["taxonomy_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE AND scope_type = 'GLOBAL'"),
    )
    op.create_index(
        "uq_taxonomy_default_company",
        TABLE,
        ["owner_company_id", "taxonomy_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE AND scope_type = 'COMPANY'"),
    )


def downgrade() -> None:
    op.drop_index("uq_taxonomy_default_company", table_name=TABLE)
    op.drop_index("uq_taxonomy_default_global", table_name=TABLE)
    op.create_index(
        "uq_taxonomy_default_per_scope",
        TABLE,
        ["scope_type", "owner_company_id", "taxonomy_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE"),
    )
