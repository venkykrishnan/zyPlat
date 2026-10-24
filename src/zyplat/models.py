"""Relational schema for taxonomies, domains, and domain instances."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

from zyplat.clock import utcnow

DRAFT = "draft"
PUBLISHED = "published"


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Taxonomy(Base):
    __tablename__ = "taxonomies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    is_hierarchical: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TaxonomyVersion(Base):
    __tablename__ = "taxonomy_versions"
    __table_args__ = (UniqueConstraint("taxonomy_id", "version", name="uq_taxonomy_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    taxonomy_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    allowed_classifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class TaxonomyEntity(Base):
    __tablename__ = "taxonomy_entities"
    __table_args__ = (UniqueConstraint("taxonomy_version_id", "code", name="uq_taxonomy_entity_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    taxonomy_version_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomy_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    # No database foreign key: a version's entities are deleted together, and the
    # tree is enforced in the service so parent/child delete order is not a constraint.
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    classifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class DomainDimension(Base):
    __tablename__ = "domain_dimensions"
    __table_args__ = (UniqueConstraint("domain_id", "name", name="uq_domain_dimension_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    domain_id: Mapped[str] = mapped_column(
        ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    taxonomy_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomies.id", ondelete="RESTRICT"), nullable=False
    )
    taxonomy_version_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomy_versions.id", ondelete="RESTRICT"), nullable=False
    )


class DomainInstance(Base):
    __tablename__ = "domain_instances"
    __table_args__ = (UniqueConstraint("domain_id", "name", name="uq_domain_instance_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    domain_id: Mapped[str] = mapped_column(
        ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    selected_classifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class DomainInstanceDimension(Base):
    """Pins copied onto the instance so later domain edits do not rewrite it."""

    __tablename__ = "domain_instance_dimensions"
    __table_args__ = (
        UniqueConstraint("instance_id", "name", name="uq_instance_dimension_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    instance_id: Mapped[str] = mapped_column(
        ForeignKey("domain_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    taxonomy_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomies.id", ondelete="RESTRICT"), nullable=False
    )
    taxonomy_version_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomy_versions.id", ondelete="RESTRICT"), nullable=False
    )


class DomainInstanceEntity(Base):
    __tablename__ = "domain_instance_entities"
    __table_args__ = (UniqueConstraint("instance_id", "code", name="uq_instance_entity_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    instance_id: Mapped[str] = mapped_column(
        ForeignKey("domain_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class DomainInstanceEntityValue(Base):
    __tablename__ = "domain_instance_entity_values"
    __table_args__ = (
        UniqueConstraint("instance_entity_id", "dimension_name", name="uq_instance_entity_dimension"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    instance_entity_id: Mapped[str] = mapped_column(
        ForeignKey("domain_instance_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dimension_name: Mapped[str] = mapped_column(String(128), nullable=False)
    taxonomy_entity_id: Mapped[str] = mapped_column(
        ForeignKey("taxonomy_entities.id", ondelete="RESTRICT"), nullable=False
    )
