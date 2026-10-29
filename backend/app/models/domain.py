import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Integer, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship

from ..core.database import Base
from .taxonomy import DefinitionScope
from .company import PeriodGranularity


class DomainKind(str, enum.Enum):
    TIME_SERIES = "TIME_SERIES"
    SCALAR = "SCALAR"


class DomainDimensionDataType(str, enum.Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    ENUM = "ENUM"
    ARRAY_STRING = "ARRAY_STRING"


class DomainMetricDataType(str, enum.Enum):
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"


class TaxonomyVersionStrategy(str, enum.Enum):
    LATEST_PUBLISHED = "LATEST_PUBLISHED"
    PINNED = "PINNED"


class DomainDefinition(Base):
    __tablename__ = "domain_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_id = Column(String, nullable=False)
    description = Column(String, nullable=False)
    kind = Column(Enum(DomainKind, name="domain_kind"), nullable=False)
    scope_type = Column(Enum(DefinitionScope, name="definition_scope"), nullable=False)
    owner_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("scope_type", "owner_company_id", "domain_id", name="uq_domain_definitions_scope_domain"),
        CheckConstraint(
            """
            (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
            OR
            (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
            """,
            name="ck_domain_scope_owner",
        ),
        Index("ix_domain_lookup", "domain_id", "scope_type", "owner_company_id", "updated_at"),
    )

    dimensions = relationship("DomainDimension", back_populates="domain_definition", cascade="all, delete-orphan")
    metrics = relationship("DomainMetric", back_populates="domain_definition", cascade="all, delete-orphan")
    instances = relationship("DomainInstance", back_populates="domain_definition", cascade="all, delete-orphan")


class DomainDimension(Base):
    __tablename__ = "domain_dimensions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_definition_id = Column(UUID(as_uuid=True), ForeignKey("domain_definitions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    data_type = Column(Enum(DomainDimensionDataType, name="domain_dimension_data_type"), nullable=False)
    required = Column(Boolean, nullable=False, server_default=text("FALSE"))
    is_filter = Column(Boolean, nullable=False, server_default=text("FALSE"))
    ordinal = Column(Integer, nullable=False)
    taxonomy_id = Column(String, nullable=True)
    taxonomy_version_strategy = Column(Enum(TaxonomyVersionStrategy, name="taxonomy_version_strategy"), nullable=True)
    taxonomy_version = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("domain_definition_id", "name", name="uq_domain_dimensions_definition_name"),
        UniqueConstraint("domain_definition_id", "ordinal", name="uq_domain_dimensions_definition_ordinal"),
        CheckConstraint(
            """
            (taxonomy_id IS NULL AND taxonomy_version_strategy IS NULL AND taxonomy_version IS NULL)
            OR
            (taxonomy_id IS NOT NULL AND taxonomy_version_strategy IS NOT NULL)
            """,
            name="ck_domain_dimension_taxonomy_fields",
        ),
        CheckConstraint(
            """
            (taxonomy_version_strategy != 'PINNED' AND taxonomy_version IS NULL)
            OR
            (taxonomy_version_strategy = 'PINNED' AND taxonomy_version IS NOT NULL)
            """,
            name="ck_domain_dimension_pinned_version",
        ),
        Index("ix_domain_dimensions_definition", "domain_definition_id"),
    )

    domain_definition = relationship("DomainDefinition", back_populates="dimensions")


class DomainMetric(Base):
    __tablename__ = "domain_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_definition_id = Column(UUID(as_uuid=True), ForeignKey("domain_definitions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    data_type = Column(Enum(DomainMetricDataType, name="domain_metric_data_type"), nullable=False)
    required = Column(Boolean, nullable=False, server_default=text("FALSE"))
    ordinal = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("domain_definition_id", "name", name="uq_domain_metrics_definition_name"),
        UniqueConstraint("domain_definition_id", "ordinal", name="uq_domain_metrics_definition_ordinal"),
        Index("ix_domain_metrics_definition", "domain_definition_id"),
    )

    domain_definition = relationship("DomainDefinition", back_populates="metrics")


class DomainInstance(Base):
    __tablename__ = "domain_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_definition_id = Column(UUID(as_uuid=True), ForeignKey("domain_definitions.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    active_classifications = Column(ARRAY(String), nullable=False, server_default=text("'{}'::text[]"))
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("domain_definition_id", "company_id", name="uq_domain_instances_definition_company"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_domain_instances_metadata_object"),
        Index("ix_domain_instances_company", "company_id"),
        Index("ix_domain_instances_definition", "domain_definition_id"),
    )

    domain_definition = relationship("DomainDefinition", back_populates="instances")
    snapshots = relationship("DomainInstanceSnapshot", back_populates="domain_instance", cascade="all, delete-orphan")
    entities = relationship("DomainInstanceEntity", back_populates="domain_instance", cascade="all, delete-orphan")


class DomainInstanceSnapshot(Base):
    __tablename__ = "domain_instance_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_instance_id = Column(UUID(as_uuid=True), ForeignKey("domain_instances.id", ondelete="CASCADE"), nullable=False)
    company_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("company_snapshots.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_domain_instance_snapshots_instance", "domain_instance_id"),
        Index("ix_domain_instance_snapshots_company_snapshot", "company_snapshot_id"),
    )

    domain_instance = relationship("DomainInstance", back_populates="snapshots")


class DomainInstanceEntity(Base):
    __tablename__ = "domain_instance_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    domain_instance_id = Column(UUID(as_uuid=True), ForeignKey("domain_instances.id", ondelete="CASCADE"), nullable=False)
    domain_instance_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("domain_instance_snapshots.id", ondelete="CASCADE"), nullable=True)
    dimensions = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    metrics = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("jsonb_typeof(dimensions) = 'object'", name="ck_domain_instance_entities_dimensions_object"),
        CheckConstraint("jsonb_typeof(metrics) = 'object'", name="ck_domain_instance_entities_metrics_object"),
        Index("ix_domain_instance_entities_instance", "domain_instance_id"),
        Index("ix_domain_instance_entities_snapshot", "domain_instance_snapshot_id"),
    )

    domain_instance = relationship("DomainInstance", back_populates="entities")
