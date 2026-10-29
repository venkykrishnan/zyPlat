"""Unit tests for taxonomy models."""

import pytest
from datetime import datetime, timezone
from backend.app.models.taxonomy import (
    TaxonomyDefinition,
    TaxonomyEntity,
    DefinitionScope,
)
from backend.app.models.company import Company, CompanyType


class TestTaxonomyDefinition:
    """Test TaxonomyDefinition model."""

    def test_create_global_taxonomy(self, db_session):
        """Test creating a global taxonomy definition."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="accountType",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Chart of Account Types",
            is_hierarchical=True,
            allowed_classifications=["GAAP", "IFRS"],
        )
        db_session.add(taxonomy)
        db_session.commit()

        assert taxonomy.id is not None
        assert taxonomy.taxonomy_id == "accountType"
        assert taxonomy.version == "1.0.0"
        assert taxonomy.scope_type == DefinitionScope.GLOBAL
        assert taxonomy.owner_company_id is None
        assert taxonomy.is_hierarchical is True
        assert "GAAP" in taxonomy.allowed_classifications
        assert taxonomy.is_published is False
        assert taxonomy.published_at is None
        assert taxonomy.is_default is False

    def test_create_company_scoped_taxonomy(self, db_session):
        """Test creating a company-scoped taxonomy."""
        # First create a company
        company = Company(
            company_id="LEND001",
            name="Test Lender",
            company_type=CompanyType.LENDER,
            description="Test lender company",
        )
        db_session.add(company)
        db_session.flush()

        # Create company-scoped taxonomy
        taxonomy = TaxonomyDefinition(
            taxonomy_id="customAccountType",
            version="1.0.0",
            scope_type=DefinitionScope.COMPANY,
            owner_company_id=company.id,
            description="Custom Account Types",
            is_hierarchical=False,
            allowed_classifications=["CIQ"],
        )
        db_session.add(taxonomy)
        db_session.commit()

        assert taxonomy.scope_type == DefinitionScope.COMPANY
        assert taxonomy.owner_company_id == company.id

    def test_global_taxonomy_cannot_have_owner(self, db_session):
        """Test that global taxonomies cannot have owner_company_id."""
        company = Company(
            company_id="BORR001",
            name="Test Borrower",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        # Global taxonomy with owner should violate constraint
        taxonomy = TaxonomyDefinition(
            taxonomy_id="badTaxonomy",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            owner_company_id=company.id,  # Invalid!
            description="Invalid",
        )
        db_session.add(taxonomy)

        with pytest.raises(Exception):  # Constraint violation
            db_session.commit()

    def test_company_taxonomy_must_have_owner(self, db_session):
        """Test that company-scoped taxonomies must have owner_company_id."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="badTaxonomy2",
            version="1.0.0",
            scope_type=DefinitionScope.COMPANY,
            owner_company_id=None,  # Invalid!
            description="Invalid",
        )
        db_session.add(taxonomy)

        with pytest.raises(Exception):  # Constraint violation
            db_session.commit()

    def test_publish_taxonomy(self, db_session):
        """Test publishing a taxonomy definition."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="publishTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Test",
        )
        db_session.add(taxonomy)
        db_session.commit()

        # Publish the taxonomy
        taxonomy.is_published = True
        taxonomy.published_at = datetime.now(timezone.utc)
        db_session.commit()

        assert taxonomy.is_published is True
        assert taxonomy.published_at is not None

    def test_set_default_taxonomy(self, db_session):
        """Test setting a taxonomy as default."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="defaultTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Test",
            is_default=True,
        )
        db_session.add(taxonomy)
        db_session.commit()

        assert taxonomy.is_default is True

    def test_unique_constraint_scope_taxonomy_version(self, db_session):
        """Test unique constraint on scope + owner + taxonomy_id + version."""
        taxonomy1 = TaxonomyDefinition(
            taxonomy_id="dupeTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="First",
        )
        db_session.add(taxonomy1)
        db_session.commit()

        # Same taxonomy_id + version + scope should fail
        taxonomy2 = TaxonomyDefinition(
            taxonomy_id="dupeTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Second",
        )
        db_session.add(taxonomy2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()

    def test_different_versions_allowed(self, db_session):
        """Test that different versions of same taxonomy are allowed."""
        taxonomy1 = TaxonomyDefinition(
            taxonomy_id="versionTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Version 1",
        )
        taxonomy2 = TaxonomyDefinition(
            taxonomy_id="versionTest",
            version="2.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Version 2",
        )
        db_session.add(taxonomy1)
        db_session.add(taxonomy2)
        db_session.commit()

        assert taxonomy1.version == "1.0.0"
        assert taxonomy2.version == "2.0.0"

    def test_empty_allowed_classifications(self, db_session):
        """Test taxonomy with no allowed classifications."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="noClassifications",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="No classifications",
            allowed_classifications=[],
        )
        db_session.add(taxonomy)
        db_session.commit()

        assert taxonomy.allowed_classifications == []


class TestTaxonomyEntity:
    """Test TaxonomyEntity model."""

    def test_create_simple_entity(self, db_session):
        """Test creating a simple taxonomy entity without parent."""
        # Create taxonomy definition
        taxonomy = TaxonomyDefinition(
            taxonomy_id="accountType",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Account Types",
        )
        db_session.add(taxonomy)
        db_session.flush()

        # Create entity
        entity = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="ASSET",
            value="asset",
            display_name="Asset",
            description="Asset accounts",
            explicit_classifications=["GAAP"],
        )
        db_session.add(entity)
        db_session.commit()

        assert entity.id is not None
        assert entity.entity_id == "ASSET"
        assert entity.value == "asset"
        assert entity.display_name == "Asset"
        assert entity.parent_entity_id is None
        assert "GAAP" in entity.explicit_classifications
        assert entity.is_base_entity is True

    def test_create_hierarchical_entities(self, db_session):
        """Test creating hierarchical taxonomy entities with parent-child relationships."""
        # Create taxonomy definition
        taxonomy = TaxonomyDefinition(
            taxonomy_id="accountType",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Account Types",
            is_hierarchical=True,
        )
        db_session.add(taxonomy)
        db_session.flush()

        # Create parent entity
        parent = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="ASSET",
            value="asset",
            display_name="Asset",
            description="Asset accounts",
        )
        db_session.add(parent)
        db_session.flush()

        # Create child entity
        child = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="CURRENT_ASSET",
            value="current_asset",
            display_name="Current Asset",
            description="Current asset accounts",
            parent_entity_id=parent.id,
        )
        db_session.add(child)
        db_session.commit()

        assert child.parent_entity_id == parent.id
        assert child.parent.entity_id == "ASSET"
        assert parent.children[0].entity_id == "CURRENT_ASSET"

    def test_unique_constraint_definition_entity(self, db_session):
        """Test unique constraint on taxonomy_definition_id + entity_id."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="dupeEntityTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Test",
        )
        db_session.add(taxonomy)
        db_session.flush()

        entity1 = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="DUPE",
            value="dupe1",
            display_name="First",
            description="First entity",
        )
        db_session.add(entity1)
        db_session.commit()

        # Same entity_id in same taxonomy should fail
        entity2 = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="DUPE",
            value="dupe2",
            display_name="Second",
            description="Second entity",
        )
        db_session.add(entity2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()

    def test_entity_id_not_empty_constraint(self, db_session):
        """Test that entity_id cannot be empty or whitespace."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="emptyTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Test",
        )
        db_session.add(taxonomy)
        db_session.flush()

        entity = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="   ",  # Whitespace only
            value="test",
            display_name="Test",
            description="Test entity",
        )
        db_session.add(entity)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()

    def test_multiple_entities_in_taxonomy(self, db_session):
        """Test creating multiple entities in the same taxonomy."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="multiEntity",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Multiple entities",
        )
        db_session.add(taxonomy)
        db_session.flush()

        entities = [
            TaxonomyEntity(
                taxonomy_definition_id=taxonomy.id,
                entity_id="ASSET",
                value="asset",
                display_name="Asset",
                description="Asset accounts",
            ),
            TaxonomyEntity(
                taxonomy_definition_id=taxonomy.id,
                entity_id="LIABILITY",
                value="liability",
                display_name="Liability",
                description="Liability accounts",
            ),
            TaxonomyEntity(
                taxonomy_definition_id=taxonomy.id,
                entity_id="EQUITY",
                value="equity",
                display_name="Equity",
                description="Equity accounts",
            ),
        ]

        for entity in entities:
            db_session.add(entity)
        db_session.commit()

        assert len(taxonomy.entities) == 3

    def test_derived_entity(self, db_session):
        """Test creating a derived (non-base) entity."""
        taxonomy = TaxonomyDefinition(
            taxonomy_id="derivedTest",
            version="1.0.0",
            scope_type=DefinitionScope.GLOBAL,
            description="Test",
        )
        db_session.add(taxonomy)
        db_session.flush()

        entity = TaxonomyEntity(
            taxonomy_definition_id=taxonomy.id,
            entity_id="DERIVED",
            value="derived",
            display_name="Derived Entity",
            description="Derived entity",
            is_base_entity=False,
        )
        db_session.add(entity)
        db_session.commit()

        assert entity.is_base_entity is False
