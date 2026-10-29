from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..models.domain import DomainDefinition
from ..schemas.domain import DomainDefinitionCreate, DomainDefinitionUpdate


def get_domain_definition(db: Session, domain_id: UUID) -> Optional[DomainDefinition]:
    return db.query(DomainDefinition).filter(DomainDefinition.id == domain_id).first()


def get_domain_definitions(db: Session, skip: int = 0, limit: int = 100) -> List[DomainDefinition]:
    return db.query(DomainDefinition).offset(skip).limit(limit).all()


def create_domain_definition(db: Session, domain: DomainDefinitionCreate) -> DomainDefinition:
    db_domain = DomainDefinition(**domain.model_dump())
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain


def update_domain_definition(
    db: Session, domain_id: UUID, domain_update: DomainDefinitionUpdate
) -> Optional[DomainDefinition]:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        return None

    update_data = domain_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_domain, field, value)

    db.commit()
    db.refresh(db_domain)
    return db_domain


def delete_domain_definition(db: Session, domain_id: UUID) -> bool:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        return False

    db.delete(db_domain)
    db.commit()
    return True
