from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models.company import PeriodGranularity
from ..models.domain import (
    DomainDimensionDataType,
    DomainKind,
    DomainMetricDataType,
    TaxonomyVersionStrategy,
)
from ..models.taxonomy import DefinitionScope


class DomainDimensionBase(BaseModel):
    name: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    data_type: DomainDimensionDataType
    required: bool = False
    is_filter: bool = False
    ordinal: int
    taxonomy_id: str | None = None
    taxonomy_version_strategy: TaxonomyVersionStrategy | None = None
    taxonomy_version: str | None = None
    is_time_series: bool = False
    period_type: PeriodGranularity | None = None

    @model_validator(mode="after")
    def validate_time_series_fields(self) -> DomainDimensionBase:
        if self.is_time_series:
            if self.period_type is None:
                raise ValueError("period_type is required when is_time_series is true")
            if self.data_type != DomainDimensionDataType.DATETIME:
                raise ValueError("time-series dimensions must have data_type DATETIME")
        elif self.period_type is not None:
            raise ValueError("period_type is only allowed when is_time_series is true")
        return self


class DomainDimensionCreate(DomainDimensionBase):
    pass


class DomainDimensionUpdate(BaseModel):
    display_name: str | None = None
    required: bool | None = None
    is_filter: bool | None = None
    ordinal: int | None = None
    taxonomy_id: str | None = None
    taxonomy_version_strategy: TaxonomyVersionStrategy | None = None
    taxonomy_version: str | None = None
    is_time_series: bool | None = None
    period_type: PeriodGranularity | None = None
    data_type: DomainDimensionDataType | None = None


class DomainDimensionResponse(DomainDimensionBase):
    id: UUID
    domain_definition_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DomainMetricBase(BaseModel):
    name: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    data_type: DomainMetricDataType
    required: bool = False
    ordinal: int


class DomainMetricCreate(DomainMetricBase):
    pass


class DomainMetricResponse(DomainMetricBase):
    id: UUID
    domain_definition_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DomainDefinitionBase(BaseModel):
    domain_id: str = Field(..., min_length=1)
    description: str
    kind: DomainKind
    scope_type: DefinitionScope
    owner_company_id: UUID | None = None


class DomainDefinitionCreate(DomainDefinitionBase):
    dimensions: list[DomainDimensionCreate] = Field(default_factory=list)
    metrics: list[DomainMetricCreate] = Field(default_factory=list)


class DomainDefinitionUpdate(BaseModel):
    description: str | None = None


class DomainDefinitionResponse(DomainDefinitionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    dimensions: list[DomainDimensionResponse] = Field(default_factory=list)
    metrics: list[DomainMetricResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
