"""Domain and domain-instance HTTP routes."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from zyplat.db import get_session
from zyplat.schemas import (
    DomainCreate,
    DomainListResponse,
    DomainResponse,
    DomainUpdate,
    ErrorResponse,
    InstanceCreate,
    InstanceEntityCreate,
    InstanceEntityListResponse,
    InstanceEntityResponse,
    InstanceEntityUpdate,
    InstanceListResponse,
    InstanceResponse,
    InstanceUpdate,
    TaxonomyEntityListResponse,
)
from zyplat.services import domain_service

_ERRORS = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}

domains_router = APIRouter(prefix="/domains", tags=["domains"])
instances_router = APIRouter(prefix="/domain-instances", tags=["domain-instances"])


@domains_router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED, responses=_ERRORS)
def create_domain(payload: DomainCreate, session: Session = Depends(get_session)) -> DomainResponse:
    return domain_service.create_domain(session, payload)


@domains_router.get("", response_model=DomainListResponse, responses=_ERRORS)
def list_domains(session: Session = Depends(get_session)) -> DomainListResponse:
    return domain_service.list_domains(session)


@domains_router.get("/{domain_id}", response_model=DomainResponse, responses=_ERRORS)
def get_domain(domain_id: str, session: Session = Depends(get_session)) -> DomainResponse:
    return domain_service.get_domain(session, domain_id)


@domains_router.patch("/{domain_id}", response_model=DomainResponse, responses=_ERRORS)
def update_domain(
    domain_id: str, payload: DomainUpdate, session: Session = Depends(get_session)
) -> DomainResponse:
    return domain_service.update_domain(session, domain_id, payload)


@domains_router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_ERRORS)
def delete_domain(domain_id: str, session: Session = Depends(get_session)) -> Response:
    domain_service.delete_domain(session, domain_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@domains_router.post(
    "/{domain_id}/instances",
    response_model=InstanceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERRORS,
)
def create_instance(
    domain_id: str, payload: InstanceCreate, session: Session = Depends(get_session)
) -> InstanceResponse:
    return domain_service.create_instance(session, domain_id, payload)


@domains_router.get("/{domain_id}/instances", response_model=InstanceListResponse, responses=_ERRORS)
def list_instances(domain_id: str, session: Session = Depends(get_session)) -> InstanceListResponse:
    return domain_service.list_instances(session, domain_id)


@instances_router.get("/{instance_id}", response_model=InstanceResponse, responses=_ERRORS)
def get_instance(instance_id: str, session: Session = Depends(get_session)) -> InstanceResponse:
    return domain_service.get_instance(session, instance_id)


@instances_router.patch("/{instance_id}", response_model=InstanceResponse, responses=_ERRORS)
def update_instance(
    instance_id: str, payload: InstanceUpdate, session: Session = Depends(get_session)
) -> InstanceResponse:
    return domain_service.update_instance(session, instance_id, payload)


@instances_router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_ERRORS)
def delete_instance(instance_id: str, session: Session = Depends(get_session)) -> Response:
    domain_service.delete_instance(session, instance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@instances_router.get(
    "/{instance_id}/entities", response_model=InstanceEntityListResponse, responses=_ERRORS
)
def list_instance_entities(
    instance_id: str, session: Session = Depends(get_session)
) -> InstanceEntityListResponse:
    return domain_service.list_instance_entities(session, instance_id)


@instances_router.post(
    "/{instance_id}/entities",
    response_model=InstanceEntityResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERRORS,
)
def create_instance_entity(
    instance_id: str, payload: InstanceEntityCreate, session: Session = Depends(get_session)
) -> InstanceEntityResponse:
    return domain_service.create_instance_entity(session, instance_id, payload)


@instances_router.get(
    "/{instance_id}/dimensions/{dimension_name}/values",
    response_model=TaxonomyEntityListResponse,
    responses=_ERRORS,
)
def list_dimension_values(
    instance_id: str, dimension_name: str, session: Session = Depends(get_session)
) -> TaxonomyEntityListResponse:
    return domain_service.list_dimension_values(session, instance_id, dimension_name)


@instances_router.get(
    "/{instance_id}/entities/{code}", response_model=InstanceEntityResponse, responses=_ERRORS
)
def get_instance_entity(
    instance_id: str, code: str, session: Session = Depends(get_session)
) -> InstanceEntityResponse:
    return domain_service.get_instance_entity(session, instance_id, code)


@instances_router.patch(
    "/{instance_id}/entities/{code}", response_model=InstanceEntityResponse, responses=_ERRORS
)
def update_instance_entity(
    instance_id: str,
    code: str,
    payload: InstanceEntityUpdate,
    session: Session = Depends(get_session),
) -> InstanceEntityResponse:
    return domain_service.update_instance_entity(session, instance_id, code, payload)


@instances_router.delete(
    "/{instance_id}/entities/{code}", status_code=status.HTTP_204_NO_CONTENT, responses=_ERRORS
)
def delete_instance_entity(
    instance_id: str, code: str, session: Session = Depends(get_session)
) -> Response:
    domain_service.delete_instance_entity(session, instance_id, code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
