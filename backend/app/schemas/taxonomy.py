from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from ..models.taxonomy import DefinitionScope


class TaxonomyDefinitionBase(BaseModel):
    taxonomy_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    scope_type: DefinitionScope
    owner_company_id: Optional[UUID] = None
    description: str
    is_hierarchical: bool = False
    allowed_classifications: List[str] = Field(default_factory=list)
    is_published: bool = False
    is_default: bool = False


class TaxonomyDefinitionCreate(TaxonomyDefinitionBase):
    pass


class TaxonomyDefinitionUpdate(BaseModel):
    description: Optional[str] = None
    is_published: Optional[bool] = None
    is_default: Optional[bool] = None
    allowed_classifications: Optional[List[str]] = None


class TaxonomyDefinitionResponse(TaxonomyDefinitionBase):
    id: UUID
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxonomyEntityBase(BaseModel):
    entity_id: str = Field(..., min_length=1)
    value: str
    display_name: str
    description: str
    parent_entity_id: Optional[UUID] = None
    explicit_classifications: List[str] = Field(default_factory=list)
    is_base_entity: bool = True


class TaxonomyEntityCreate(TaxonomyEntityBase):
    taxonomy_definition_id: UUID


class TaxonomyEntityUpdate(BaseModel):
    value: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    parent_entity_id: Optional[UUID] = None
    explicit_classifications: Optional[List[str]] = None


class TaxonomyEntityResponse(TaxonomyEntityBase):
    id: UUID
    taxonomy_definition_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
