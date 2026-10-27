from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from ..models.domain import DomainKind
from ..models.taxonomy import DefinitionScope


class DomainDefinitionBase(BaseModel):
    domain_id: str = Field(..., min_length=1)
    description: str
    kind: DomainKind
    scope_type: DefinitionScope
    owner_company_id: Optional[UUID] = None


class DomainDefinitionCreate(DomainDefinitionBase):
    pass


class DomainDefinitionUpdate(BaseModel):
    description: Optional[str] = None


class DomainDefinitionResponse(DomainDefinitionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
