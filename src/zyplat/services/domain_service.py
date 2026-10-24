"""Domain definitions, instances, and the entities stored on an instance."""

from __future__ import annotations

import json

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zyplat.classification import CycleError, effective_classifications, is_admissible
from zyplat.clock import to_iso, utcnow
from zyplat.errors import AppError
from zyplat.models import (
    PUBLISHED,
    Domain,
    DomainDimension,
    DomainInstance,
    DomainInstanceDimension,
    DomainInstanceEntity,
    DomainInstanceEntityValue,
    Taxonomy,
    TaxonomyEntity,
    TaxonomyVersion,
)
from zyplat.schemas import (
    DimensionInput,
    DimensionResponse,
    DimensionValueResponse,
    DomainCreate,
    DomainListResponse,
    DomainResponse,
    DomainUpdate,
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
from zyplat.services.taxonomy_service import entities_for_version, render_entities

_MAX_ATTRIBUTES_BYTES = 16_384


def create_domain(session: Session, payload: DomainCreate) -> DomainResponse:
    _ensure_domain_name_available(session, payload.name)
    domain = Domain(name=payload.name, description=payload.description)
    session.add(domain)
    session.flush()
    _replace_dimensions(session, domain, payload.dimensions)
    session.flush()
    return _domain_response(session, domain)


def list_domains(session: Session) -> DomainListResponse:
    rows = list(session.scalars(select(Domain).order_by(Domain.name)).all())
    items = [_domain_response(session, row) for row in rows]
    return DomainListResponse(items=items, total=len(items))


def get_domain(session: Session, domain_id: str) -> DomainResponse:
    return _domain_response(session, _get_domain(session, domain_id))


def update_domain(session: Session, domain_id: str, payload: DomainUpdate) -> DomainResponse:
    domain = _get_domain(session, domain_id)
    fields = payload.model_fields_set
    _reject_null(fields, "name", payload.name, "name")
    _reject_null(fields, "description", payload.description, "description")
    _reject_null(fields, "dimensions", payload.dimensions, "dimensions")
    if "name" in fields and payload.name != domain.name:
        _ensure_domain_name_available(session, payload.name)
        domain.name = payload.name
    if "description" in fields:
        domain.description = payload.description or ""
    if "dimensions" in fields and payload.dimensions is not None:
        _replace_dimensions(session, domain, payload.dimensions)
    domain.updated_at = utcnow()
    session.flush()
    return _domain_response(session, domain)


def delete_domain(session: Session, domain_id: str) -> None:
    domain = _get_domain(session, domain_id)
    instance_count = session.scalar(
        select(func.count()).select_from(DomainInstance).where(DomainInstance.domain_id == domain.id)
    )
    if instance_count:
        raise AppError(
            "domain_in_use",
            "Delete the domain's instances before deleting the domain",
            409,
        )
    session.execute(sql_delete(DomainDimension).where(DomainDimension.domain_id == domain.id))
    session.delete(domain)
    session.flush()


def create_instance(session: Session, domain_id: str, payload: InstanceCreate) -> InstanceResponse:
    domain = _get_domain(session, domain_id)
    _ensure_instance_name_available(session, domain.id, payload.name)
    pins = _domain_dimensions(session, domain.id)
    inherited = _inherited_from_pins(session, pins)
    _ensure_subset(payload.classifications, inherited)
    instance = DomainInstance(
        domain_id=domain.id,
        name=payload.name,
        selected_classifications=list(payload.classifications),
    )
    session.add(instance)
    session.flush()
    for pin in pins:
        session.add(
            DomainInstanceDimension(
                instance_id=instance.id,
                name=pin.name,
                position=pin.position,
                taxonomy_id=pin.taxonomy_id,
                taxonomy_version_id=pin.taxonomy_version_id,
            )
        )
    domain.updated_at = utcnow()
    session.flush()
    return _instance_response(session, instance)


def list_instances(session: Session, domain_id: str) -> InstanceListResponse:
    domain = _get_domain(session, domain_id)
    rows = list(
        session.scalars(
            select(DomainInstance)
            .where(DomainInstance.domain_id == domain.id)
            .order_by(DomainInstance.name)
        ).all()
    )
    items = [_instance_response(session, row) for row in rows]
    return InstanceListResponse(items=items, total=len(items))


def get_instance(session: Session, instance_id: str) -> InstanceResponse:
    return _instance_response(session, _get_instance(session, instance_id))


def update_instance(
    session: Session, instance_id: str, payload: InstanceUpdate
) -> InstanceResponse:
    instance = _get_instance(session, instance_id)
    fields = payload.model_fields_set
    _reject_null(fields, "name", payload.name, "name")
    _reject_null(fields, "classifications", payload.classifications, "classifications")
    if "name" in fields and payload.name != instance.name:
        _ensure_instance_name_available(session, instance.domain_id, payload.name)
        instance.name = payload.name
    if "classifications" in fields and payload.classifications is not None:
        pins = _instance_dimensions(session, instance.id)
        inherited = _inherited_from_pins(session, pins)
        _ensure_subset(payload.classifications, inherited)
        _ensure_entities_stay_admissible(session, instance, payload.classifications)
        instance.selected_classifications = list(payload.classifications)
    instance.updated_at = utcnow()
    session.flush()
    return _instance_response(session, instance)


def delete_instance(session: Session, instance_id: str) -> None:
    instance = _get_instance(session, instance_id)
    entity_ids = list(
        session.scalars(
            select(DomainInstanceEntity.id).where(DomainInstanceEntity.instance_id == instance.id)
        ).all()
    )
    if entity_ids:
        session.execute(
            sql_delete(DomainInstanceEntityValue).where(
                DomainInstanceEntityValue.instance_entity_id.in_(entity_ids)
            )
        )
        session.execute(
            sql_delete(DomainInstanceEntity).where(DomainInstanceEntity.instance_id == instance.id)
        )
    session.execute(
        sql_delete(DomainInstanceDimension).where(DomainInstanceDimension.instance_id == instance.id)
    )
    session.delete(instance)
    session.flush()


def create_instance_entity(
    session: Session, instance_id: str, payload: InstanceEntityCreate
) -> InstanceEntityResponse:
    instance = _get_instance(session, instance_id)
    if _instance_entity_by_code(session, instance.id, payload.code) is not None:
        raise AppError("code_conflict", f"Entity '{payload.code}' already exists", 409)
    resolved = _resolve_dimension_values(session, instance, payload.dimensions)
    attributes = _check_attributes(payload.attributes)
    entity = DomainInstanceEntity(
        instance_id=instance.id,
        code=payload.code,
        name=payload.name,
        attributes=attributes,
    )
    session.add(entity)
    session.flush()
    _insert_values(session, entity.id, resolved)
    instance.updated_at = utcnow()
    session.flush()
    return _instance_entity_response(session, instance, entity)


def list_instance_entities(session: Session, instance_id: str) -> InstanceEntityListResponse:
    instance = _get_instance(session, instance_id)
    rows = list(
        session.scalars(
            select(DomainInstanceEntity)
            .where(DomainInstanceEntity.instance_id == instance.id)
            .order_by(DomainInstanceEntity.code)
        ).all()
    )
    items = [_instance_entity_response(session, instance, row) for row in rows]
    return InstanceEntityListResponse(items=items, total=len(items))


def get_instance_entity(session: Session, instance_id: str, code: str) -> InstanceEntityResponse:
    instance = _get_instance(session, instance_id)
    entity = _instance_entity_by_code(session, instance.id, code)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    return _instance_entity_response(session, instance, entity)


def update_instance_entity(
    session: Session, instance_id: str, code: str, payload: InstanceEntityUpdate
) -> InstanceEntityResponse:
    instance = _get_instance(session, instance_id)
    entity = _instance_entity_by_code(session, instance.id, code)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    fields = payload.model_fields_set
    _reject_null(fields, "name", payload.name, "name")
    _reject_null(fields, "dimensions", payload.dimensions, "dimensions")
    _reject_null(fields, "attributes", payload.attributes, "attributes")
    if "name" in fields and payload.name is not None:
        entity.name = payload.name
    if "attributes" in fields and payload.attributes is not None:
        entity.attributes = _check_attributes(payload.attributes)
    if "dimensions" in fields and payload.dimensions is not None:
        resolved = _resolve_dimension_values(session, instance, payload.dimensions)
        session.execute(
            sql_delete(DomainInstanceEntityValue).where(
                DomainInstanceEntityValue.instance_entity_id == entity.id
            )
        )
        session.flush()
        _insert_values(session, entity.id, resolved)
    entity.updated_at = utcnow()
    instance.updated_at = utcnow()
    session.flush()
    return _instance_entity_response(session, instance, entity)


def delete_instance_entity(session: Session, instance_id: str, code: str) -> None:
    instance = _get_instance(session, instance_id)
    entity = _instance_entity_by_code(session, instance.id, code)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    session.execute(
        sql_delete(DomainInstanceEntityValue).where(
            DomainInstanceEntityValue.instance_entity_id == entity.id
        )
    )
    session.delete(entity)
    instance.updated_at = utcnow()
    session.flush()


def list_dimension_values(
    session: Session, instance_id: str, dimension_name: str
) -> TaxonomyEntityListResponse:
    instance = _get_instance(session, instance_id)
    pin = _instance_dimension(session, instance.id, dimension_name)
    taxonomy = session.get(Taxonomy, pin.taxonomy_id)
    version = session.get(TaxonomyVersion, pin.taxonomy_version_id)
    if taxonomy is None or version is None:
        raise AppError("data_integrity", "Dimension pin is missing its taxonomy", 500)
    entities = entities_for_version(session, version.id)
    items = render_entities(taxonomy, version, entities)
    selected = list(instance.selected_classifications or [])
    legal = [item for item in items if is_admissible(item.effective_classifications, selected)]
    return TaxonomyEntityListResponse(
        items=legal,
        total=len(legal),
        version=version.version,
        status=version.status,
    )


def _reject_null(fields: set[str], field: str, value: object, label: str) -> None:
    if field in fields and value is None:
        raise AppError("validation_error", f"{label} cannot be null", 400)


def _get_domain(session: Session, domain_id: str) -> Domain:
    domain = session.get(Domain, domain_id)
    if domain is None:
        raise AppError("not_found", "Domain not found", 404)
    return domain


def _get_instance(session: Session, instance_id: str) -> DomainInstance:
    instance = session.get(DomainInstance, instance_id)
    if instance is None:
        raise AppError("not_found", "Domain instance not found", 404)
    return instance


def _ensure_domain_name_available(session: Session, name: str) -> None:
    existing = session.scalar(select(Domain.id).where(Domain.name == name))
    if existing is not None:
        raise AppError("name_conflict", f"Domain '{name}' already exists", 409)


def _ensure_instance_name_available(session: Session, domain_id: str, name: str) -> None:
    existing = session.scalar(
        select(DomainInstance.id).where(
            DomainInstance.domain_id == domain_id,
            DomainInstance.name == name,
        )
    )
    if existing is not None:
        raise AppError("name_conflict", f"Instance '{name}' already exists on this domain", 409)


def _domain_dimensions(session: Session, domain_id: str) -> list[DomainDimension]:
    return list(
        session.scalars(
            select(DomainDimension)
            .where(DomainDimension.domain_id == domain_id)
            .order_by(DomainDimension.position)
        ).all()
    )


def _instance_dimensions(session: Session, instance_id: str) -> list[DomainInstanceDimension]:
    return list(
        session.scalars(
            select(DomainInstanceDimension)
            .where(DomainInstanceDimension.instance_id == instance_id)
            .order_by(DomainInstanceDimension.position)
        ).all()
    )


def _instance_dimension(
    session: Session, instance_id: str, name: str
) -> DomainInstanceDimension:
    pin = session.scalar(
        select(DomainInstanceDimension).where(
            DomainInstanceDimension.instance_id == instance_id,
            DomainInstanceDimension.name == name,
        )
    )
    if pin is None:
        raise AppError("not_found", f"Dimension '{name}' not found on this instance", 404)
    return pin


def _replace_dimensions(session: Session, domain: Domain, dimensions: list[DimensionInput]) -> None:
    session.execute(sql_delete(DomainDimension).where(DomainDimension.domain_id == domain.id))
    session.flush()
    for position, item in enumerate(dimensions):
        taxonomy, version = _resolve_pin(session, item)
        session.add(
            DomainDimension(
                domain_id=domain.id,
                name=item.name,
                position=position,
                taxonomy_id=taxonomy.id,
                taxonomy_version_id=version.id,
            )
        )


def _resolve_pin(session: Session, item: DimensionInput) -> tuple[Taxonomy, TaxonomyVersion]:
    taxonomy: Taxonomy | None = None
    if item.taxonomy_id:
        taxonomy = session.get(Taxonomy, item.taxonomy_id)
        if taxonomy is None:
            raise AppError("not_found", "Taxonomy not found", 404, {"taxonomyId": item.taxonomy_id})
        if item.taxonomy_name and item.taxonomy_name != taxonomy.name:
            raise AppError(
                "validation_error",
                "taxonomyId and taxonomyName do not refer to the same taxonomy",
                400,
            )
    else:
        taxonomy = session.scalar(select(Taxonomy).where(Taxonomy.name == item.taxonomy_name))
        if taxonomy is None:
            raise AppError("not_found", f"Taxonomy '{item.taxonomy_name}' not found", 404)
    if item.version is None:
        version = session.scalar(
            select(TaxonomyVersion)
            .where(
                TaxonomyVersion.taxonomy_id == taxonomy.id,
                TaxonomyVersion.status == PUBLISHED,
            )
            .order_by(TaxonomyVersion.version.desc())
            .limit(1)
        )
        if version is None:
            raise AppError(
                "version_not_published",
                f"Taxonomy '{taxonomy.name}' has no published version",
                400,
            )
        return taxonomy, version
    version = session.scalar(
        select(TaxonomyVersion).where(
            TaxonomyVersion.taxonomy_id == taxonomy.id,
            TaxonomyVersion.version == item.version,
        )
    )
    if version is None:
        raise AppError(
            "not_found",
            f"Version {item.version} of taxonomy '{taxonomy.name}' not found",
            404,
        )
    if version.status != PUBLISHED:
        raise AppError(
            "version_not_published",
            "Domain dimensions must pin a published taxonomy version",
            400,
            {"taxonomy": taxonomy.name, "version": item.version},
        )
    return taxonomy, version


def _inherited_from_pins(
    session: Session, pins: list[DomainDimension] | list[DomainInstanceDimension]
) -> list[str]:
    inherited: list[str] = []
    for pin in pins:
        version = session.get(TaxonomyVersion, pin.taxonomy_version_id)
        if version is None:
            raise AppError("data_integrity", "Dimension pin is missing its taxonomy version", 500)
        for value in version.allowed_classifications or []:
            if value not in inherited:
                inherited.append(value)
    return inherited


def _ensure_subset(selected: list[str], inherited: list[str]) -> None:
    unknown = [value for value in selected if value not in inherited]
    if unknown:
        raise AppError(
            "instance_classifications_invalid",
            f"Classifications {unknown} are not inherited by this domain",
            400,
            {"classifications": unknown, "inheritedClassifications": inherited},
        )


def _dimension_response(session: Session, pin: DomainDimension | DomainInstanceDimension) -> DimensionResponse:
    taxonomy = session.get(Taxonomy, pin.taxonomy_id)
    version = session.get(TaxonomyVersion, pin.taxonomy_version_id)
    if taxonomy is None or version is None:
        raise AppError("data_integrity", "Dimension pin is missing its taxonomy", 500)
    return DimensionResponse(
        name=pin.name,
        taxonomy_id=taxonomy.id,
        taxonomy_name=taxonomy.name,
        taxonomy_version=version.version,
        taxonomy_version_id=version.id,
    )


def _domain_response(session: Session, domain: Domain) -> DomainResponse:
    pins = _domain_dimensions(session, domain.id)
    return DomainResponse(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        dimensions=[_dimension_response(session, pin) for pin in pins],
        inherited_classifications=_inherited_from_pins(session, pins),
        created_at=to_iso(domain.created_at),
        updated_at=to_iso(domain.updated_at),
    )


def _instance_response(session: Session, instance: DomainInstance) -> InstanceResponse:
    domain = session.get(Domain, instance.domain_id)
    if domain is None:
        raise AppError("data_integrity", "Instance is missing its domain", 500)
    pins = _instance_dimensions(session, instance.id)
    return InstanceResponse(
        id=instance.id,
        domain_id=domain.id,
        domain_name=domain.name,
        name=instance.name,
        classifications=list(instance.selected_classifications or []),
        inherited_classifications=_inherited_from_pins(session, pins),
        dimensions=[_dimension_response(session, pin) for pin in pins],
        created_at=to_iso(instance.created_at),
        updated_at=to_iso(instance.updated_at),
    )


def _instance_entity_by_code(
    session: Session, instance_id: str, code: str
) -> DomainInstanceEntity | None:
    return session.scalar(
        select(DomainInstanceEntity).where(
            DomainInstanceEntity.instance_id == instance_id,
            DomainInstanceEntity.code == code,
        )
    )


def _check_attributes(value: dict) -> dict:
    encoded = json.dumps(value).encode("utf-8")
    if len(encoded) > _MAX_ATTRIBUTES_BYTES:
        raise AppError("validation_error", "attributes must be at most 16KB of JSON", 400)
    return value


def _version_index(
    session: Session,
    version_id: str,
    cache: dict[str, tuple[dict[str, TaxonomyEntity], dict[str, TaxonomyEntity]]],
) -> tuple[dict[str, TaxonomyEntity], dict[str, TaxonomyEntity]]:
    cached = cache.get(version_id)
    if cached is not None:
        return cached
    entities = entities_for_version(session, version_id)
    indexed = ({entity.id: entity for entity in entities}, {entity.code: entity for entity in entities})
    cache[version_id] = indexed
    return indexed


def _resolve_dimension_values(
    session: Session, instance: DomainInstance, dimensions: dict[str, str]
) -> list[tuple[DomainInstanceDimension, TaxonomyEntity]]:
    pins = _instance_dimensions(session, instance.id)
    expected = [pin.name for pin in pins]
    missing = [name for name in expected if name not in dimensions]
    extra = [name for name in dimensions if name not in expected]
    if missing or extra:
        raise AppError(
            "dimension_invalid",
            "Instance entities must set every dimension exactly once",
            400,
            {"missing": missing, "extra": extra},
        )
    selected = list(instance.selected_classifications or [])
    cache: dict[str, tuple[dict[str, TaxonomyEntity], dict[str, TaxonomyEntity]]] = {}
    resolved: list[tuple[DomainInstanceDimension, TaxonomyEntity]] = []
    for pin in pins:
        code = dimensions[pin.name].strip()
        by_id, by_code = _version_index(session, pin.taxonomy_version_id, cache)
        taxonomy_entity = by_code.get(code)
        if taxonomy_entity is None:
            raise AppError(
                "not_found",
                f"Taxonomy entity '{code}' was not found for dimension '{pin.name}'",
                404,
                {"dimension": pin.name, "code": code},
            )
        try:
            effective = effective_classifications(taxonomy_entity.id, by_id)
        except CycleError as exc:
            raise AppError(
                "data_integrity", "Taxonomy entity hierarchy contains a cycle", 500
            ) from exc
        if not is_admissible(effective, selected):
            raise _not_admissible(pin.name, code, effective, selected)
        resolved.append((pin, taxonomy_entity))
    return resolved


def _not_admissible(
    dimension: str, code: str, effective: list[str], selected: list[str]
) -> AppError:
    if selected:
        allowance = "base entities and entities classified as " + ", ".join(selected)
    else:
        allowance = "only base entities"
    return AppError(
        "entity_not_admissible",
        (
            f"Taxonomy entity '{code}' is not valid for dimension '{dimension}' on this instance. "
            f"It is classified as {', '.join(effective)}; this instance allows {allowance}."
        ),
        400,
        {
            "dimension": dimension,
            "code": code,
            "effectiveClassifications": effective,
            "instanceClassifications": list(selected),
        },
    )


def _insert_values(
    session: Session,
    instance_entity_id: str,
    resolved: list[tuple[DomainInstanceDimension, TaxonomyEntity]],
) -> None:
    for pin, taxonomy_entity in resolved:
        session.add(
            DomainInstanceEntityValue(
                instance_entity_id=instance_entity_id,
                dimension_name=pin.name,
                taxonomy_entity_id=taxonomy_entity.id,
            )
        )


def _ensure_entities_stay_admissible(
    session: Session, instance: DomainInstance, selected: list[str]
) -> None:
    entities = list(
        session.scalars(
            select(DomainInstanceEntity).where(DomainInstanceEntity.instance_id == instance.id)
        ).all()
    )
    if not entities:
        return
    pins = _instance_dimensions(session, instance.id)
    cache: dict[str, tuple[dict[str, TaxonomyEntity], dict[str, TaxonomyEntity]]] = {}
    invalid: list[str] = []
    for entity in entities:
        values = list(
            session.scalars(
                select(DomainInstanceEntityValue).where(
                    DomainInstanceEntityValue.instance_entity_id == entity.id
                )
            ).all()
        )
        by_dimension = {value.dimension_name: value for value in values}
        for pin in pins:
            value = by_dimension.get(pin.name)
            if value is None:
                invalid.append(entity.code)
                break
            by_id, _by_code = _version_index(session, pin.taxonomy_version_id, cache)
            taxonomy_entity = by_id.get(value.taxonomy_entity_id)
            if taxonomy_entity is None:
                invalid.append(entity.code)
                break
            try:
                effective = effective_classifications(taxonomy_entity.id, by_id)
            except CycleError as exc:
                raise AppError(
                    "data_integrity", "Taxonomy entity hierarchy contains a cycle", 500
                ) from exc
            if not is_admissible(effective, selected):
                invalid.append(entity.code)
                break
    if invalid:
        unique = sorted(set(invalid))
        raise AppError(
            "instance_classifications_invalid",
            "Changing classifications would make existing entities invalid",
            409,
            {"entities": unique},
        )


def _instance_entity_response(
    session: Session, instance: DomainInstance, entity: DomainInstanceEntity
) -> InstanceEntityResponse:
    pins = _instance_dimensions(session, instance.id)
    values = list(
        session.scalars(
            select(DomainInstanceEntityValue).where(
                DomainInstanceEntityValue.instance_entity_id == entity.id
            )
        ).all()
    )
    by_dimension = {value.dimension_name: value for value in values}
    cache: dict[str, tuple[dict[str, TaxonomyEntity], dict[str, TaxonomyEntity]]] = {}
    dimensions: dict[str, DimensionValueResponse] = {}
    for pin in pins:
        value = by_dimension.get(pin.name)
        if value is None:
            raise AppError("data_integrity", f"Entity '{entity.code}' is missing dimension '{pin.name}'", 500)
        by_id, _by_code = _version_index(session, pin.taxonomy_version_id, cache)
        taxonomy_entity = by_id.get(value.taxonomy_entity_id)
        if taxonomy_entity is None:
            raise AppError(
                "data_integrity",
                f"Entity '{entity.code}' points at a missing taxonomy entity",
                500,
            )
        try:
            effective = effective_classifications(taxonomy_entity.id, by_id)
        except CycleError as exc:
            raise AppError(
                "data_integrity", "Taxonomy entity hierarchy contains a cycle", 500
            ) from exc
        dimensions[pin.name] = DimensionValueResponse(
            code=taxonomy_entity.code,
            taxonomy_entity_id=taxonomy_entity.id,
            effective_classifications=effective,
        )
    return InstanceEntityResponse(
        id=entity.id,
        instance_id=instance.id,
        code=entity.code,
        name=entity.name,
        dimensions=dimensions,
        attributes=dict(entity.attributes or {}),
        created_at=to_iso(entity.created_at),
        updated_at=to_iso(entity.updated_at),
    )
