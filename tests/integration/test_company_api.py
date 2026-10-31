"""Integration tests for company API endpoints."""

import pytest
from fastapi import status


class TestCompanyAPI:
    """Test /api/v1/companies endpoints."""

    def test_create_company(self, client):
        """Test POST /api/v1/companies - Create company."""
        payload = {
            "company_id": "LEND001",
            "name": "First National Bank",
            "company_type": "LENDER",
            "description": "Large commercial lender",
            "customer_id": "CUST-12345",
            "is_enabled": True,
            "is_test": False,
            "naics_code": "522110",
            "state": "CA",
            "report_info": [{"type": "quarterly", "frequency": 4}],
            "metadata": {"founded": "1985", "employees": 5000},
        }

        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company_id"] == "LEND001"
        assert data["name"] == "First National Bank"
        assert data["company_type"] == "LENDER"
        assert data["customer_id"] == "CUST-12345"
        assert data["naics_code"] == "522110"
        assert data["state"] == "CA"
        assert "id" in data
        assert "created_at" in data

    def test_create_borrower_company(self, client):
        """Test creating a borrower company."""
        payload = {
            "company_id": "BORR001",
            "name": "Tech Startup Inc",
            "company_type": "BORROWER",
            "description": "Technology startup seeking financing",
        }

        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company_type"] == "BORROWER"

    def test_create_participant_company(self, client):
        """Test creating a participant company."""
        payload = {
            "company_id": "PART001",
            "name": "Syndication Partner Bank",
            "company_type": "PARTICIPANT",
            "description": "Loan syndication participant",
        }

        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company_type"] == "PARTICIPANT"

    def test_create_duplicate_company_id(self, client):
        """Test that duplicate company_id is rejected."""
        payload = {
            "company_id": "DUPE001",
            "name": "First Company",
            "company_type": "LENDER",
            "description": "First",
        }
        client.post("/api/v1/companies", json=payload)

        # Try to create with same company_id
        duplicate_payload = {
            "company_id": "DUPE001",
            "name": "Second Company",
            "company_type": "BORROWER",
            "description": "Second",
        }
        response = client.post("/api/v1/companies", json=duplicate_payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_list_companies(self, client):
        """Test GET /api/v1/companies - List all companies."""
        # Create several companies
        companies = [
            {
                "company_id": "LEND001",
                "name": "Lender Bank",
                "company_type": "LENDER",
                "description": "Lender",
            },
            {
                "company_id": "BORR001",
                "name": "Borrower Corp",
                "company_type": "BORROWER",
                "description": "Borrower",
            },
            {
                "company_id": "PART001",
                "name": "Participant Bank",
                "company_type": "PARTICIPANT",
                "description": "Participant",
            },
        ]

        for company_data in companies:
            client.post("/api/v1/companies", json=company_data)

        # List companies
        response = client.get("/api/v1/companies")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

        company_ids = [c["company_id"] for c in data]
        assert "LEND001" in company_ids
        assert "BORR001" in company_ids
        assert "PART001" in company_ids

    def test_list_companies_with_pagination(self, client):
        """Test listing companies with skip and limit parameters."""
        # Create multiple companies
        for i in range(5):
            payload = {
                "company_id": f"PAGE{i:03d}",
                "name": f"Company {i}",
                "company_type": "LENDER",
                "description": f"Company {i}",
            }
            client.post("/api/v1/companies", json=payload)

        # Test pagination
        response = client.get("/api/v1/companies?skip=2&limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 2

    def test_get_company(self, client):
        """Test GET /api/v1/companies/{id} - Get specific company."""
        # Create company
        payload = {
            "company_id": "GET001",
            "name": "Get Test Company",
            "company_type": "LENDER",
            "description": "Test",
        }
        create_response = client.post("/api/v1/companies", json=payload)
        company_id = create_response.json()["id"]

        # Get company
        response = client.get(f"/api/v1/companies/{company_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == company_id
        assert data["company_id"] == "GET001"

    def test_get_nonexistent_company(self, client):
        """Test GET for non-existent company returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/companies/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_company(self, client):
        """Test PUT /api/v1/companies/{id} - Update company."""
        # Create company
        payload = {
            "company_id": "UPDATE001",
            "name": "Original Company",
            "company_type": "LENDER",
            "description": "Original description",
            "is_enabled": True,
        }
        create_response = client.post("/api/v1/companies", json=payload)
        company_id = create_response.json()["id"]

        # Update company
        update_payload = {
            "description": "Updated description",
            "is_enabled": False,
            "naics_code": "522110",
        }
        response = client.put(f"/api/v1/companies/{company_id}", json=update_payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["is_enabled"] is False
        assert data["naics_code"] == "522110"
        assert data["company_id"] == "UPDATE001"  # Unchanged

    def test_delete_company(self, client):
        """Test DELETE /api/v1/companies/{id} - Delete company."""
        # Create company
        payload = {
            "company_id": "DELETE001",
            "name": "To Be Deleted",
            "company_type": "LENDER",
            "description": "Test",
        }
        create_response = client.post("/api/v1/companies", json=payload)
        company_id = create_response.json()["id"]

        # Delete company
        response = client.delete(f"/api/v1/companies/{company_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        get_response = client.get(f"/api/v1/companies/{company_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyTypes:
    """Test company type variants."""

    def test_all_company_types(self, client):
        """Test creating companies of all types."""
        types = ["LENDER", "BORROWER", "PARTICIPANT"]

        for idx, company_type in enumerate(types):
            payload = {
                "company_id": f"TYPE{idx:03d}",
                "name": f"{company_type} Company {idx}",
                "company_type": company_type,
                "description": f"{company_type} company",
            }
            response = client.post("/api/v1/companies", json=payload)

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["company_type"] == company_type


class TestCompanyFlags:
    """Test company flags (is_enabled, is_test)."""

    def test_create_test_company(self, client):
        """Test creating a test company."""
        payload = {
            "company_id": "TEST001",
            "name": "Test Company",
            "company_type": "LENDER",
            "description": "Test company for QA",
            "is_test": True,
        }
        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["is_test"] is True

    def test_create_disabled_company(self, client):
        """Test creating a disabled company."""
        payload = {
            "company_id": "DISABLED001",
            "name": "Disabled Company",
            "company_type": "LENDER",
            "description": "Disabled",
            "is_enabled": False,
        }
        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["is_enabled"] is False


class TestCompanyMetadata:
    """Test company metadata and report_info fields."""

    def test_company_with_report_info(self, client):
        """Test creating company with report_info."""
        payload = {
            "company_id": "REPORT001",
            "name": "Reporting Company",
            "company_type": "LENDER",
            "description": "Test",
            "report_info": [
                {"type": "quarterly", "frequency": 4},
                {"type": "annual", "frequency": 1},
            ],
        }
        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["report_info"]) == 2
        assert data["report_info"][0]["type"] == "quarterly"

    def test_company_with_metadata(self, client):
        """Test creating company with metadata."""
        payload = {
            "company_id": "META001",
            "name": "Metadata Company",
            "company_type": "LENDER",
            "description": "Test",
            "metadata": {
                "founded": "1985",
                "employees": 5000,
                "headquarters": "San Francisco, CA",
            },
        }
        response = client.post("/api/v1/companies", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["metadata"]["founded"] == "1985"
        assert data["metadata"]["employees"] == 5000

    def test_metadata_is_persisted_not_just_echoed(self, client):
        """A fresh GET must return what was created; the create response alone proves nothing."""
        payload = {
            "company_id": "META002",
            "name": "Persisted Metadata Company",
            "company_type": "LENDER",
            "metadata": {"founded": "1985"},
        }
        created = client.post("/api/v1/companies", json=payload).json()

        fetched = client.get(f"/api/v1/companies/{created['id']}").json()

        assert fetched["metadata"] == {"founded": "1985"}

    def test_update_replaces_metadata_and_persists_it(self, client):
        """Update must write metadata to the column, not onto the Python object."""
        payload = {
            "company_id": "META003",
            "name": "Updated Metadata Company",
            "company_type": "LENDER",
            "metadata": {"old": True},
        }
        created = client.post("/api/v1/companies", json=payload).json()

        client.put(f"/api/v1/companies/{created['id']}", json={"metadata": {"new": True}})

        fetched = client.get(f"/api/v1/companies/{created['id']}").json()
        assert fetched["metadata"] == {"new": True}

    def test_omitted_metadata_defaults_to_empty_object(self, client):
        """Responses must always include metadata as an object."""
        payload = {"company_id": "META004", "name": "No Metadata", "company_type": "LENDER"}

        created = client.post("/api/v1/companies", json=payload).json()

        assert created["metadata"] == {}


class TestCompanyEndToEnd:
    """End-to-end tests for company workflows."""

    def test_complete_company_workflow(self, client):
        """Test complete workflow: create, list, get, update, delete."""
        # 1. Create company
        create_payload = {
            "company_id": "WORKFLOW001",
            "name": "Workflow Test Bank",
            "company_type": "LENDER",
            "description": "Test workflow",
            "customer_id": "CUST-001",
            "naics_code": "522110",
            "state": "CA",
            "is_enabled": True,
            "is_test": False,
        }
        create_response = client.post("/api/v1/companies", json=create_payload)
        assert create_response.status_code == status.HTTP_201_CREATED
        company_id = create_response.json()["id"]

        # 2. List companies - verify it's there
        list_response = client.get("/api/v1/companies")
        assert list_response.status_code == status.HTTP_200_OK
        company_ids = [c["id"] for c in list_response.json()]
        assert company_id in company_ids

        # 3. Get specific company
        get_response = client.get(f"/api/v1/companies/{company_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["company_id"] == "WORKFLOW001"

        # 4. Update company
        update_payload = {
            "description": "Updated workflow test",
            "state": "NY",
            "metadata": {"updated": True},
        }
        update_response = client.put(f"/api/v1/companies/{company_id}", json=update_payload)
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["description"] == "Updated workflow test"
        assert update_response.json()["state"] == "NY"

        # 5. Delete company
        delete_response = client.delete(f"/api/v1/companies/{company_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify it's gone
        final_get = client.get(f"/api/v1/companies/{company_id}")
        assert final_get.status_code == status.HTTP_404_NOT_FOUND
