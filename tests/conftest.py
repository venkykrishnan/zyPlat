"""Test configuration and fixtures."""

import os
import uuid
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test database URL
os.environ["DATABASE_URL"] = "postgresql://zyplat:zyplat@localhost:5432/zyplat_test"

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.company import Company, CompanySnapshot, CompanyType, PeriodGranularity
from backend.app.models.domain import (
    DomainDefinition,
    DomainDimension,
    DomainDimensionDataType,
    DomainInstance,
    DomainInstanceSnapshot,
    DomainKind,
    DomainMetric,
    DomainMetricDataType,
)
from backend.app.models.taxonomy import DefinitionScope


# Test database setup
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://zyplat:zyplat@localhost:5432/zyplat_test"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def snapshot_factory(db_session):
    """Return a builder that persists a company, domain, instance, and one empty snapshot.

    The TIME_SERIES domain has dimensions ``account`` (STRING, required), ``period`` (DATE,
    required), ``tags`` (ARRAY_STRING, optional) and metrics ``amount`` (DECIMAL, required),
    ``units`` (INTEGER, optional).
    """

    def build(kind: DomainKind = DomainKind.TIME_SERIES) -> DomainInstanceSnapshot:
        suffix = uuid.uuid4().hex[:8]
        company = Company(
            company_id=f"CO-{suffix}",
            name=f"Company {suffix}",
            company_type=CompanyType.BORROWER,
        )
        definition = DomainDefinition(
            domain_id=f"GL-{suffix}",
            description="General ledger",
            kind=kind,
            scope_type=DefinitionScope.GLOBAL,
            dimensions=[
                _dimension("account", DomainDimensionDataType.STRING, True, 1),
                _dimension("period", DomainDimensionDataType.DATE, True, 2),
                _dimension("tags", DomainDimensionDataType.ARRAY_STRING, False, 3),
            ],
            metrics=[
                _metric("amount", DomainMetricDataType.DECIMAL, True, 1),
                _metric("units", DomainMetricDataType.INTEGER, False, 2),
            ],
        )
        db_session.add_all([company, definition])
        db_session.flush()

        instance = DomainInstance(domain_definition_id=definition.id, company_id=company.id)
        db_session.add(instance)
        db_session.flush()

        company_snapshot = CompanySnapshot(
            company_id=company.id, period_type=PeriodGranularity.YEAR, period_value="2026", ord=1
        )
        db_session.add(company_snapshot)
        db_session.flush()

        snapshot = DomainInstanceSnapshot(
            domain_instance_id=instance.id, company_snapshot_id=company_snapshot.id
        )
        db_session.add(snapshot)
        db_session.flush()
        return snapshot

    return build


@pytest.fixture
def gl_frame() -> pd.DataFrame:
    """Rows that satisfy the domain built by ``snapshot_factory``."""
    return pd.DataFrame(
        {
            "account": ["1000", "2000"],
            "period": [date(2026, 1, 1), date(2026, 2, 1)],
            "amount": [Decimal("10.50"), Decimal("-3.25")],
            "units": [1, None],
        }
    )


def _dimension(name: str, data_type, required: bool, ordinal: int) -> DomainDimension:
    return DomainDimension(
        name=name,
        display_name=name.title(),
        data_type=data_type,
        required=required,
        ordinal=ordinal,
    )


def _metric(name: str, data_type, required: bool, ordinal: int) -> DomainMetric:
    return DomainMetric(
        name=name,
        display_name=name.title(),
        data_type=data_type,
        required=required,
        ordinal=ordinal,
    )
