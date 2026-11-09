"""Integration tests for company snapshot CRUD and default resolution."""

from fastapi import status


def test_create_snapshot_assigns_increasing_ord(client):
    """Each create for the same period gets the next ord; default is highest ord."""
    company = client.post(
        "/api/v1/companies",
        json={
            "company_id": "NorthCo",
            "name": "North Co",
            "company_type": "BORROWER",
        },
    ).json()
    company_id = company["id"]

    first = client.post(
        f"/api/v1/companies/{company_id}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    )
    second = client.post(
        f"/api/v1/companies/{company_id}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert first.json()["ord"] == 1
    assert second.json()["ord"] == 2

    default = client.get(
        f"/api/v1/companies/{company_id}/snapshots/default",
        params={"period_type": "MONTH", "period_value": "2026-07"},
    )
    assert default.status_code == status.HTTP_200_OK
    assert default.json()["ord"] == 2
    assert default.json()["id"] == second.json()["id"]


def test_invalid_period_value_is_rejected(client):
    """DB period regex surfaces as a validation error."""
    company = client.post(
        "/api/v1/companies",
        json={
            "company_id": "SouthCo",
            "name": "South Co",
            "company_type": "BORROWER",
        },
    ).json()

    response = client.post(
        f"/api/v1/companies/{company['id']}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026/07"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
