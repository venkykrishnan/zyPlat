"""Integration tests for application validation, lifecycle, and bind rules (plan section 9)."""

from uuid import UUID

from fastapi import status

from tests.integration.test_application_api import (
    _app_payload,
    _create_bbc_domain,
    _create_company,
    _create_gl_domain,
)

_GL_EXPECTED = {
    "kind": "TIME_SERIES",
    "time_series_dimension": "period",
    "period_type": "MONTH",
    "dimensions": [
        {"name": "period", "data_type": "DATETIME"},
        {"name": "account", "data_type": "STRING"},
    ],
    "metrics": [{"name": "amount", "data_type": "NUMBER"}],
}


def _gl_domains(expected=None):
    return [{"domain_id": "GL", "role": "INPUT", "expected": expected or _GL_EXPECTED}]


def _create_app(client, expected=None):
    return client.post("/api/v1/applications", json=_app_payload(_gl_domains(expected)))


def test_create_fails_on_kind_mismatch(client):
    _create_gl_domain(client)
    response = _create_app(client, {**_GL_EXPECTED, "kind": "SCALAR"})
    assert response.status_code in {422, 400}


def test_create_fails_on_dimension_type_mismatch(client):
    _create_gl_domain(client)
    bad = {
        **_GL_EXPECTED,
        "dimensions": [
            {"name": "period", "data_type": "DATETIME"},
            {"name": "account", "data_type": "NUMBER"},
        ],
    }
    assert _create_app(client, bad).status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_fails_on_missing_expected_dimension(client):
    _create_gl_domain(client)
    bad = {
        **_GL_EXPECTED,
        "dimensions": _GL_EXPECTED["dimensions"] + [{"name": "nope", "data_type": "STRING"}],
    }
    assert _create_app(client, bad).status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_fails_on_period_type_mismatch(client):
    _create_gl_domain(client)
    bad = {**_GL_EXPECTED, "period_type": "DATE"}
    assert _create_app(client, bad).status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_allows_extra_domain_fields(client):
    """The domain may have more dimensions/metrics than the application requires."""
    _create_gl_domain(client)
    subset = {**_GL_EXPECTED, "dimensions": [{"name": "period", "data_type": "DATETIME"}]}
    assert _create_app(client, subset).status_code == status.HTTP_201_CREATED


def test_duplicate_application_and_version_conflict(client):
    _create_gl_domain(client)
    assert _create_app(client).status_code == status.HTTP_201_CREATED
    assert _create_app(client).status_code == status.HTTP_409_CONFLICT
    dup_version = client.post(
        "/api/v1/applications/LoanMonitoring/versions",
        json={"version": "1.0.0", "name": "dup", "domains": _gl_domains()},
    )
    assert dup_version.status_code == status.HTTP_409_CONFLICT


def test_lifecycle_transitions(client):
    _create_gl_domain(client)
    _create_app(client)
    base = "/api/v1/applications/LoanMonitoring"

    published = client.post(f"{base}/publish")
    assert published.status_code == status.HTTP_200_OK
    assert published.json()["status"] == "PUBLISHED"

    unpublished = client.post(f"{base}/unpublish")
    assert unpublished.status_code == status.HTTP_200_OK
    assert unpublished.json()["status"] == "DRAFT"

    archived = client.post(f"{base}/archive")
    assert archived.status_code == status.HTTP_200_OK
    assert archived.json()["status"] == "ARCHIVED"

    # ARCHIVED is read-only.
    assert client.post(f"{base}/publish").status_code == status.HTTP_409_CONFLICT


def test_enable_unknown_company_is_404(client):
    _create_gl_domain(client)
    _create_app(client)
    response = client.put("/api/v1/applications/LoanMonitoring/versions/1.0.0/companies/Ghost")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_bind_without_company_enablement_conflicts(client):
    _create_company(client)
    _create_gl_domain(client)
    _create_app(client)
    client.post("/api/v1/applications/LoanMonitoring/publish")
    response = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "period_type": "MONTH",
            "period_value": "2026-07",
            "members": [],
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def _published_app_with_company(client):
    company = _create_company(client)
    gl = _create_gl_domain(client)
    _create_app(client)
    client.post("/api/v1/applications/LoanMonitoring/publish")
    client.put("/api/v1/applications/LoanMonitoring/versions/1.0.0/companies/NorthCo")
    return company, gl


def test_bind_missing_company_tied_input_snapshot_is_422(client):
    company, _ = _published_app_with_company(client)
    client.post(
        f"/api/v1/companies/{company['id']}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    )
    response = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "period_type": "MONTH",
            "period_value": "2026-07",
            "members": [],
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text


def test_bind_duplicate_and_disable_company_conflict(client, db_session):
    from backend.app.models.domain import DomainInstance, DomainInstanceSnapshot

    company, gl = _published_app_with_company(client)
    snap = client.post(
        f"/api/v1/companies/{company['id']}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    ).json()
    instance = DomainInstance(domain_definition_id=UUID(gl["id"]), company_id=UUID(company["id"]))
    db_session.add(instance)
    db_session.flush()
    gl_snap = DomainInstanceSnapshot(
        domain_instance_id=instance.id, company_snapshot_id=UUID(snap["id"])
    )
    db_session.add(gl_snap)
    db_session.flush()

    body = {
        "company_id": "NorthCo",
        "company_snapshot_id": snap["id"],
        "members": [{"domain_id": "GL", "domain_instance_snapshot_id": str(gl_snap.id)}],
    }
    url = "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances"
    assert client.post(url, json=body).status_code == status.HTTP_201_CREATED

    # Disable runs before the duplicate-bind check: that path rolls back the shared test
    # transaction.
    disable = client.delete("/api/v1/applications/LoanMonitoring/versions/1.0.0/companies/NorthCo")
    assert disable.status_code == status.HTTP_409_CONFLICT, disable.text
    assert client.post(url, json=body).status_code == status.HTTP_409_CONFLICT


def test_bbc_snapshot_without_company_snapshot_and_duplicate_member(client, db_session):
    """BBC date snapshots may have no company snapshot; listing a domain's snapshot twice is 422."""
    from backend.app.models.company import PeriodGranularity
    from backend.app.models.domain import DomainInstance, DomainInstanceSnapshot

    company = _create_company(client)
    gl = _create_gl_domain(client)
    bbc = _create_bbc_domain(client)
    client.post(
        "/api/v1/applications",
        json=_app_payload(
            _gl_domains()
            + [
                {
                    "domain_id": "BBC",
                    "role": "INPUT",
                    "snapshot_alignment": "INDEPENDENT",
                    "expected": {
                        "kind": "TIME_SERIES",
                        "time_series_dimension": "period",
                        "period_type": "DATE",
                        "dimensions": [{"name": "period", "data_type": "DATETIME"}],
                        "metrics": [{"name": "amount", "data_type": "NUMBER"}],
                    },
                }
            ]
        ),
    )
    client.post("/api/v1/applications/LoanMonitoring/publish")
    client.put("/api/v1/applications/LoanMonitoring/versions/1.0.0/companies/NorthCo")
    snap = client.post(
        f"/api/v1/companies/{company['id']}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    ).json()

    cid = UUID(company["id"])
    gl_inst = DomainInstance(domain_definition_id=UUID(gl["id"]), company_id=cid)
    bbc_inst = DomainInstance(domain_definition_id=UUID(bbc["id"]), company_id=cid)
    db_session.add_all([gl_inst, bbc_inst])
    db_session.flush()
    gl_a = DomainInstanceSnapshot(
        domain_instance_id=gl_inst.id, company_snapshot_id=UUID(snap["id"])
    )
    bbc_snap = DomainInstanceSnapshot(
        domain_instance_id=bbc_inst.id,
        company_snapshot_id=None,
        snapshot_period_type=PeriodGranularity.DATE,
        snapshot_period_value="2026-07-05",
    )
    db_session.add_all([gl_a, bbc_snap])
    db_session.flush()
    assert bbc_snap.company_snapshot_id is None

    response = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "company_snapshot_id": snap["id"],
            "members": [
                {"domain_id": "GL", "domain_instance_snapshot_id": str(gl_a.id)},
                {"domain_id": "GL", "domain_instance_snapshot_id": str(gl_a.id)},
            ],
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text
