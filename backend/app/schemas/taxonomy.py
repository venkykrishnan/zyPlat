from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models.taxonomy import DefinitionScope


class TaxonomyDefinitionBase(BaseModel):
    taxonomy_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    scope_type: DefinitionScope
    owner_company_id: UUID | None = None
    description: str
    is_hierarchical: bool = False
    allowed_classifications: list[str] = Field(default_factory=list)
    is_published: bool = False
    is_default: bool = False


class TaxonomyDefinitionCreate(TaxonomyDefinitionBase):
    pass


class TaxonomyDefinitionUpdate(BaseModel):
    description: str | None = None
    is_published: bool | None = None
    is_default: bool | None = None
    allowed_classifications: list[str] | None = None


class TaxonomyDefinitionResponse(TaxonomyDefinitionBase):
    id: UUID
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxonomyEntityBase(BaseModel):
    entity_id: str = Field(..., min_length=1)
    value: str
    display_name: str
    description: str
    parent_entity_id: UUID | None = None
    explicit_classifications: list[str] = Field(default_factory=list)
    is_base_entity: bool = True


class TaxonomyEntityCreate(TaxonomyEntityBase):
    taxonomy_definition_id: UUID


class TaxonomyEntityUpdate(BaseModel):
    value: str | None = None
    display_name: str | None = None
    description: str | None = None
    parent_entity_id: UUID | None = None
    explicit_classifications: list[str] | None = None


class TaxonomyEntityResponse(TaxonomyEntityBase):
    id: UUID
    taxonomy_definition_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
