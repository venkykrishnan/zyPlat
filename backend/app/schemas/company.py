from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models.company import CompanyType


class CompanyBase(BaseModel):
    company_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    company_type: CompanyType
    customer_id: str | None = None
    is_enabled: bool = True
    is_test: bool = False
    naics_code: str | None = None
    state: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    report_info: list[dict[str, Any]] = Field(default_factory=list)


class CompanyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    company_type: CompanyType | None = None
    customer_id: str | None = None
    is_enabled: bool | None = None
    is_test: bool | None = None
    naics_code: str | None = None
    state: str | None = None
    report_info: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class CompanyResponse(CompanyBase):
    id: UUID
    report_info: list[dict[str, Any]]
    # The ORM attribute is `metadata_` because `metadata` is reserved by SQLAlchemy's declarative
    # base. Reading `metadata` from the model would return the table registry, not the column.
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
