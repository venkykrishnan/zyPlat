import pytest
from fastapi.testclient import TestClient

from zyplat.app import create_app


@pytest.fixture
def client():
    app = create_app("sqlite:///:memory:")
    with TestClient(app) as test_client:
        yield test_client
