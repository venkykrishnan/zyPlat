"""Test configuration and fixtures."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test database URL
os.environ["DATABASE_URL"] = "postgresql://zyplat:zyplat@localhost:5432/zyplat_test"

from backend.app.core.database import Base, get_db
from backend.app.main import app


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
