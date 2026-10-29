"""Unit tests for domain models."""

import pytest
from backend.app.models.domain import (
    DomainDefinition,
    DomainDimension,
    DomainMetric,
    DomainInstance,
    DomainKind,
    DomainDimensionDataType,
    DomainMetricDataType,
    TaxonomyVersionStrategy,
)
from backend.app.models.taxonomy import DefinitionScope
from backend.app.models.company import Company, CompanyType


class TestDomainDefinition:
    """Test DomainDefinition model."""

    def test_create_global_time_series_domain(self, db_session):
        """Test creating a global time-series domain."""
        domain = DomainDefinition(
            domain_id="GL",
            description="General Ledger",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
            owner_company_id=None,
        )
        db_session.add(domain)
        db_session.commit()

        assert domain.id is not None
        assert domain.domain_id == "GL"
        assert domain.kind == DomainKind.TIME_SERIES
        assert domain.scope_type == DefinitionScope.GLOBAL
        assert domain.owner_company_id is None

    def test_create_scalar_domain(self, db_session):
        """Test creating a scalar domain."""
        domain = DomainDefinition(
            domain_id="CompanyInfo",
            description="Company Information",
            kind=DomainKind.SCALAR,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.commit()

        assert domain.kind == DomainKind.SCALAR

    def test_create_company_scoped_domain(self, db_session):
        """Test creating a company-scoped domain."""
        # First create a company
        company = Company(
            company_id="COMP001",
            name="Test Company",
            company_type=CompanyType.LENDER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        # Create company-scoped domain
        domain = DomainDefinition(
            domain_id="CustomGL",
            description="Custom General Ledger",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.COMPANY,
            owner_company_id=company.id,
        )
        db_session.add(domain)
        db_session.commit()

        assert domain.scope_type == DefinitionScope.COMPANY
        assert domain.owner_company_id == company.id

    def test_global_domain_cannot_have_owner(self, db_session):
        """Test that global domains cannot have an owner_company_id."""
        company = Company(
            company_id="COMP002",
            name="Test Company 2",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        # This should violate the check constraint
        domain = DomainDefinition(
            domain_id="BadDomain",
            description="Invalid domain",
            kind=DomainKind.SCALAR,
            scope_type=DefinitionScope.GLOBAL,
            owner_company_id=company.id,  # Invalid!
        )
        db_session.add(domain)

        with pytest.raises(Exception):  # Constraint violation
            db_session.commit()


class TestDomainDimension:
    """Test DomainDimension model."""

    def test_create_simple_dimension(self, db_session):
        """Test creating a simple dimension without taxonomy."""
        domain = DomainDefinition(
            domain_id="TestDomain",
            description="Test",
            kind=DomainKind.SCALAR,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        dimension = DomainDimension(
            domain_definition_id=domain.id,
            name="amount",
            display_name="Amount",
            data_type=DomainDimensionDataType.NUMBER,
            required=True,
            is_filter=False,
            ordinal=1,
        )
        db_session.add(dimension)
        db_session.commit()

        assert dimension.id is not None
        assert dimension.name == "amount"
        assert dimension.data_type == DomainDimensionDataType.NUMBER
        assert dimension.required is True
        assert dimension.taxonomy_id is None

    def test_create_taxonomy_backed_dimension_latest(self, db_session):
        """Test dimension with LATEST_PUBLISHED taxonomy strategy."""
        domain = DomainDefinition(
            domain_id="GLDomain",
            description="GL",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        dimension = DomainDimension(
            domain_definition_id=domain.id,
            name="accountType",
            display_name="Account Type",
            data_type=DomainDimensionDataType.ENUM,
            required=True,
            is_filter=True,
            ordinal=1,
            taxonomy_id="accountType",
            taxonomy_version_strategy=TaxonomyVersionStrategy.LATEST_PUBLISHED,
            taxonomy_version=None,  # Not required for LATEST_PUBLISHED
        )
        db_session.add(dimension)
        db_session.commit()

        assert dimension.taxonomy_id == "accountType"
        assert dimension.taxonomy_version_strategy == TaxonomyVersionStrategy.LATEST_PUBLISHED
        assert dimension.taxonomy_version is None

    def test_create_taxonomy_backed_dimension_pinned(self, db_session):
        """Test dimension with PINNED taxonomy strategy."""
        domain = DomainDefinition(
            domain_id="GLDomain2",
            description="GL",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        dimension = DomainDimension(
            domain_definition_id=domain.id,
            name="accountType",
            display_name="Account Type",
            data_type=DomainDimensionDataType.ENUM,
            required=True,
            is_filter=True,
            ordinal=1,
            taxonomy_id="accountType",
            taxonomy_version_strategy=TaxonomyVersionStrategy.PINNED,
            taxonomy_version="1.0.0",  # Required for PINNED
        )
        db_session.add(dimension)
        db_session.commit()

        assert dimension.taxonomy_version_strategy == TaxonomyVersionStrategy.PINNED
        assert dimension.taxonomy_version == "1.0.0"

    def test_pinned_strategy_requires_version(self, db_session):
        """Test that PINNED strategy requires taxonomy_version."""
        domain = DomainDefinition(
            domain_id="BadDomain2",
            description="Test",
            kind=DomainKind.SCALAR,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        # PINNED without version should fail
        dimension = DomainDimension(
            domain_definition_id=domain.id,
            name="test",
            display_name="Test",
            data_type=DomainDimensionDataType.ENUM,
            required=False,
            is_filter=False,
            ordinal=1,
            taxonomy_id="testTax",
            taxonomy_version_strategy=TaxonomyVersionStrategy.PINNED,
            taxonomy_version=None,  # Missing!
        )
        db_session.add(dimension)

        with pytest.raises(Exception):  # Constraint violation
            db_session.commit()


class TestDomainMetric:
    """Test DomainMetric model."""

    def test_create_metric(self, db_session):
        """Test creating a domain metric."""
        domain = DomainDefinition(
            domain_id="FinDomain",
            description="Financial",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        metric = DomainMetric(
            domain_definition_id=domain.id,
            name="balance",
            display_name="Account Balance",
            data_type=DomainMetricDataType.DECIMAL,
            required=True,
            ordinal=1,
        )
        db_session.add(metric)
        db_session.commit()

        assert metric.id is not None
        assert metric.name == "balance"
        assert metric.data_type == DomainMetricDataType.DECIMAL
        assert metric.required is True

    def test_multiple_metrics_different_ordinals(self, db_session):
        """Test creating multiple metrics with different ordinals."""
        domain = DomainDefinition(
            domain_id="MultiMetric",
            description="Multiple Metrics",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        metrics = [
            DomainMetric(
                domain_definition_id=domain.id,
                name="revenue",
                display_name="Revenue",
                data_type=DomainMetricDataType.DECIMAL,
                required=True,
                ordinal=1,
            ),
            DomainMetric(
                domain_definition_id=domain.id,
                name="expenses",
                display_name="Expenses",
                data_type=DomainMetricDataType.DECIMAL,
                required=True,
                ordinal=2,
            ),
            DomainMetric(
                domain_definition_id=domain.id,
                name="count",
                display_name="Transaction Count",
                data_type=DomainMetricDataType.INTEGER,
                required=False,
                ordinal=3,
            ),
        ]

        for metric in metrics:
            db_session.add(metric)
        db_session.commit()

        assert len(metrics) == 3
        assert metrics[0].ordinal == 1
        assert metrics[1].ordinal == 2
        assert metrics[2].ordinal == 3


class TestDomainInstance:
    """Test DomainInstance model."""

    def test_create_domain_instance(self, db_session):
        """Test creating a domain instance."""
        # Create company
        company = Company(
            company_id="BORR001",
            name="Borrower 1",
            company_type=CompanyType.BORROWER,
            description="Test borrower",
        )
        db_session.add(company)
        db_session.flush()

        # Create domain
        domain = DomainDefinition(
            domain_id="GL",
            description="General Ledger",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        # Create instance
        instance = DomainInstance(
            domain_definition_id=domain.id,
            company_id=company.id,
            active_classifications=["CIQ", "GAAP"],
            metadata_={"source": "import", "version": "1.0"},
        )
        db_session.add(instance)
        db_session.commit()

        assert instance.id is not None
        assert instance.domain_definition_id == domain.id
        assert instance.company_id == company.id
        assert "CIQ" in instance.active_classifications
        assert instance.metadata_["source"] == "import"

    def test_one_instance_per_domain_per_company(self, db_session):
        """Test unique constraint: one instance per domain per company."""
        company = Company(
            company_id="BORR002",
            name="Borrower 2",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        domain = DomainDefinition(
            domain_id="LoanPayment",
            description="Loan Payments",
            kind=DomainKind.TIME_SERIES,
            scope_type=DefinitionScope.GLOBAL,
        )
        db_session.add(domain)
        db_session.flush()

        # First instance
        instance1 = DomainInstance(
            domain_definition_id=domain.id,
            company_id=company.id,
            active_classifications=[],
        )
        db_session.add(instance1)
        db_session.commit()

        # Second instance for same domain+company should fail
        instance2 = DomainInstance(
            domain_definition_id=domain.id,
            company_id=company.id,
            active_classifications=[],
        )
        db_session.add(instance2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()
