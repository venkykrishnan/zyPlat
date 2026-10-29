"""Integration tests for domain API endpoints."""

import pytest
from fastapi import status


class TestDomainDefinitionAPI:
    """Test /api/v1/domains endpoints."""

    def test_create_domain_definition(self, client):
        """Test POST /api/v1/domains - Create domain definition."""
        payload = {
            "domain_id": "GL",
            "description": "General Ledger",
            "kind": "TIME_SERIES",
            "scope_type": "GLOBAL",
            "owner_company_id": None,
        }

        response = client.post("/api/v1/domains", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["domain_id"] == "GL"
        assert data["kind"] == "TIME_SERIES"
        assert data["scope_type"] == "GLOBAL"
        assert "id" in data
        assert "created_at" in data

    def test_create_scalar_domain(self, client):
        """Test creating a scalar domain."""
        payload = {
            "domain_id": "CompanyInfo",
            "description": "Company Information",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
        }

        response = client.post("/api/v1/domains", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["kind"] == "SCALAR"

    def test_list_domain_definitions(self, client):
        """Test GET /api/v1/domains - List all domains."""
        # Create a few domains first
        domains = [
            {
                "domain_id": "GL",
                "description": "General Ledger",
                "kind": "TIME_SERIES",
                "scope_type": "GLOBAL",
            },
            {
                "domain_id": "LoanPayment",
                "description": "Loan Payments",
                "kind": "TIME_SERIES",
                "scope_type": "GLOBAL",
            },
        ]

        for domain_data in domains:
            client.post("/api/v1/domains", json=domain_data)

        # List domains
        response = client.get("/api/v1/domains")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        domain_ids = [d["domain_id"] for d in data]
        assert "GL" in domain_ids
        assert "LoanPayment" in domain_ids

    def test_get_domain_definition(self, client):
        """Test GET /api/v1/domains/{id} - Get specific domain."""
        # Create domain
        payload = {
            "domain_id": "TestDomain",
            "description": "Test Domain",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
        }
        create_response = client.post("/api/v1/domains", json=payload)
        domain_id = create_response.json()["id"]

        # Get domain
        response = client.get(f"/api/v1/domains/{domain_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == domain_id
        assert data["domain_id"] == "TestDomain"

    def test_get_nonexistent_domain(self, client):
        """Test GET for non-existent domain returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/domains/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_domain_definition(self, client):
        """Test PUT /api/v1/domains/{id} - Update domain."""
        # Create domain
        payload = {
            "domain_id": "UpdateTest",
            "description": "Original Description",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
        }
        create_response = client.post("/api/v1/domains", json=payload)
        domain_id = create_response.json()["id"]

        # Update domain
        update_payload = {"description": "Updated Description"}
        response = client.put(f"/api/v1/domains/{domain_id}", json=update_payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated Description"
        assert data["domain_id"] == "UpdateTest"  # Unchanged

    def test_delete_domain_definition(self, client):
        """Test DELETE /api/v1/domains/{id} - Delete domain."""
        # Create domain
        payload = {
            "domain_id": "DeleteTest",
            "description": "To be deleted",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
        }
        create_response = client.post("/api/v1/domains", json=payload)
        domain_id = create_response.json()["id"]

        # Delete domain
        response = client.delete(f"/api/v1/domains/{domain_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        get_response = client.get(f"/api/v1/domains/{domain_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_company_scoped_domain(self, client):
        """Test creating a company-scoped domain."""
        # First create a company
        company_payload = {
            "company_id": "LEND001",
            "name": "Test Lender",
            "company_type": "LENDER",
            "description": "Test lender company",
        }
        company_response = client.post("/api/v1/companies", json=company_payload)
        company_uuid = company_response.json()["id"]

        # Create company-scoped domain
        domain_payload = {
            "domain_id": "CustomGL",
            "description": "Custom General Ledger",
            "kind": "TIME_SERIES",
            "scope_type": "COMPANY",
            "owner_company_id": company_uuid,
        }
        response = client.post("/api/v1/domains", json=domain_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["scope_type"] == "COMPANY"
        assert data["owner_company_id"] == company_uuid


class TestDomainValidation:
    """Test domain validation rules."""

    def test_time_series_vs_scalar_kinds(self, client):
        """Test that both TIME_SERIES and SCALAR kinds are accepted."""
        time_series = {
            "domain_id": "TimeSeries1",
            "description": "Time Series Domain",
            "kind": "TIME_SERIES",
            "scope_type": "GLOBAL",
        }
        scalar = {
            "domain_id": "Scalar1",
            "description": "Scalar Domain",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
        }

        response1 = client.post("/api/v1/domains", json=time_series)
        response2 = client.post("/api/v1/domains", json=scalar)

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        assert response1.json()["kind"] == "TIME_SERIES"
        assert response2.json()["kind"] == "SCALAR"

    def test_global_vs_company_scopes(self, client):
        """Test GLOBAL and COMPANY scope types."""
        # Global domain
        global_domain = {
            "domain_id": "GlobalDomain",
            "description": "Global",
            "kind": "SCALAR",
            "scope_type": "GLOBAL",
            "owner_company_id": None,
        }

        response = client.post("/api/v1/domains", json=global_domain)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["scope_type"] == "GLOBAL"


class TestDomainEndToEnd:
    """End-to-end tests for domain workflows."""

    def test_complete_domain_workflow(self, client):
        """Test complete workflow: create domain, list, update, get, delete."""
        # 1. Create domain
        create_payload = {
            "domain_id": "WorkflowDomain",
            "description": "Test workflow",
            "kind": "TIME_SERIES",
            "scope_type": "GLOBAL",
        }
        create_response = client.post("/api/v1/domains", json=create_payload)
        assert create_response.status_code == status.HTTP_201_CREATED
        domain_id = create_response.json()["id"]

        # 2. List domains - verify it's there
        list_response = client.get("/api/v1/domains")
        assert list_response.status_code == status.HTTP_200_OK
        domain_ids = [d["id"] for d in list_response.json()]
        assert domain_id in domain_ids

        # 3. Update domain
        update_payload = {"description": "Updated description"}
        update_response = client.put(f"/api/v1/domains/{domain_id}", json=update_payload)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["description"] == "Updated description"

        # 4. Get specific domain
        get_response = client.get(f"/api/v1/domains/{domain_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["description"] == "Updated description"

        # 5. Delete domain
        delete_response = client.delete(f"/api/v1/domains/{domain_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify it's gone
        final_get = client.get(f"/api/v1/domains/{domain_id}")
        assert final_get.status_code == status.HTTP_404_NOT_FOUND
