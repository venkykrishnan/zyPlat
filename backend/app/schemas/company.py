from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from ..models.company import CompanyType, PeriodGranularity


class CompanyBase(BaseModel):
    company_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    company_type: CompanyType
    customer_id: Optional[str] = None
    is_enabled: bool = True
    is_test: bool = False
    naics_code: Optional[str] = None
    state: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    report_info: List[Dict[str, Any]] = Field(default_factory=list)


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_type: Optional[CompanyType] = None
    customer_id: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_test: Optional[bool] = None
    naics_code: Optional[str] = None
    state: Optional[str] = None
    report_info: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class CompanyResponse(CompanyBase):
    id: UUID
    report_info: List[Dict[str, Any]]
    # The ORM attribute is `metadata_` because `metadata` is reserved by SQLAlchemy's declarative
    # base. Reading `metadata` from the model would return the table registry, not the column.
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
