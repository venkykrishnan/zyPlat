from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.application import ApplicationStatus
from ...models.company import PeriodGranularity
from . import service
from .schemas import (
    ApplicationCompanyResponse,
    ApplicationCreate,
    ApplicationDomainCreate,
    ApplicationDomainResponse,
    ApplicationSummaryResponse,
    ApplicationVersionCreate,
    ApplicationVersionResponse,
    ApplicationVersionUpdate,
    BindInstanceCreate,
    BindInstanceResponse,
    BindInstanceUpdate,
    SetDefaultRequest,
)

router = APIRouter()


@router.post("/", response_model=ApplicationVersionResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    return service.create_application(db, payload)


@router.get("/", response_model=list[ApplicationSummaryResponse])
def list_applications(
    application_id: str | None = None,
    app_status: ApplicationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return service.list_applications(db, application_id=application_id, status=app_status)


@router.get("/{application_id}", response_model=ApplicationVersionResponse)
def get_application(application_id: str, db: Session = Depends(get_db)):
    return service.get_default_version(db, application_id)


@router.post(
    "/{application_id}/versions",
    response_model=ApplicationVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_version(
    application_id: str, payload: ApplicationVersionCreate, db: Session = Depends(get_db)
):
    return service.add_version(db, application_id, payload)


@router.get("/{application_id}/versions/{version}", response_model=ApplicationVersionResponse)
def get_version(application_id: str, version: str, db: Session = Depends(get_db)):
    return service.get_version(db, application_id, version)


@router.put("/{application_id}/versions/{version}", response_model=ApplicationVersionResponse)
def update_version(
    application_id: str,
    version: str,
    payload: ApplicationVersionUpdate,
    db: Session = Depends(get_db),
):
    return service.update_version(db, application_id, version, payload)


@router.delete("/{application_id}/versions/{version}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(application_id: str, version: str, db: Session = Depends(get_db)):
    service.delete_version(db, application_id, version)


@router.post("/{application_id}/set-default", response_model=ApplicationVersionResponse)
def set_default(application_id: str, payload: SetDefaultRequest, db: Session = Depends(get_db)):
    return service.set_default(db, application_id, payload.version)


@router.post("/{application_id}/publish", response_model=ApplicationVersionResponse)
def publish(application_id: str, db: Session = Depends(get_db)):
    return service.publish(db, application_id)


@router.post("/{application_id}/unpublish", response_model=ApplicationVersionResponse)
def unpublish(application_id: str, db: Session = Depends(get_db)):
    return service.unpublish(db, application_id)


@router.post("/{application_id}/archive", response_model=ApplicationVersionResponse)
def archive(application_id: str, db: Session = Depends(get_db)):
    return service.archive(db, application_id)


@router.post(
    "/{application_id}/versions/{version}/domains",
    response_model=ApplicationDomainResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_domain(
    application_id: str,
    version: str,
    payload: ApplicationDomainCreate,
    db: Session = Depends(get_db),
):
    return service.add_output_domain(db, application_id, version, payload)


@router.get(
    "/{application_id}/versions/{version}/domains",
    response_model=list[ApplicationDomainResponse],
)
def list_domains(application_id: str, version: str, db: Session = Depends(get_db)):
    return service.list_domains(db, application_id, version)


@router.put(
    "/{application_id}/versions/{version}/companies/{company_id}",
    response_model=ApplicationCompanyResponse,
)
def enable_company(
    application_id: str, version: str, company_id: str, db: Session = Depends(get_db)
):
    return service.enable_company(db, application_id, version, company_id)


@router.get(
    "/{application_id}/versions/{version}/companies",
    response_model=list[ApplicationCompanyResponse],
)
def list_companies(application_id: str, version: str, db: Session = Depends(get_db)):
    return service.list_companies(db, application_id, version)


@router.delete(
    "/{application_id}/versions/{version}/companies/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disable_company(
    application_id: str, version: str, company_id: str, db: Session = Depends(get_db)
):
    service.disable_company(db, application_id, version, company_id)


@router.post(
    "/{application_id}/versions/{version}/bind-instances",
    response_model=BindInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bind_instance(
    application_id: str,
    version: str,
    payload: BindInstanceCreate,
    db: Session = Depends(get_db),
):
    return service.create_bind_instance(db, application_id, version, payload)


@router.get(
    "/{application_id}/versions/{version}/bind-instances",
    response_model=list[BindInstanceResponse],
)
def list_bind_instances(
    application_id: str,
    version: str,
    company_id: str | None = None,
    period_type: PeriodGranularity | None = None,
    period_value: str | None = None,
    db: Session = Depends(get_db),
):
    return service.list_bind_instances(
        db,
        application_id,
        version,
        company_id=company_id,
        period_type=period_type,
        period_value=period_value,
    )


@router.get(
    "/{application_id}/versions/{version}/bind-instances/{bind_instance_id}",
    response_model=BindInstanceResponse,
)
def get_bind_instance(
    application_id: str,
    version: str,
    bind_instance_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get_bind_instance(db, application_id, version, bind_instance_id)


@router.put(
    "/{application_id}/versions/{version}/bind-instances/{bind_instance_id}",
    response_model=BindInstanceResponse,
)
def update_bind_instance(
    application_id: str,
    version: str,
    bind_instance_id: UUID,
    payload: BindInstanceUpdate,
    db: Session = Depends(get_db),
):
    return service.update_bind_instance(db, application_id, version, bind_instance_id, payload)


@router.delete(
    "/{application_id}/versions/{version}/bind-instances/{bind_instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bind_instance(
    application_id: str,
    version: str,
    bind_instance_id: UUID,
    db: Session = Depends(get_db),
):
    service.delete_bind_instance(db, application_id, version, bind_instance_id)
