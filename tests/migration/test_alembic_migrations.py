"""Migration tests: run the real Alembic CLI against scratch Postgres databases.

Alembic is run as a subprocess because its ``env.py`` calls ``fileConfig``, which would
disable the loggers of every other test if run in-process. Each test gets its own database so
the shared ``zyplat_test`` schema used by the rest of the suite is never touched.
"""

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.migration

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
SNAPSHOTS_TABLE = "domain_instance_snapshots"
TAXONOMY_TABLE = "taxonomy_definitions"
DOMAIN_TABLE = "domain_definitions"
POINTER_COLUMNS = {"storage_uri", "row_count", "schema_hash", "checksum", "calc_run_id"}
ENUM_TYPES = {
    "company_type",
    "definition_scope",
    "domain_kind",
    "domain_dimension_data_type",
    "domain_metric_data_type",
    "period_granularity",
}


def _base_url() -> URL:
    return make_url(os.environ["DATABASE_URL"])


@pytest.fixture
def scratch_db() -> Iterator[URL]:
    """Create an empty database for one test and drop it afterwards."""
    base = _base_url()
    name = f"zyplat_mig_{uuid.uuid4().hex[:10]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield base.set(database=name)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def scratch_engine(scratch_db: URL) -> Iterator[Engine]:
    engine = create_engine(scratch_db)
    yield engine
    engine.dispose()


def run_alembic(
    database: URL, *args: str, cwd: Path = REPO_ROOT, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run ``alembic -c backend/alembic.ini <args>`` against ``database``."""
    env = {
        **os.environ,
        "ALEMBIC_DATABASE_URL": database.render_as_string(hide_password=False),
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        pytest.fail(f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


def _user_types(engine: Engine) -> set[str]:
    query = text(
        "SELECT typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "WHERE n.nspname = 'public' AND t.typtype = 'e'"
    )
    with engine.connect() as connection:
        return {row[0] for row in connection.execute(query)}


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


class TestMigrationHistory:
    """The revision graph must be linear."""

    def test_there_is_exactly_one_head(self, scratch_db):
        """Multiple heads mean two branches were merged without a merge revision."""
        output = run_alembic(scratch_db, "heads").stdout

        assert output.count("(head)") == 1


class TestUpgrade:
    """``upgrade head`` must work from either supported working directory."""

    @pytest.mark.parametrize("cwd", [REPO_ROOT, BACKEND_DIR], ids=["repo-root", "backend-dir"])
    def test_upgrade_head_creates_schema(self, scratch_db, scratch_engine, cwd):
        """CI runs from backend/ and the Makefile from the repo root; both must work."""
        run_alembic(scratch_db, "upgrade", "head", cwd=cwd)

        assert {"companies", "domain_definitions", SNAPSHOTS_TABLE} <= _tables(scratch_engine)

    def test_head_adds_storage_pointer_columns(self, scratch_db, scratch_engine):
        """Instance data pointers live on the snapshot row."""
        run_alembic(scratch_db, "upgrade", "head")

        columns = {c["name"] for c in inspect(scratch_engine).get_columns(SNAPSHOTS_TABLE)}

        assert columns >= POINTER_COLUMNS

    def test_head_creates_pointer_constraints(self, scratch_db, scratch_engine):
        """Constraints in the migration must match the ones declared on the model."""
        run_alembic(scratch_db, "upgrade", "head")

        inspector = inspect(scratch_engine)
        checks = {c["name"] for c in inspector.get_check_constraints(SNAPSHOTS_TABLE)}
        uniques = {u["name"] for u in inspector.get_unique_constraints(SNAPSHOTS_TABLE)}

        assert "ck_domain_instance_snapshots_storage_pointer_complete" in checks
        assert "ck_domain_instance_snapshots_row_count_non_negative" in checks
        assert "uq_domain_instance_snapshots_storage_uri" in uniques

    def test_upgrade_is_idempotent(self, scratch_db):
        """Running upgrade twice must be a no-op the second time."""
        run_alembic(scratch_db, "upgrade", "head")

        run_alembic(scratch_db, "upgrade", "head")

    def test_current_reports_head_after_upgrade(self, scratch_db):
        """``alembic current`` is the post-deploy sanity check."""
        run_alembic(scratch_db, "upgrade", "head")

        assert "(head)" in run_alembic(scratch_db, "current").stdout


class TestDowngrade:
    """Downgrades must cleanly reverse upgrades."""

    def test_downgrade_removes_only_pointer_columns(self, scratch_db, scratch_engine):
        """Reversing 0002 must not touch the earlier schema."""
        run_alembic(scratch_db, "upgrade", "head")

        run_alembic(scratch_db, "downgrade", "20261024_0001")

        columns = {c["name"] for c in inspect(scratch_engine).get_columns(SNAPSHOTS_TABLE)}
        assert columns.isdisjoint(POINTER_COLUMNS)
        assert "domain_instance_id" in columns

    def test_downgrade_restores_original_default_index(self, scratch_db, scratch_engine):
        """Reversing 0003 swaps the two per-scope indexes back for the original single one."""
        run_alembic(scratch_db, "upgrade", "head")

        run_alembic(scratch_db, "downgrade", "-1")

        names = _index_names(scratch_engine, TAXONOMY_TABLE)
        assert "uq_taxonomy_default_per_scope" in names
        assert {"uq_taxonomy_default_global", "uq_taxonomy_default_company"}.isdisjoint(names)

    def test_downgrade_to_base_removes_tables_and_enum_types(self, scratch_db, scratch_engine):
        """Leftover enum types would make the next upgrade fail with DuplicateObject."""
        run_alembic(scratch_db, "upgrade", "head")

        run_alembic(scratch_db, "downgrade", "base")

        assert _tables(scratch_engine) <= {"alembic_version"}
        assert ENUM_TYPES.isdisjoint(_user_types(scratch_engine))

    def test_upgrade_after_full_downgrade_succeeds(self, scratch_db, scratch_engine):
        """The upgrade/downgrade cycle must be repeatable."""
        run_alembic(scratch_db, "upgrade", "head")
        run_alembic(scratch_db, "downgrade", "base")

        run_alembic(scratch_db, "upgrade", "head")

        assert SNAPSHOTS_TABLE in _tables(scratch_engine)


class TestMigratedSchemaEnforcesRules:
    """The deployed schema comes from migrations, so its rules are tested there directly."""

    def _insert_taxonomy(self, connection, version, *, is_default, taxonomy_id="tax"):
        connection.execute(
            text(
                "INSERT INTO taxonomy_definitions "
                "(taxonomy_id, version, scope_type, description, is_default) "
                "VALUES (:taxonomy_id, :version, 'GLOBAL', 'd', :is_default)"
            ),
            {"taxonomy_id": taxonomy_id, "version": version, "is_default": is_default},
        )

    def test_two_global_defaults_for_one_taxonomy_are_rejected(self, scratch_db, scratch_engine):
        """Global rows have a NULL owner, which the original index did not cover."""
        run_alembic(scratch_db, "upgrade", "head")

        with scratch_engine.connect() as connection:
            self._insert_taxonomy(connection, "1.0.0", is_default=True)
            with pytest.raises(IntegrityError, match="uq_taxonomy_default_global"):
                self._insert_taxonomy(connection, "2.0.0", is_default=True)

    def test_duplicate_global_taxonomy_version_is_rejected(self, scratch_db, scratch_engine):
        """The migrated schema must reject what the ORM models reject."""
        run_alembic(scratch_db, "upgrade", "head")

        with scratch_engine.connect() as connection:
            self._insert_taxonomy(connection, "1.0.0", is_default=False)
            with pytest.raises(IntegrityError, match="uq_taxonomy_definitions_global"):
                self._insert_taxonomy(connection, "1.0.0", is_default=False)

    def test_upgrade_with_existing_duplicate_defaults_fails_with_clear_message(
        self, scratch_db, scratch_engine
    ):
        """Existing bad data must produce an actionable error, not an opaque index failure."""
        run_alembic(scratch_db, "upgrade", "20261031_0002")
        with scratch_engine.begin() as connection:
            self._insert_taxonomy(connection, "1.0.0", is_default=True)
            self._insert_taxonomy(connection, "2.0.0", is_default=True)

        result = run_alembic(scratch_db, "upgrade", "head", check=False)

        assert result.returncode != 0
        assert "have several default versions: ['tax']" in result.stderr


@pytest.mark.parametrize("table", [SNAPSHOTS_TABLE, TAXONOMY_TABLE, DOMAIN_TABLE])
class TestModelsMatchMigrations:
    """Guard tables against drift between ORM models and migrations.

    A full ``alembic check`` still reports pre-existing drift elsewhere (see the backlog), so
    tables are added here as they are brought in line.
    """

    def test_table_matches_model_metadata(self, scratch_db, scratch_engine, table):
        """Columns, constraints and indexes must agree between ORM and migrations."""
        model_db = _create_model_database(scratch_db)
        model_engine = create_engine(model_db)
        try:
            run_alembic(scratch_db, "upgrade", "head")
            migrated = _describe_table(scratch_engine, table)
            modeled = _describe_table(model_engine, table)
        finally:
            model_engine.dispose()
            _drop_database(scratch_db, model_db)

        assert migrated == modeled


def _create_model_database(scratch_db: URL) -> URL:
    from backend.app.core.database import Base

    model_url = scratch_db.set(database=f"{scratch_db.database}_model")
    admin = create_engine(scratch_db.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{model_url.database}"'))
    admin.dispose()
    engine = create_engine(model_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    return model_url


def _drop_database(scratch_db: URL, model_url: URL) -> None:
    admin = create_engine(scratch_db.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{model_url.database}" WITH (FORCE)'))
    admin.dispose()


def _describe_table(engine: Engine, table: str) -> dict[str, object]:
    """Describe a table's integrity rules.

    Column types and non-unique indexes are left out on purpose: the models and migrations still
    differ there (TEXT vs VARCHAR, lookup index names), which is tracked in the backlog.
    """
    inspector = inspect(engine)
    return {
        "columns": {c["name"]: c["nullable"] for c in inspector.get_columns(table)},
        "checks": {c["name"] for c in inspector.get_check_constraints(table)},
        "uniques": {u["name"] for u in inspector.get_unique_constraints(table)},
        "unique_indexes": {
            (
                i["name"],
                tuple(i["column_names"]),
                i.get("dialect_options", {}).get("postgresql_where"),
            )
            for i in inspector.get_indexes(table)
            if i["unique"]
        },
    }


def _index_names(engine: Engine, table: str) -> set[str]:
    return {i["name"] for i in inspect(engine).get_indexes(table)}
