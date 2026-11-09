import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ApplicationDomainRole(str, enum.Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class SnapshotAlignment(str, enum.Enum):
    COMPANY = "COMPANY"
    INDEPENDENT = "INDEPENDENT"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    default_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "application_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_applications_default_version",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(application_id)) > 0", name="ck_applications_application_id_not_empty"
        ),
    )

    versions = relationship(
        "ApplicationVersion",
        back_populates="application",
        cascade="all, delete-orphan",
        foreign_keys="ApplicationVersion.application_id",
    )
    default_version = relationship(
        "ApplicationVersion", foreign_keys=[default_version_id], post_update=True
    )


class ApplicationVersion(Base):
    __tablename__ = "application_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_application_versions_app_version"),
        CheckConstraint(
            "length(trim(version)) > 0", name="ck_application_versions_version_not_empty"
        ),
        CheckConstraint("length(trim(name)) > 0", name="ck_application_versions_name_not_empty"),
        Index("ix_application_versions_application", "application_id"),
    )

    application = relationship(
        "Application", back_populates="versions", foreign_keys=[application_id]
    )
    domains = relationship(
        "ApplicationDomain", back_populates="application_version", cascade="all, delete-orphan"
    )
    companies = relationship(
        "ApplicationCompany", back_populates="application_version", cascade="all, delete-orphan"
    )
    bind_instances = relationship(
        "ApplicationBindInstance",
        back_populates="application_version",
        cascade="all, delete-orphan",
    )


class ApplicationDomain(Base):
    __tablename__ = "application_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    domain_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domain_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[ApplicationDomainRole] = mapped_column(
        Enum(ApplicationDomainRole, name="application_domain_role"), nullable=False
    )
    snapshot_alignment: Mapped[SnapshotAlignment] = mapped_column(
        Enum(SnapshotAlignment, name="snapshot_alignment"), nullable=False
    )
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "application_version_id",
            "domain_definition_id",
            name="uq_application_domains_version_domain",
        ),
        Index("ix_application_domains_version", "application_version_id"),
    )

    application_version = relationship("ApplicationVersion", back_populates="domains")


class ApplicationCompany(Base):
    __tablename__ = "application_companies"

    application_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    application_version = relationship("ApplicationVersion", back_populates="companies")


class ApplicationBindInstance(Base):
    __tablename__ = "application_bind_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    company_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "application_version_id",
            "company_id",
            "company_snapshot_id",
            name="uq_application_bind_instances_version_company_snapshot",
        ),
        Index("ix_application_bind_instances_version", "application_version_id"),
    )

    application_version = relationship("ApplicationVersion", back_populates="bind_instances")
    members = relationship(
        "ApplicationBindInstanceMember",
        back_populates="bind_instance",
        cascade="all, delete-orphan",
    )


class ApplicationBindInstanceMember(Base):
    __tablename__ = "application_bind_instance_members"

    bind_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_bind_instances.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain_instance_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domain_instance_snapshots.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    domain_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domain_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (Index("ix_application_bind_members_domain", "domain_definition_id"),)

    bind_instance = relationship("ApplicationBindInstance", back_populates="members")
