"""Unit tests for company models."""

import pytest
from backend.app.models.company import (
    Company,
    CompanySnapshot,
    CompanySnapshotHead,
    CompanyType,
    PeriodGranularity,
)


class TestCompany:
    """Test Company model."""

    def test_create_lender_company(self, db_session):
        """Test creating a lender company."""
        company = Company(
            company_id="LEND001",
            name="First National Bank",
            company_type=CompanyType.LENDER,
            description="Large commercial lender",
            customer_id="CUST-12345",
            is_enabled=True,
            is_test=False,
            naics_code="522110",
            state="CA",
            report_info=[{"type": "quarterly", "frequency": 4}],
            metadata_={"founded": "1985", "employees": 5000},
        )
        db_session.add(company)
        db_session.commit()

        assert company.id is not None
        assert company.company_id == "LEND001"
        assert company.name == "First National Bank"
        assert company.company_type == CompanyType.LENDER
        assert company.customer_id == "CUST-12345"
        assert company.is_enabled is True
        assert company.is_test is False
        assert company.naics_code == "522110"
        assert company.state == "CA"
        assert len(company.report_info) == 1
        assert company.metadata_["founded"] == "1985"

    def test_create_borrower_company(self, db_session):
        """Test creating a borrower company."""
        company = Company(
            company_id="BORR001",
            name="Tech Startup Inc",
            company_type=CompanyType.BORROWER,
            description="Technology startup seeking financing",
        )
        db_session.add(company)
        db_session.commit()

        assert company.company_type == CompanyType.BORROWER
        assert company.is_enabled is True  # Default
        assert company.is_test is False  # Default

    def test_create_participant_company(self, db_session):
        """Test creating a participant company."""
        company = Company(
            company_id="PART001",
            name="Syndication Partner Bank",
            company_type=CompanyType.PARTICIPANT,
            description="Loan syndication participant",
        )
        db_session.add(company)
        db_session.commit()

        assert company.company_type == CompanyType.PARTICIPANT

    def test_company_id_unique_constraint(self, db_session):
        """Test that company_id must be unique."""
        company1 = Company(
            company_id="DUPE001",
            name="First Company",
            company_type=CompanyType.LENDER,
            description="First",
        )
        db_session.add(company1)
        db_session.commit()

        company2 = Company(
            company_id="DUPE001",  # Duplicate company_id
            name="Second Company",
            company_type=CompanyType.BORROWER,
            description="Second",
        )
        db_session.add(company2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()

    def test_company_name_unique_constraint(self, db_session):
        """Test that company name must be unique."""
        company1 = Company(
            company_id="COMP001",
            name="Unique Bank",
            company_type=CompanyType.LENDER,
            description="First",
        )
        db_session.add(company1)
        db_session.commit()

        company2 = Company(
            company_id="COMP002",
            name="Unique Bank",  # Duplicate name
            company_type=CompanyType.BORROWER,
            description="Second",
        )
        db_session.add(company2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()

    def test_company_id_not_empty_constraint(self, db_session):
        """Test that company_id cannot be empty or whitespace."""
        company = Company(
            company_id="   ",  # Whitespace only
            name="Test Company",
            company_type=CompanyType.LENDER,
            description="Test",
        )
        db_session.add(company)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()

    def test_company_name_not_empty_constraint(self, db_session):
        """Test that company name cannot be empty or whitespace."""
        company = Company(
            company_id="TEST001",
            name="   ",  # Whitespace only
            company_type=CompanyType.LENDER,
            description="Test",
        )
        db_session.add(company)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()

    def test_empty_report_info_default(self, db_session):
        """Test that report_info defaults to empty array."""
        company = Company(
            company_id="EMPTY001",
            name="Empty Reports",
            company_type=CompanyType.LENDER,
            description="No reports",
        )
        db_session.add(company)
        db_session.commit()

        assert company.report_info == []

    def test_empty_metadata_default(self, db_session):
        """Test that metadata defaults to empty object."""
        company = Company(
            company_id="NOMETA001",
            name="No Metadata",
            company_type=CompanyType.LENDER,
            description="No metadata",
        )
        db_session.add(company)
        db_session.commit()

        assert company.metadata_ == {}

    def test_test_company_flag(self, db_session):
        """Test creating a test company."""
        company = Company(
            company_id="TEST001",
            name="Test Company",
            company_type=CompanyType.LENDER,
            description="Test company for QA",
            is_test=True,
        )
        db_session.add(company)
        db_session.commit()

        assert company.is_test is True

    def test_disabled_company(self, db_session):
        """Test creating a disabled company."""
        company = Company(
            company_id="DISABLED001",
            name="Disabled Company",
            company_type=CompanyType.LENDER,
            description="Disabled company",
            is_enabled=False,
        )
        db_session.add(company)
        db_session.commit()

        assert company.is_enabled is False


class TestCompanySnapshot:
    """Test CompanySnapshot model."""

    def test_create_yearly_snapshot(self, db_session):
        """Test creating a yearly company snapshot."""
        company = Company(
            company_id="SNAP001",
            name="Snapshot Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=1,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.id is not None
        assert snapshot.period_type == PeriodGranularity.YEAR
        assert snapshot.period_value == "2024"
        assert snapshot.ord == 1

    def test_create_quarterly_snapshot(self, db_session):
        """Test creating a quarterly company snapshot."""
        company = Company(
            company_id="SNAP002",
            name="Quarterly Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.QUARTER,
            period_value="2024Q3",
            ord=1,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.period_value == "2024Q3"

    def test_create_monthly_snapshot(self, db_session):
        """Test creating a monthly company snapshot."""
        company = Company(
            company_id="SNAP003",
            name="Monthly Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.MONTH,
            period_value="2024-03",
            ord=1,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.period_value == "2024-03"

    def test_create_daily_snapshot(self, db_session):
        """Test creating a daily company snapshot."""
        company = Company(
            company_id="SNAP004",
            name="Daily Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.DATE,
            period_value="2024-03-15",
            ord=1,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.period_value == "2024-03-15"

    def test_ordinal_versioning(self, db_session):
        """Test creating multiple snapshots with different ordinals."""
        company = Company(
            company_id="SNAP005",
            name="Ordinal Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        # Create multiple versions for same period
        snapshots = [
            CompanySnapshot(
                company_id=company.id,
                period_type=PeriodGranularity.YEAR,
                period_value="2024",
                ord=1,
            ),
            CompanySnapshot(
                company_id=company.id,
                period_type=PeriodGranularity.YEAR,
                period_value="2024",
                ord=2,
            ),
            CompanySnapshot(
                company_id=company.id,
                period_type=PeriodGranularity.YEAR,
                period_value="2024",
                ord=3,
            ),
        ]

        for snapshot in snapshots:
            db_session.add(snapshot)
        db_session.commit()

        assert snapshots[0].ord == 1
        assert snapshots[1].ord == 2
        assert snapshots[2].ord == 3

    def test_unique_constraint_company_period_ord(self, db_session):
        """Test unique constraint on company_id + period_type + period_value + ord."""
        company = Company(
            company_id="SNAP006",
            name="Unique Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot1 = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=1,
        )
        db_session.add(snapshot1)
        db_session.commit()

        # Same company + period + ord should fail
        snapshot2 = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=1,  # Duplicate
        )
        db_session.add(snapshot2)

        with pytest.raises(Exception):  # Unique constraint violation
            db_session.commit()

    def test_ordinal_positive_constraint(self, db_session):
        """Test that ordinal must be positive."""
        company = Company(
            company_id="SNAP007",
            name="Positive Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=0,  # Invalid - must be > 0
        )
        db_session.add(snapshot)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()

    def test_invalid_year_format(self, db_session):
        """Test that year period must match YYYY format."""
        company = Company(
            company_id="SNAP008",
            name="Format Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="24",  # Invalid format
            ord=1,
        )
        db_session.add(snapshot)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()

    def test_invalid_quarter_format(self, db_session):
        """Test that quarter period must match YYYYQN format."""
        company = Company(
            company_id="SNAP009",
            name="Quarter Format Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.QUARTER,
            period_value="2024Q5",  # Invalid - Q must be 1-4
            ord=1,
        )
        db_session.add(snapshot)

        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()


class TestCompanySnapshotHead:
    """Test CompanySnapshotHead model."""

    def test_create_snapshot_head(self, db_session):
        """Test creating a snapshot head materialized view entry."""
        company = Company(
            company_id="HEAD001",
            name="Head Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=1,
        )
        db_session.add(snapshot)
        db_session.flush()

        head = CompanySnapshotHead(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            snapshot_id=snapshot.id,
        )
        db_session.add(head)
        db_session.commit()

        assert head.company_id == company.id
        assert head.snapshot_id == snapshot.id

    def test_snapshot_head_composite_primary_key(self, db_session):
        """Test that snapshot head has composite primary key."""
        company = Company(
            company_id="HEAD002",
            name="Composite Key Test",
            company_type=CompanyType.BORROWER,
            description="Test",
        )
        db_session.add(company)
        db_session.flush()

        snapshot1 = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            ord=1,
        )
        snapshot2 = CompanySnapshot(
            company_id=company.id,
            period_type=PeriodGranularity.QUARTER,
            period_value="2024Q1",
            ord=1,
        )
        db_session.add(snapshot1)
        db_session.add(snapshot2)
        db_session.flush()

        # Different period_type is allowed
        head1 = CompanySnapshotHead(
            company_id=company.id,
            period_type=PeriodGranularity.YEAR,
            period_value="2024",
            snapshot_id=snapshot1.id,
        )
        head2 = CompanySnapshotHead(
            company_id=company.id,
            period_type=PeriodGranularity.QUARTER,
            period_value="2024Q1",
            snapshot_id=snapshot2.id,
        )
        db_session.add(head1)
        db_session.add(head2)
        db_session.commit()

        assert head1.period_type == PeriodGranularity.YEAR
        assert head2.period_type == PeriodGranularity.QUARTER
