import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship

from ..core.database import Base


class DefinitionScope(str, enum.Enum):
    GLOBAL = "GLOBAL"
    COMPANY = "COMPANY"


class TaxonomyDefinition(Base):
    __tablename__ = "taxonomy_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    taxonomy_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    scope_type = Column(Enum(DefinitionScope, name="definition_scope"), nullable=False)
    owner_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    description = Column(String, nullable=False)
    is_hierarchical = Column(Boolean, nullable=False, server_default=text("FALSE"))
    allowed_classifications = Column(ARRAY(String), nullable=False, server_default=text("'{}'::text[]"))
    is_published = Column(Boolean, nullable=False, server_default=text("FALSE"))
    published_at = Column(DateTime(timezone=True), nullable=True)
    is_default = Column(Boolean, nullable=False, server_default=text("FALSE"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("scope_type", "owner_company_id", "taxonomy_id", "version", name="uq_taxonomy_definitions_scope_taxonomy_version"),
        CheckConstraint(
            """
            (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
            OR
            (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
            """,
            name="ck_taxonomy_scope_owner",
        ),
        CheckConstraint(
            "(is_published = FALSE AND published_at IS NULL) OR (is_published = TRUE)",
            name="ck_taxonomy_published_fields",
        ),
        Index(
            "uq_taxonomy_default_per_scope",
            "scope_type",
            "owner_company_id",
            "taxonomy_id",
            unique=True,
            postgresql_where=text("is_default = TRUE"),
        ),
        Index("ix_taxonomy_lookup", "taxonomy_id", "scope_type", "owner_company_id", "is_published", "is_default", "updated_at"),
    )

    entities = relationship("TaxonomyEntity", back_populates="definition", cascade="all, delete-orphan")


class TaxonomyEntity(Base):
    __tablename__ = "taxonomy_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    taxonomy_definition_id = Column(UUID(as_uuid=True), ForeignKey("taxonomy_definitions.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(String, nullable=False)
    value = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    parent_entity_id = Column(UUID(as_uuid=True), ForeignKey("taxonomy_entities.id", ondelete="RESTRICT"), nullable=True)
    explicit_classifications = Column(ARRAY(String), nullable=False, server_default=text("'{}'::text[]"))
    is_base_entity = Column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("taxonomy_definition_id", "entity_id", name="uq_taxonomy_entities_definition_entity"),
        CheckConstraint("length(trim(entity_id)) > 0", name="ck_taxonomy_entities_entity_id_not_empty"),
        Index("ix_taxonomy_entities_definition", "taxonomy_definition_id"),
        Index("ix_taxonomy_entities_parent", "taxonomy_definition_id", "parent_entity_id"),
    )

    definition = relationship("TaxonomyDefinition", back_populates="entities")
    parent = relationship("TaxonomyEntity", remote_side=[id], backref="children")
