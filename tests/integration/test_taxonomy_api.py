"""Integration tests for taxonomy API endpoints."""

import pytest
from fastapi import status


class TestTaxonomyDefinitionAPI:
    """Test /api/v1/taxonomies/definitions endpoints."""

    def test_create_taxonomy_definition(self, client):
        """Test POST /api/v1/taxonomies/definitions - Create taxonomy definition."""
        payload = {
            "taxonomy_id": "accountType",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "owner_company_id": None,
            "description": "Chart of Account Types",
            "is_hierarchical": True,
            "allowed_classifications": ["GAAP", "IFRS"],
        }

        response = client.post("/api/v1/taxonomies/definitions", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["taxonomy_id"] == "accountType"
        assert data["version"] == "1.0.0"
        assert data["scope_type"] == "GLOBAL"
        assert data["is_hierarchical"] is True
        assert "GAAP" in data["allowed_classifications"]
        assert "id" in data
        assert "created_at" in data

    def test_create_company_scoped_taxonomy(self, client):
        """Test creating a company-scoped taxonomy."""
        # Create company first
        company_payload = {
            "company_id": "LEND001",
            "name": "Test Lender",
            "company_type": "LENDER",
            "description": "Test lender company",
        }
        company_response = client.post("/api/v1/companies", json=company_payload)
        company_uuid = company_response.json()["id"]

        # Create company-scoped taxonomy
        taxonomy_payload = {
            "taxonomy_id": "customAccounts",
            "version": "1.0.0",
            "scope_type": "COMPANY",
            "owner_company_id": company_uuid,
            "description": "Custom Account Types",
            "is_hierarchical": False,
            "allowed_classifications": ["CIQ"],
        }
        response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["scope_type"] == "COMPANY"
        assert data["owner_company_id"] == company_uuid

    def test_list_taxonomy_definitions(self, client):
        """Test GET /api/v1/taxonomies/definitions - List all taxonomies."""
        # Create a few taxonomies
        taxonomies = [
            {
                "taxonomy_id": "accountType",
                "version": "1.0.0",
                "scope_type": "GLOBAL",
                "description": "Account Types",
                "is_hierarchical": True,
                "allowed_classifications": ["GAAP"],
            },
            {
                "taxonomy_id": "loanType",
                "version": "1.0.0",
                "scope_type": "GLOBAL",
                "description": "Loan Types",
                "is_hierarchical": False,
                "allowed_classifications": ["CIQ"],
            },
        ]

        for taxonomy_data in taxonomies:
            client.post("/api/v1/taxonomies/definitions", json=taxonomy_data)

        # List taxonomies
        response = client.get("/api/v1/taxonomies/definitions")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        taxonomy_ids = [t["taxonomy_id"] for t in data]
        assert "accountType" in taxonomy_ids
        assert "loanType" in taxonomy_ids

    def test_get_taxonomy_definition(self, client):
        """Test GET /api/v1/taxonomies/definitions/{id} - Get specific taxonomy."""
        # Create taxonomy
        payload = {
            "taxonomy_id": "testTaxonomy",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Test Taxonomy",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        create_response = client.post("/api/v1/taxonomies/definitions", json=payload)
        taxonomy_id = create_response.json()["id"]

        # Get taxonomy
        response = client.get(f"/api/v1/taxonomies/definitions/{taxonomy_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == taxonomy_id
        assert data["taxonomy_id"] == "testTaxonomy"

    def test_get_nonexistent_taxonomy(self, client):
        """Test GET for non-existent taxonomy returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/taxonomies/definitions/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_taxonomy_definition(self, client):
        """Test PUT /api/v1/taxonomies/definitions/{id} - Update taxonomy."""
        # Create taxonomy
        payload = {
            "taxonomy_id": "updateTest",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Original Description",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        create_response = client.post("/api/v1/taxonomies/definitions", json=payload)
        taxonomy_id = create_response.json()["id"]

        # Update taxonomy
        update_payload = {
            "description": "Updated Description",
            "is_published": True,
        }
        response = client.put(
            f"/api/v1/taxonomies/definitions/{taxonomy_id}", json=update_payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated Description"
        assert data["is_published"] is True

    def test_delete_taxonomy_definition(self, client):
        """Test DELETE /api/v1/taxonomies/definitions/{id} - Delete taxonomy."""
        # Create taxonomy
        payload = {
            "taxonomy_id": "deleteTest",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "To be deleted",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        create_response = client.post("/api/v1/taxonomies/definitions", json=payload)
        taxonomy_id = create_response.json()["id"]

        # Delete taxonomy
        response = client.delete(f"/api/v1/taxonomies/definitions/{taxonomy_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        get_response = client.get(f"/api/v1/taxonomies/definitions/{taxonomy_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestTaxonomyEntityAPI:
    """Test /api/v1/taxonomies/entities endpoints."""

    def test_create_taxonomy_entity(self, client):
        """Test POST /api/v1/taxonomies/entities - Create taxonomy entity."""
        # Create taxonomy definition first
        taxonomy_payload = {
            "taxonomy_id": "accountType",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Account Types",
            "is_hierarchical": True,
            "allowed_classifications": ["GAAP"],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        taxonomy_def_id = taxonomy_response.json()["id"]

        # Create entity
        entity_payload = {
            "taxonomy_definition_id": taxonomy_def_id,
            "entity_id": "ASSET",
            "value": "asset",
            "display_name": "Asset",
            "description": "Asset accounts",
            "explicit_classifications": ["GAAP"],
        }
        response = client.post("/api/v1/taxonomies/entities", json=entity_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["entity_id"] == "ASSET"
        assert data["value"] == "asset"
        assert data["display_name"] == "Asset"
        assert "id" in data

    def test_create_hierarchical_entities(self, client):
        """Test creating parent-child taxonomy entities."""
        # Create taxonomy
        taxonomy_payload = {
            "taxonomy_id": "accountType",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Account Types",
            "is_hierarchical": True,
            "allowed_classifications": [],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        taxonomy_def_id = taxonomy_response.json()["id"]

        # Create parent entity
        parent_payload = {
            "taxonomy_definition_id": taxonomy_def_id,
            "entity_id": "ASSET",
            "value": "asset",
            "display_name": "Asset",
            "description": "Asset accounts",
            "explicit_classifications": [],
        }
        parent_response = client.post("/api/v1/taxonomies/entities", json=parent_payload)
        parent_id = parent_response.json()["id"]

        # Create child entity
        child_payload = {
            "taxonomy_definition_id": taxonomy_def_id,
            "entity_id": "CURRENT_ASSET",
            "value": "current_asset",
            "display_name": "Current Asset",
            "description": "Current asset accounts",
            "parent_entity_id": parent_id,
            "explicit_classifications": [],
        }
        response = client.post("/api/v1/taxonomies/entities", json=child_payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["parent_entity_id"] == parent_id

    def test_list_taxonomy_entities(self, client):
        """Test GET /api/v1/taxonomies/definitions/{id}/entities - List entities."""
        # Create taxonomy
        taxonomy_payload = {
            "taxonomy_id": "entityList",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Test",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        taxonomy_def_id = taxonomy_response.json()["id"]

        # Create entities
        entities = ["ASSET", "LIABILITY", "EQUITY"]
        for entity_id in entities:
            entity_payload = {
                "taxonomy_definition_id": taxonomy_def_id,
                "entity_id": entity_id,
                "value": entity_id.lower(),
                "display_name": entity_id.title(),
                "description": f"{entity_id.title()} accounts",
                "explicit_classifications": [],
            }
            client.post("/api/v1/taxonomies/entities", json=entity_payload)

        # List entities
        response = client.get(f"/api/v1/taxonomies/definitions/{taxonomy_def_id}/entities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        entity_ids = [e["entity_id"] for e in data]
        assert "ASSET" in entity_ids
        assert "LIABILITY" in entity_ids
        assert "EQUITY" in entity_ids

    def test_update_taxonomy_entity(self, client):
        """Test PUT /api/v1/taxonomies/entities/{id} - Update entity."""
        # Create taxonomy and entity
        taxonomy_payload = {
            "taxonomy_id": "updateEntity",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Test",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        taxonomy_def_id = taxonomy_response.json()["id"]

        entity_payload = {
            "taxonomy_definition_id": taxonomy_def_id,
            "entity_id": "TEST",
            "value": "test",
            "display_name": "Original",
            "description": "Original description",
            "explicit_classifications": [],
        }
        entity_response = client.post("/api/v1/taxonomies/entities", json=entity_payload)
        entity_id = entity_response.json()["id"]

        # Update entity
        update_payload = {
            "display_name": "Updated",
            "description": "Updated description",
        }
        response = client.put(f"/api/v1/taxonomies/entities/{entity_id}", json=update_payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Updated"
        assert data["description"] == "Updated description"

    def test_delete_taxonomy_entity(self, client):
        """Test DELETE /api/v1/taxonomies/entities/{id} - Delete entity."""
        # Create taxonomy and entity
        taxonomy_payload = {
            "taxonomy_id": "deleteEntity",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Test",
            "is_hierarchical": False,
            "allowed_classifications": [],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        taxonomy_def_id = taxonomy_response.json()["id"]

        entity_payload = {
            "taxonomy_definition_id": taxonomy_def_id,
            "entity_id": "DELETE",
            "value": "delete",
            "display_name": "To Delete",
            "description": "To be deleted",
            "explicit_classifications": [],
        }
        entity_response = client.post("/api/v1/taxonomies/entities", json=entity_payload)
        entity_id = entity_response.json()["id"]

        # Delete entity
        response = client.delete(f"/api/v1/taxonomies/entities/{entity_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        get_response = client.get(f"/api/v1/taxonomies/entities/{entity_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestTaxonomyEndToEnd:
    """End-to-end tests for taxonomy workflows."""

    def test_complete_taxonomy_workflow(self, client):
        """Test complete workflow: create taxonomy with entities, update, query, delete."""
        # 1. Create taxonomy definition
        taxonomy_payload = {
            "taxonomy_id": "completeWorkflow",
            "version": "1.0.0",
            "scope_type": "GLOBAL",
            "description": "Complete workflow test",
            "is_hierarchical": True,
            "allowed_classifications": ["GAAP", "IFRS"],
        }
        taxonomy_response = client.post("/api/v1/taxonomies/definitions", json=taxonomy_payload)
        assert taxonomy_response.status_code == status.HTTP_201_CREATED
        taxonomy_id = taxonomy_response.json()["id"]

        # 2. Create parent entity
        parent_payload = {
            "taxonomy_definition_id": taxonomy_id,
            "entity_id": "BALANCE_SHEET",
            "value": "balance_sheet",
            "display_name": "Balance Sheet",
            "description": "Balance sheet accounts",
            "explicit_classifications": ["GAAP"],
        }
        parent_response = client.post("/api/v1/taxonomies/entities", json=parent_payload)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        # 3. Create child entities
        children = ["ASSET", "LIABILITY", "EQUITY"]
        for child_entity_id in children:
            child_payload = {
                "taxonomy_definition_id": taxonomy_id,
                "entity_id": child_entity_id,
                "value": child_entity_id.lower(),
                "display_name": child_entity_id.title(),
                "description": f"{child_entity_id.title()} accounts",
                "parent_entity_id": parent_id,
                "explicit_classifications": ["GAAP"],
            }
            response = client.post("/api/v1/taxonomies/entities", json=child_payload)
            assert response.status_code == status.HTTP_201_CREATED

        # 4. List entities
        list_response = client.get(f"/api/v1/taxonomies/definitions/{taxonomy_id}/entities")
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.json()) == 4  # 1 parent + 3 children

        # 5. Publish taxonomy
        update_payload = {"is_published": True}
        update_response = client.put(
            f"/api/v1/taxonomies/definitions/{taxonomy_id}", json=update_payload
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["is_published"] is True

        # 6. Delete taxonomy (cascade deletes entities)
        delete_response = client.delete(f"/api/v1/taxonomies/definitions/{taxonomy_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 7. Verify it's gone
        get_response = client.get(f"/api/v1/taxonomies/definitions/{taxonomy_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
