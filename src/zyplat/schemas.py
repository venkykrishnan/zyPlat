"""Request and response models. JSON fields are camelCase."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from zyplat.validation import (
    normalize_classification_list,
    normalize_description,
    normalize_display_name,
    normalize_identifier,
)


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorBody(APIModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorBody


class TaxonomyCreate(APIModel):
    name: str
    description: str = ""
    is_hierarchical: bool
    allowed_classifications: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return normalize_description(value)

    @field_validator("allowed_classifications")
    @classmethod
    def _classifications(cls, value: list[str]) -> list[str]:
        return normalize_classification_list(value)


class TaxonomyUpdate(APIModel):
    name: str | None = None
    description: str | None = None
    allowed_classifications: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_description(value)

    @field_validator("allowed_classifications")
    @classmethod
    def _classifications(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_classification_list(value)


class VersionSummary(APIModel):
    version: int
    status: str
    allowed_classifications: list[str]
    published_at: str | None
    entity_count: int
    created_at: str
    updated_at: str


class TaxonomyResponse(APIModel):
    id: str
    name: str
    description: str
    is_hierarchical: bool
    created_at: str
    updated_at: str
    latest_version: VersionSummary
    latest_published_version: int | None


class TaxonomyListResponse(APIModel):
    items: list[TaxonomyResponse]
    total: int


class VersionListResponse(APIModel):
    items: list[VersionSummary]
    total: int


class TaxonomyEntityCreate(APIModel):
    code: str
    name: str
    parent_code: str | None = None
    classifications: list[str] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_display_name(value)

    @field_validator("parent_code")
    @classmethod
    def _parent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @field_validator("classifications")
    @classmethod
    def _classifications(cls, value: list[str]) -> list[str]:
        return normalize_classification_list(value)


class TaxonomyEntityUpdate(APIModel):
    name: str | None = None
    parent_code: str | None = None
    classifications: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_display_name(value)

    @field_validator("parent_code")
    @classmethod
    def _parent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @field_validator("classifications")
    @classmethod
    def _classifications(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_classification_list(value)


class TaxonomyEntityResponse(APIModel):
    id: str
    taxonomy_id: str
    version: int
    code: str
    name: str
    parent_code: str | None
    depth: int
    classifications: list[str]
    effective_classifications: list[str]
    is_base: bool
    created_at: str
    updated_at: str


class TaxonomyEntityListResponse(APIModel):
    items: list[TaxonomyEntityResponse]
    total: int
    version: int
    status: str


class DimensionInput(APIModel):
    name: str
    taxonomy_id: str | None = None
    taxonomy_name: str | None = None
    version: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("taxonomy_name")
    @classmethod
    def _taxonomy_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @model_validator(mode="after")
    def _one_taxonomy_ref(self) -> DimensionInput:
        if not self.taxonomy_id and not self.taxonomy_name:
            raise ValueError("dimension requires taxonomyId or taxonomyName")
        return self


class DomainCreate(APIModel):
    name: str
    description: str = ""
    dimensions: list[DimensionInput]

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return normalize_description(value)

    @field_validator("dimensions")
    @classmethod
    def _dimensions(cls, value: list[DimensionInput]) -> list[DimensionInput]:
        if not value:
            raise ValueError("a domain needs at least one dimension")
        names = [item.name for item in value]
        if len(names) != len(set(names)):
            raise ValueError("dimension names must be unique")
        return value


class DomainUpdate(APIModel):
    name: str | None = None
    description: str | None = None
    dimensions: list[DimensionInput] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_description(value)

    @field_validator("dimensions")
    @classmethod
    def _dimensions(cls, value: list[DimensionInput] | None) -> list[DimensionInput] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("a domain needs at least one dimension")
        names = [item.name for item in value]
        if len(names) != len(set(names)):
            raise ValueError("dimension names must be unique")
        return value


class DimensionResponse(APIModel):
    name: str
    taxonomy_id: str
    taxonomy_name: str
    taxonomy_version: int
    taxonomy_version_id: str


class DomainResponse(APIModel):
    id: str
    name: str
    description: str
    dimensions: list[DimensionResponse]
    inherited_classifications: list[str]
    created_at: str
    updated_at: str


class DomainListResponse(APIModel):
    items: list[DomainResponse]
    total: int


class InstanceCreate(APIModel):
    name: str
    classifications: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("classifications")
    @classmethod
    def _classifications(cls, value: list[str]) -> list[str]:
        return normalize_classification_list(value)


class InstanceUpdate(APIModel):
    name: str | None = None
    classifications: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_identifier(value)

    @field_validator("classifications")
    @classmethod
    def _classifications(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_classification_list(value)


class InstanceResponse(APIModel):
    id: str
    domain_id: str
    domain_name: str
    name: str
    classifications: list[str]
    inherited_classifications: list[str]
    dimensions: list[DimensionResponse]
    created_at: str
    updated_at: str


class InstanceListResponse(APIModel):
    items: list[InstanceResponse]
    total: int


class InstanceEntityCreate(APIModel):
    code: str
    name: str
    dimensions: dict[str, str]
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def _code(cls, value: str) -> str:
        return normalize_identifier(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return normalize_display_name(value)


class InstanceEntityUpdate(APIModel):
    name: str | None = None
    dimensions: dict[str, str] | None = None
    attributes: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_display_name(value)


class DimensionValueResponse(APIModel):
    code: str
    taxonomy_entity_id: str
    effective_classifications: list[str]


class InstanceEntityResponse(APIModel):
    id: str
    instance_id: str
    code: str
    name: str
    dimensions: dict[str, DimensionValueResponse]
    attributes: dict[str, Any]
    created_at: str
    updated_at: str


class InstanceEntityListResponse(APIModel):
    items: list[InstanceEntityResponse]
    total: int
