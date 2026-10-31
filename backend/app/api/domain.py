from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import domain as crud
from ..schemas.domain import (
    DomainDefinitionCreate,
    DomainDefinitionResponse,
    DomainDefinitionUpdate,
)

router = APIRouter()


@router.post("/", response_model=DomainDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_domain_definition(domain: DomainDefinitionCreate, db: Session = Depends(get_db)):
    return crud.create_domain_definition(db, domain)


@router.get("/", response_model=list[DomainDefinitionResponse])
def list_domain_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_domain_definitions(db, skip=skip, limit=limit)


@router.get("/{domain_id}", response_model=DomainDefinitionResponse)
def get_domain_definition(domain_id: UUID, db: Session = Depends(get_db)):
    db_domain = crud.get_domain_definition(db, domain_id)
    if not db_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain definition not found"
        )
    return db_domain


@router.put("/{domain_id}", response_model=DomainDefinitionResponse)
def update_domain_definition(
    domain_id: UUID, domain: DomainDefinitionUpdate, db: Session = Depends(get_db)
):
    db_domain = crud.update_domain_definition(db, domain_id, domain)
    if not db_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain definition not found"
        )
    return db_domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain_definition(domain_id: UUID, db: Session = Depends(get_db)):
    if not crud.delete_domain_definition(db, domain_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain definition not found"
        )
