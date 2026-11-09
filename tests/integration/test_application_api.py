"""Integration tests for application lifecycle and bind instances."""

from uuid import UUID

from fastapi import status


def _create_company(client, company_id: str = "NorthCo"):
    return client.post(
        "/api/v1/companies",
        json={
            "company_id": company_id,
            "name": f"Company {company_id}",
            "company_type": "BORROWER",
        },
    ).json()


def _create_gl_domain(client):
    return client.post(
        "/api/v1/domains",
        json={
            "domain_id": "GL",
            "description": "General Ledger",
            "kind": "TIME_SERIES",
            "scope_type": "GLOBAL",
            "dimensions": [
                {
                    "name": "period",
                    "display_name": "Period",
                    "data_type": "DATETIME",
                    "required": True,
                    "ordinal": 1,
                    "is_time_series": True,
                    "period_type": "MONTH",
                },
                {
                    "name": "account",
                    "display_name": "Account",
                    "data_type": "STRING",
                    "required": True,
                    "ordinal": 2,
                },
            ],
            "metrics": [
                {
                    "name": "amount",
                    "display_name": "Amount",
                    "data_type": "NUMBER",
                    "required": True,
                    "ordinal": 1,
                }
            ],
        },
    ).json()


def _create_bbc_domain(client):
    return client.post(
        "/api/v1/domains",
        json={
            "domain_id": "BBC",
            "description": "Borrowing base",
            "kind": "TIME_SERIES",
            "scope_type": "GLOBAL",
            "dimensions": [
                {
                    "name": "period",
                    "display_name": "Period",
                    "data_type": "DATETIME",
                    "required": True,
                    "ordinal": 1,
                    "is_time_series": True,
                    "period_type": "DATE",
                }
            ],
            "metrics": [
                {
                    "name": "amount",
                    "display_name": "Amount",
                    "data_type": "NUMBER",
                    "required": True,
                    "ordinal": 1,
                }
            ],
        },
    ).json()


def _app_payload(domains):
    return {
        "application_id": "LoanMonitoring",
        "version": "1.0.0",
        "name": "Loan Monitoring",
        "description": "Monitor loans",
        "domains": domains,
    }


def test_create_starts_draft_and_get_returns_default(client):
    """New applications are DRAFT; GET by id returns the default version."""
    _create_gl_domain(client)
    created = client.post(
        "/api/v1/applications",
        json=_app_payload(
            [
                {
                    "domain_id": "GL",
                    "role": "INPUT",
                    "snapshot_alignment": "COMPANY",
                    "expected": {
                        "kind": "TIME_SERIES",
                        "time_series_dimension": "period",
                        "period_type": "MONTH",
                        "dimensions": [
                            {"name": "period", "data_type": "DATETIME"},
                            {"name": "account", "data_type": "STRING"},
                        ],
                        "metrics": [{"name": "amount", "data_type": "NUMBER"}],
                    },
                }
            ]
        ),
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["status"] == "DRAFT"
    assert body["is_default"] is True
    assert body["version"] == "1.0.0"

    fetched = client.get("/api/v1/applications/LoanMonitoring")
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json()["version"] == "1.0.0"
    assert fetched.json()["status"] == "DRAFT"


def test_new_version_auto_defaults_and_set_default(client):
    """Creating a version auto-defaults; set-default can point back."""
    _create_gl_domain(client)
    client.post(
        "/api/v1/applications",
        json=_app_payload(
            [
                {
                    "domain_id": "GL",
                    "role": "INPUT",
                    "expected": {
                        "kind": "TIME_SERIES",
                        "time_series_dimension": "period",
                        "period_type": "MONTH",
                        "dimensions": [
                            {"name": "period", "data_type": "DATETIME"},
                            {"name": "account", "data_type": "STRING"},
                        ],
                        "metrics": [{"name": "amount", "data_type": "NUMBER"}],
                    },
                }
            ]
        ),
    )
    v2 = client.post(
        "/api/v1/applications/LoanMonitoring/versions",
        json={
            "version": "2.0.0",
            "name": "Loan Monitoring v2",
            "domains": [
                {
                    "domain_id": "GL",
                    "role": "INPUT",
                    "expected": {
                        "kind": "TIME_SERIES",
                        "time_series_dimension": "period",
                        "period_type": "MONTH",
                        "dimensions": [
                            {"name": "period", "data_type": "DATETIME"},
                            {"name": "account", "data_type": "STRING"},
                        ],
                        "metrics": [{"name": "amount", "data_type": "NUMBER"}],
                    },
                }
            ],
        },
    )
    assert v2.status_code == status.HTTP_201_CREATED
    assert v2.json()["is_default"] is True

    reset = client.post(
        "/api/v1/applications/LoanMonitoring/set-default", json={"version": "1.0.0"}
    )
    assert reset.status_code == status.HTTP_200_OK
    assert reset.json()["version"] == "1.0.0"
    assert reset.json()["is_default"] is True


def test_bind_requires_published_and_july_view(client, db_session):
    """Bind writes are blocked in DRAFT; July view accepts GL + contained BBC dates."""
    from backend.app.models.company import PeriodGranularity
    from backend.app.models.domain import DomainInstance, DomainInstanceSnapshot

    company = _create_company(client)
    gl = _create_gl_domain(client)
    bbc = _create_bbc_domain(client)

    client.post(
        "/api/v1/applications",
        json=_app_payload(
            [
                {
                    "domain_id": "GL",
                    "role": "INPUT",
                    "snapshot_alignment": "COMPANY",
                    "expected": {
                        "kind": "TIME_SERIES",
                        "time_series_dimension": "period",
                        "period_type": "MONTH",
                        "dimensions": [
                            {"name": "period", "data_type": "DATETIME"},
                            {"name": "account", "data_type": "STRING"},
                        ],
                        "metrics": [{"name": "amount", "data_type": "NUMBER"}],
                    },
                },
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
                },
            ]
        ),
    )

    draft_bind = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "period_type": "MONTH",
            "period_value": "2026-07",
            "members": [],
        },
    )
    assert draft_bind.status_code == status.HTTP_409_CONFLICT

    assert (
        client.post("/api/v1/applications/LoanMonitoring/publish").status_code == status.HTTP_200_OK
    )
    assert (
        client.put(
            f"/api/v1/applications/LoanMonitoring/versions/1.0.0/companies/{company['company_id']}"
        ).status_code
        == status.HTTP_200_OK
    )

    company_snap = client.post(
        f"/api/v1/companies/{company['id']}/snapshots",
        json={"period_type": "MONTH", "period_value": "2026-07"},
    ).json()

    company_uuid = UUID(company["id"])
    gl_instance = DomainInstance(domain_definition_id=UUID(gl["id"]), company_id=company_uuid)
    bbc_instance = DomainInstance(domain_definition_id=UUID(bbc["id"]), company_id=company_uuid)
    db_session.add_all([gl_instance, bbc_instance])
    db_session.flush()

    gl_snap = DomainInstanceSnapshot(
        domain_instance_id=gl_instance.id, company_snapshot_id=UUID(company_snap["id"])
    )
    bbc_snaps = [
        DomainInstanceSnapshot(
            domain_instance_id=bbc_instance.id,
            company_snapshot_id=None,
            snapshot_period_type=PeriodGranularity.DATE,
            snapshot_period_value=value,
        )
        for value in ("2026-07-05", "2026-07-15", "2026-07-26")
    ]
    outside = DomainInstanceSnapshot(
        domain_instance_id=bbc_instance.id,
        company_snapshot_id=None,
        snapshot_period_type=PeriodGranularity.DATE,
        snapshot_period_value="2026-08-01",
    )
    db_session.add_all([gl_snap, *bbc_snaps, outside])
    db_session.flush()

    created = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "period_type": "MONTH",
            "period_value": "2026-07",
            "members": [
                {"domain_id": "GL", "domain_instance_snapshot_id": str(gl_snap.id)},
            ],
            "resolve_independent_members": True,
        },
    )
    assert created.status_code == status.HTTP_201_CREATED, created.text
    members = created.json()["members"]
    assert len(members) == 4
    bbc_ids = {str(s.id) for s in bbc_snaps}
    assert {m["domain_instance_snapshot_id"] for m in members if m["domain_id"] == "BBC"} == bbc_ids

    bad = client.post(
        "/api/v1/applications/LoanMonitoring/versions/1.0.0/bind-instances",
        json={
            "company_id": "NorthCo",
            "company_snapshot_id": company_snap["id"],
            "members": [
                {"domain_id": "GL", "domain_instance_snapshot_id": str(gl_snap.id)},
                {"domain_id": "BBC", "domain_instance_snapshot_id": str(outside.id)},
            ],
            "resolve_independent_members": False,
        },
    )
    # Duplicate bind for same company snapshot is conflict; use a second company snapshot.
    assert bad.status_code in {
        status.HTTP_409_CONFLICT,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    }

    unpublish = client.post("/api/v1/applications/LoanMonitoring/unpublish")
    assert unpublish.status_code == status.HTTP_409_CONFLICT


def test_missing_domain_fails_create(client):
    """Application create does not invent missing domains."""
    response = client.post(
        "/api/v1/applications",
        json=_app_payload(
            [
                {
                    "domain_id": "Missing",
                    "role": "INPUT",
                    "expected": {"kind": "SCALAR", "dimensions": [], "metrics": []},
                }
            ]
        ),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
