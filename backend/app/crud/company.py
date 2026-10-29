from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..models.company import Company
from ..schemas.company import CompanyCreate, CompanyUpdate


def get_company(db: Session, company_id: UUID) -> Optional[Company]:
    return db.query(Company).filter(Company.id == company_id).first()


def get_company_by_company_id(db: Session, company_id: str) -> Optional[Company]:
    return db.query(Company).filter(Company.company_id == company_id).first()


def get_companies(db: Session, skip: int = 0, limit: int = 100) -> List[Company]:
    return db.query(Company).offset(skip).limit(limit).all()


def create_company(db: Session, company: CompanyCreate) -> Company:
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


def update_company(
    db: Session, company_id: UUID, company_update: CompanyUpdate
) -> Optional[Company]:
    db_company = get_company(db, company_id)
    if not db_company:
        return None

    update_data = company_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_company, field, value)

    db.commit()
    db.refresh(db_company)
    return db_company


def delete_company(db: Session, company_id: UUID) -> bool:
    db_company = get_company(db, company_id)
    if not db_company:
        return False

    db.delete(db_company)
    db.commit()
    return True
