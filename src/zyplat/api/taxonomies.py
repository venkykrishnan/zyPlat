"""Taxonomy HTTP routes."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from zyplat.db import get_session
from zyplat.schemas import (
    ErrorResponse,
    TaxonomyCreate,
    TaxonomyEntityCreate,
    TaxonomyEntityListResponse,
    TaxonomyEntityResponse,
    TaxonomyEntityUpdate,
    TaxonomyListResponse,
    TaxonomyResponse,
    TaxonomyUpdate,
    VersionListResponse,
    VersionSummary,
)
from zyplat.services import taxonomy_service

router = APIRouter(prefix="/taxonomies", tags=["taxonomies"])

_ERRORS = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.post("", response_model=TaxonomyResponse, status_code=status.HTTP_201_CREATED, responses=_ERRORS)
def create_taxonomy(payload: TaxonomyCreate, session: Session = Depends(get_session)) -> TaxonomyResponse:
    return taxonomy_service.create_taxonomy(session, payload)


@router.get("", response_model=TaxonomyListResponse, responses=_ERRORS)
def list_taxonomies(session: Session = Depends(get_session)) -> TaxonomyListResponse:
    return taxonomy_service.list_taxonomies(session)


@router.get("/{taxonomy_id}", response_model=TaxonomyResponse, responses=_ERRORS)
def get_taxonomy(taxonomy_id: str, session: Session = Depends(get_session)) -> TaxonomyResponse:
    return taxonomy_service.get_taxonomy(session, taxonomy_id)


@router.patch("/{taxonomy_id}", response_model=TaxonomyResponse, responses=_ERRORS)
def update_taxonomy(
    taxonomy_id: str, payload: TaxonomyUpdate, session: Session = Depends(get_session)
) -> TaxonomyResponse:
    return taxonomy_service.update_taxonomy(session, taxonomy_id, payload)


@router.delete("/{taxonomy_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_ERRORS)
def delete_taxonomy(taxonomy_id: str, session: Session = Depends(get_session)) -> Response:
    taxonomy_service.delete_taxonomy(session, taxonomy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{taxonomy_id}/publish", response_model=TaxonomyResponse, responses=_ERRORS)
def publish_taxonomy(taxonomy_id: str, session: Session = Depends(get_session)) -> TaxonomyResponse:
    return taxonomy_service.publish_taxonomy(session, taxonomy_id)


@router.post("/{taxonomy_id}/draft", response_model=TaxonomyResponse, responses=_ERRORS)
def open_draft(taxonomy_id: str, session: Session = Depends(get_session)) -> TaxonomyResponse:
    return taxonomy_service.open_draft(session, taxonomy_id)


@router.get("/{taxonomy_id}/versions", response_model=VersionListResponse, responses=_ERRORS)
def list_versions(taxonomy_id: str, session: Session = Depends(get_session)) -> VersionListResponse:
    return taxonomy_service.list_versions(session, taxonomy_id)


@router.get("/{taxonomy_id}/versions/{version}", response_model=VersionSummary, responses=_ERRORS)
def get_version(
    taxonomy_id: str, version: int, session: Session = Depends(get_session)
) -> VersionSummary:
    return taxonomy_service.get_version(session, taxonomy_id, version)


@router.get("/{taxonomy_id}/entities", response_model=TaxonomyEntityListResponse, responses=_ERRORS)
def list_entities(
    taxonomy_id: str,
    version: int | None = None,
    classification: str | None = None,
    session: Session = Depends(get_session),
) -> TaxonomyEntityListResponse:
    return taxonomy_service.list_entities(
        session, taxonomy_id, version=version, classification=classification
    )


@router.post(
    "/{taxonomy_id}/entities",
    response_model=TaxonomyEntityResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERRORS,
)
def create_entity(
    taxonomy_id: str, payload: TaxonomyEntityCreate, session: Session = Depends(get_session)
) -> TaxonomyEntityResponse:
    return taxonomy_service.create_entity(session, taxonomy_id, payload)


@router.get(
    "/{taxonomy_id}/entities/{code}", response_model=TaxonomyEntityResponse, responses=_ERRORS
)
def get_entity(
    taxonomy_id: str,
    code: str,
    version: int | None = None,
    session: Session = Depends(get_session),
) -> TaxonomyEntityResponse:
    return taxonomy_service.get_entity(session, taxonomy_id, code, version=version)


@router.patch(
    "/{taxonomy_id}/entities/{code}", response_model=TaxonomyEntityResponse, responses=_ERRORS
)
def update_entity(
    taxonomy_id: str,
    code: str,
    payload: TaxonomyEntityUpdate,
    session: Session = Depends(get_session),
) -> TaxonomyEntityResponse:
    return taxonomy_service.update_entity(session, taxonomy_id, code, payload)


@router.delete(
    "/{taxonomy_id}/entities/{code}", status_code=status.HTTP_204_NO_CONTENT, responses=_ERRORS
)
def delete_entity(taxonomy_id: str, code: str, session: Session = Depends(get_session)) -> Response:
    taxonomy_service.delete_entity(session, taxonomy_id, code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
