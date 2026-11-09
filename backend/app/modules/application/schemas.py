from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ...models.application import ApplicationDomainRole, ApplicationStatus, SnapshotAlignment
from ...models.company import PeriodGranularity
from ...models.domain import DomainDimensionDataType, DomainKind, DomainMetricDataType


class ExpectedDimension(BaseModel):
    name: str
    data_type: DomainDimensionDataType
    taxonomy_id: str | None = None
    taxonomy_version: str | None = None


class ExpectedMetric(BaseModel):
    name: str
    data_type: DomainMetricDataType


class ExpectedDomainSchema(BaseModel):
    kind: DomainKind
    time_series_dimension: str | None = None
    period_type: PeriodGranularity | None = None
    dimensions: list[ExpectedDimension] = Field(default_factory=list)
    metrics: list[ExpectedMetric] = Field(default_factory=list)


class ApplicationDomainCreate(BaseModel):
    domain_id: str
    role: ApplicationDomainRole
    snapshot_alignment: SnapshotAlignment = SnapshotAlignment.COMPANY
    owner_company_id: UUID | None = None
    expected: ExpectedDomainSchema


class ApplicationCreate(BaseModel):
    application_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    domains: list[ApplicationDomainCreate] = Field(default_factory=list)


class ApplicationVersionCreate(BaseModel):
    version: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    domains: list[ApplicationDomainCreate] = Field(default_factory=list)


class ApplicationVersionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None


class SetDefaultRequest(BaseModel):
    version: str = Field(..., min_length=1)


class ApplicationDomainResponse(BaseModel):
    id: UUID
    domain_definition_id: UUID
    domain_id: str
    role: ApplicationDomainRole
    snapshot_alignment: SnapshotAlignment
    schema_hash: str

    model_config = ConfigDict(from_attributes=True)


class ApplicationVersionResponse(BaseModel):
    id: UUID
    application_id: str
    version: str
    name: str
    description: str
    status: ApplicationStatus
    is_default: bool
    domains: list[ApplicationDomainResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplicationSummaryResponse(BaseModel):
    id: UUID
    application_id: str
    status: ApplicationStatus
    default_version: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationCompanyResponse(BaseModel):
    company_id: str
    company_uuid: UUID
    created_at: datetime


class BindMemberCreate(BaseModel):
    domain_id: str
    domain_instance_snapshot_id: UUID


class BindInstanceCreate(BaseModel):
    company_id: str
    period_type: PeriodGranularity | None = None
    period_value: str | None = None
    company_snapshot_id: UUID | None = None
    members: list[BindMemberCreate] = Field(default_factory=list)
    resolve_independent_members: bool = True


class BindInstanceUpdate(BaseModel):
    members: list[BindMemberCreate] = Field(default_factory=list)


class BindMemberResponse(BaseModel):
    domain_id: str
    domain_definition_id: UUID
    domain_instance_snapshot_id: UUID


class BindInstanceResponse(BaseModel):
    id: UUID
    application_id: str
    version: str
    company_id: str
    company_snapshot_id: UUID
    period_type: PeriodGranularity
    period_value: str
    members: list[BindMemberResponse]
    created_at: datetime
    updated_at: datetime
