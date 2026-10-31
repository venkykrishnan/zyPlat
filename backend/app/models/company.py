import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from ..core.database import Base


class CompanyType(str, enum.Enum):
    LENDER = "LENDER"
    BORROWER = "BORROWER"
    PARTICIPANT = "PARTICIPANT"


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False, server_default="")
    company_type = Column(Enum(CompanyType, name="company_type"), nullable=False)
    customer_id = Column(String, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default=text("TRUE"))
    is_test = Column(Boolean, nullable=False, server_default=text("FALSE"))
    naics_code = Column(String, nullable=True)
    state = Column(String, nullable=True)
    report_info = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(trim(company_id)) > 0", name="ck_companies_company_id_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_companies_name_not_empty"),
        CheckConstraint(
            "jsonb_typeof(report_info) = 'array'", name="ck_companies_report_info_array"
        ),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_companies_metadata_object"),
        Index("ix_companies_customer_id", "customer_id"),
        Index("ix_companies_is_enabled", "is_enabled"),
        Index("ix_companies_is_test", "is_test"),
        Index("ix_companies_naics_code", "naics_code"),
        Index("ix_companies_state", "state"),
        Index("ix_companies_company_type", "company_type"),
    )

    snapshots = relationship(
        "CompanySnapshot", back_populates="company", cascade="all, delete-orphan"
    )


class PeriodGranularity(str, enum.Enum):
    YEAR = "YEAR"
    QUARTER = "QUARTER"
    MONTH = "MONTH"
    DATE = "DATE"


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_type = Column(Enum(PeriodGranularity, name="period_granularity"), nullable=False)
    period_value = Column(String, nullable=False)
    ord = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "period_value", "ord", name="uq_company_snapshot_tuple"
        ),
        CheckConstraint("ord > 0", name="ck_company_snapshot_ord_positive"),
        CheckConstraint(
            """
            (period_type = 'YEAR'    AND period_value ~ '^[0-9]{4}$') OR
            (period_type = 'QUARTER' AND period_value ~ '^[0-9]{4}Q[1-4]$') OR
            (period_type = 'MONTH'   AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])$') OR
            (period_type = 'DATE'    AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])$')
            """,
            name="ck_company_snapshot_period_format",
        ),
        Index(
            "ix_company_snapshot_default_lookup", "company_id", "period_type", "period_value", "ord"
        ),
    )

    company = relationship("Company", back_populates="snapshots")


class CompanySnapshotHead(Base):
    __tablename__ = "company_snapshot_heads"

    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    period_type = Column(Enum(PeriodGranularity, name="period_granularity"), primary_key=True)
    period_value = Column(String, primary_key=True)
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("company_snapshots.id", ondelete="CASCADE"), nullable=False
    )
