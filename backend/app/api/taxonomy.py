from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import taxonomy as crud
from ..schemas.taxonomy import (
    TaxonomyDefinitionCreate,
    TaxonomyDefinitionResponse,
    TaxonomyDefinitionUpdate,
    TaxonomyEntityCreate,
    TaxonomyEntityResponse,
    TaxonomyEntityUpdate,
)

router = APIRouter()


# Taxonomy Definition endpoints
@router.post(
    "/definitions", response_model=TaxonomyDefinitionResponse, status_code=status.HTTP_201_CREATED
)
def create_taxonomy_definition(taxonomy: TaxonomyDefinitionCreate, db: Session = Depends(get_db)):
    return crud.create_taxonomy_definition(db, taxonomy)


@router.get("/definitions", response_model=list[TaxonomyDefinitionResponse])
def list_taxonomy_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_taxonomy_definitions(db, skip=skip, limit=limit)


@router.get("/definitions/{taxonomy_id}", response_model=TaxonomyDefinitionResponse)
def get_taxonomy_definition(taxonomy_id: UUID, db: Session = Depends(get_db)):
    db_taxonomy = crud.get_taxonomy_definition(db, taxonomy_id)
    if not db_taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy definition not found"
        )
    return db_taxonomy


@router.put("/definitions/{taxonomy_id}", response_model=TaxonomyDefinitionResponse)
def update_taxonomy_definition(
    taxonomy_id: UUID, taxonomy: TaxonomyDefinitionUpdate, db: Session = Depends(get_db)
):
    db_taxonomy = crud.update_taxonomy_definition(db, taxonomy_id, taxonomy)
    if not db_taxonomy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy definition not found"
        )
    return db_taxonomy


@router.delete("/definitions/{taxonomy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_taxonomy_definition(taxonomy_id: UUID, db: Session = Depends(get_db)):
    if not crud.delete_taxonomy_definition(db, taxonomy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy definition not found"
        )


# Taxonomy Entity endpoints
@router.post(
    "/entities", response_model=TaxonomyEntityResponse, status_code=status.HTTP_201_CREATED
)
def create_taxonomy_entity(entity: TaxonomyEntityCreate, db: Session = Depends(get_db)):
    return crud.create_taxonomy_entity(db, entity)


@router.get("/definitions/{definition_id}/entities", response_model=list[TaxonomyEntityResponse])
def list_taxonomy_entities(
    definition_id: UUID, skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)
):
    return crud.get_taxonomy_entities_by_definition(db, definition_id, skip=skip, limit=limit)


@router.get("/entities/{entity_id}", response_model=TaxonomyEntityResponse)
def get_taxonomy_entity(entity_id: UUID, db: Session = Depends(get_db)):
    db_entity = crud.get_taxonomy_entity(db, entity_id)
    if not db_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy entity not found"
        )
    return db_entity


@router.put("/entities/{entity_id}", response_model=TaxonomyEntityResponse)
def update_taxonomy_entity(
    entity_id: UUID, entity: TaxonomyEntityUpdate, db: Session = Depends(get_db)
):
    db_entity = crud.update_taxonomy_entity(db, entity_id, entity)
    if not db_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy entity not found"
        )
    return db_entity


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_taxonomy_entity(entity_id: UUID, db: Session = Depends(get_db)):
    if not crud.delete_taxonomy_entity(db, entity_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy entity not found"
        )
