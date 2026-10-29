from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..models.taxonomy import TaxonomyDefinition, TaxonomyEntity, DefinitionScope
from ..schemas.taxonomy import (
    TaxonomyDefinitionCreate,
    TaxonomyDefinitionUpdate,
    TaxonomyEntityCreate,
    TaxonomyEntityUpdate,
)


# Taxonomy Definition CRUD
def get_taxonomy_definition(db: Session, taxonomy_id: UUID) -> Optional[TaxonomyDefinition]:
    return db.query(TaxonomyDefinition).filter(TaxonomyDefinition.id == taxonomy_id).first()


def get_taxonomy_definitions(
    db: Session, skip: int = 0, limit: int = 100
) -> List[TaxonomyDefinition]:
    return db.query(TaxonomyDefinition).offset(skip).limit(limit).all()


def create_taxonomy_definition(
    db: Session, taxonomy: TaxonomyDefinitionCreate
) -> TaxonomyDefinition:
    db_taxonomy = TaxonomyDefinition(**taxonomy.model_dump())
    if db_taxonomy.is_published and not db_taxonomy.published_at:
        db_taxonomy.published_at = datetime.utcnow()
    db.add(db_taxonomy)
    db.commit()
    db.refresh(db_taxonomy)
    return db_taxonomy


def update_taxonomy_definition(
    db: Session, taxonomy_id: UUID, taxonomy_update: TaxonomyDefinitionUpdate
) -> Optional[TaxonomyDefinition]:
    db_taxonomy = get_taxonomy_definition(db, taxonomy_id)
    if not db_taxonomy:
        return None

    update_data = taxonomy_update.model_dump(exclude_unset=True)

    if (
        "is_published" in update_data
        and update_data["is_published"]
        and not db_taxonomy.published_at
    ):
        db_taxonomy.published_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(db_taxonomy, field, value)

    db.commit()
    db.refresh(db_taxonomy)
    return db_taxonomy


def delete_taxonomy_definition(db: Session, taxonomy_id: UUID) -> bool:
    db_taxonomy = get_taxonomy_definition(db, taxonomy_id)
    if not db_taxonomy:
        return False

    db.delete(db_taxonomy)
    db.commit()
    return True


# Taxonomy Entity CRUD
def get_taxonomy_entity(db: Session, entity_id: UUID) -> Optional[TaxonomyEntity]:
    return db.query(TaxonomyEntity).filter(TaxonomyEntity.id == entity_id).first()


def get_taxonomy_entities_by_definition(
    db: Session, definition_id: UUID, skip: int = 0, limit: int = 1000
) -> List[TaxonomyEntity]:
    return (
        db.query(TaxonomyEntity)
        .filter(TaxonomyEntity.taxonomy_definition_id == definition_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_taxonomy_entity(db: Session, entity: TaxonomyEntityCreate) -> TaxonomyEntity:
    db_entity = TaxonomyEntity(**entity.model_dump())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity


def update_taxonomy_entity(
    db: Session, entity_id: UUID, entity_update: TaxonomyEntityUpdate
) -> Optional[TaxonomyEntity]:
    db_entity = get_taxonomy_entity(db, entity_id)
    if not db_entity:
        return None

    update_data = entity_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_entity, field, value)

    db.commit()
    db.refresh(db_entity)
    return db_entity


def delete_taxonomy_entity(db: Session, entity_id: UUID) -> bool:
    db_entity = get_taxonomy_entity(db, entity_id)
    if not db_entity:
        return False

    db.delete(db_entity)
    db.commit()
    return True
