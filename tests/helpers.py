"""Shared API builders for integration tests."""

from fastapi.testclient import TestClient


def publish_account_type(client: TestClient, name: str = "accountType") -> str:
    """Hierarchical account-type taxonomy used by the general-ledger story."""

    created = client.post(
        "/api/v1/taxonomies",
        json={
            "name": name,
            "description": "Account types",
            "isHierarchical": True,
            "allowedClassifications": ["CIQ", "EDGAR"],
        },
    )
    assert created.status_code == 201, created.text
    taxonomy_id = created.json()["id"]
    entities = [
        {"code": "accountType", "name": "Account Type", "classifications": []},
        {
            "code": "revenue",
            "name": "Revenue",
            "parentCode": "accountType",
            "classifications": ["CIQ", "EDGAR"],
        },
        {
            "code": "productRevenue",
            "name": "Product Revenue",
            "parentCode": "revenue",
            "classifications": [],
        },
        {"code": "expense", "name": "Expense", "parentCode": "accountType", "classifications": []},
        {
            "code": "edgarOnly",
            "name": "EDGAR only",
            "parentCode": "accountType",
            "classifications": ["EDGAR"],
        },
    ]
    for entity in entities:
        response = client.post(f"/api/v1/taxonomies/{taxonomy_id}/entities", json=entity)
        assert response.status_code == 201, response.text
    published = client.post(f"/api/v1/taxonomies/{taxonomy_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["latestVersion"]["status"] == "published"
    return taxonomy_id
