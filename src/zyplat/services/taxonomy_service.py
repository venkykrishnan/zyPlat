"""Taxonomy identity, versions, and entities."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zyplat.classification import CycleError, effective_classifications
from zyplat.clock import to_iso, utcnow
from zyplat.errors import AppError
from zyplat.hierarchy import HierarchyError, validate_entities
from zyplat.models import (
    DRAFT,
    PUBLISHED,
    DomainDimension,
    DomainInstanceDimension,
    Taxonomy,
    TaxonomyEntity,
    TaxonomyVersion,
)
from zyplat.schemas import (
    TaxonomyCreate,
    TaxonomyEntityCreate,
    TaxonomyEntityListResponse,
    TaxonomyEntityResponse,
    TaxonomyEntityUpdate,
    TaxonomyListResponse,
    TaxonomyResponse,
    TaxonomyUpdate,
    VersionListResponse,
    VersionSummary,
)


def create_taxonomy(session: Session, payload: TaxonomyCreate) -> TaxonomyResponse:
    _ensure_name_available(session, payload.name)
    taxonomy = Taxonomy(
        name=payload.name,
        description=payload.description,
        is_hierarchical=payload.is_hierarchical,
    )
    session.add(taxonomy)
    session.flush()
    session.add(
        TaxonomyVersion(
            taxonomy_id=taxonomy.id,
            version=1,
            status=DRAFT,
            allowed_classifications=list(payload.allowed_classifications),
        )
    )
    session.flush()
    return _taxonomy_response(session, taxonomy)


def list_taxonomies(session: Session) -> TaxonomyListResponse:
    rows = list(session.scalars(select(Taxonomy).order_by(Taxonomy.name)).all())
    items = [_taxonomy_response(session, row) for row in rows]
    return TaxonomyListResponse(items=items, total=len(items))


def get_taxonomy(session: Session, taxonomy_id: str) -> TaxonomyResponse:
    return _taxonomy_response(session, _get_taxonomy(session, taxonomy_id))


def update_taxonomy(session: Session, taxonomy_id: str, payload: TaxonomyUpdate) -> TaxonomyResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    fields = payload.model_fields_set
    _reject_null(fields, "name", payload.name, "name")
    _reject_null(fields, "description", payload.description, "description")
    _reject_null(fields, "allowed_classifications", payload.allowed_classifications, "allowedClassifications")
    if "allowed_classifications" in fields and payload.allowed_classifications is not None:
        draft = _require_draft(session, taxonomy.id)
        _ensure_classifications_cover_entities(
            session, draft, payload.allowed_classifications
        )
        draft.allowed_classifications = list(payload.allowed_classifications)
        draft.updated_at = utcnow()
    if "name" in fields and payload.name is not None and payload.name != taxonomy.name:
        _ensure_name_available(session, payload.name)
        taxonomy.name = payload.name
    if "description" in fields and payload.description is not None:
        taxonomy.description = payload.description
    taxonomy.updated_at = utcnow()
    session.flush()
    return _taxonomy_response(session, taxonomy)


def delete_taxonomy(session: Session, taxonomy_id: str) -> None:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    versions = _versions(session, taxonomy.id)
    version_ids = [version.id for version in versions]
    if version_ids and _version_is_pinned(session, version_ids):
        raise AppError(
            "taxonomy_in_use",
            "Taxonomy is pinned by a domain or a domain instance",
            409,
        )
    if version_ids:
        session.execute(
            sql_delete(TaxonomyEntity).where(TaxonomyEntity.taxonomy_version_id.in_(version_ids))
        )
        session.execute(sql_delete(TaxonomyVersion).where(TaxonomyVersion.taxonomy_id == taxonomy.id))
    session.delete(taxonomy)
    try:
        session.flush()
    except IntegrityError as exc:
        raise AppError(
            "taxonomy_in_use",
            "Taxonomy is pinned by a domain or a domain instance",
            409,
        ) from exc


def publish_taxonomy(session: Session, taxonomy_id: str) -> TaxonomyResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    latest = _latest_version(session, taxonomy.id)
    if latest.status != DRAFT:
        raise AppError("no_draft", "There is no draft to publish", 409)
    entities = _entities(session, latest.id)
    allowed = list(latest.allowed_classifications or [])
    for entity in entities:
        unknown = [value for value in (entity.classifications or []) if value not in allowed]
        if unknown:
            raise AppError(
                "classification_not_allowed",
                f"Entity '{entity.code}' uses classifications that are not allowed: {unknown}",
                400,
                {"code": entity.code, "classifications": unknown},
            )
    try:
        validate_entities(entities, hierarchical=taxonomy.is_hierarchical)
    except HierarchyError as exc:
        raise AppError("hierarchy_error", exc.message, 400) from exc
    latest.status = PUBLISHED
    latest.published_at = utcnow()
    latest.updated_at = utcnow()
    taxonomy.updated_at = utcnow()
    session.flush()
    return _taxonomy_response(session, taxonomy)


def open_draft(session: Session, taxonomy_id: str) -> TaxonomyResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    latest = _latest_version(session, taxonomy.id)
    if latest.status == DRAFT:
        raise AppError("draft_exists", "A draft is already open", 409)
    if latest.status != PUBLISHED:
        raise AppError("no_draft", "There is no published version to clone", 409)
    draft = TaxonomyVersion(
        taxonomy_id=taxonomy.id,
        version=latest.version + 1,
        status=DRAFT,
        allowed_classifications=list(latest.allowed_classifications or []),
    )
    session.add(draft)
    session.flush()
    source_entities = _entities(session, latest.id)
    clones: list[tuple[TaxonomyEntity, TaxonomyEntity]] = []
    code_to_clone: dict[str, TaxonomyEntity] = {}
    for entity in source_entities:
        clone = TaxonomyEntity(
            taxonomy_version_id=draft.id,
            code=entity.code,
            name=entity.name,
            parent_id=None,
            classifications=list(entity.classifications or []),
        )
        session.add(clone)
        clones.append((entity, clone))
        code_to_clone[entity.code] = clone
    session.flush()
    old_by_id = {entity.id: entity for entity in source_entities}
    for entity, clone in clones:
        if entity.parent_id is None:
            continue
        parent_code = old_by_id[entity.parent_id].code
        clone.parent_id = code_to_clone[parent_code].id
    taxonomy.updated_at = utcnow()
    session.flush()
    return _taxonomy_response(session, taxonomy)


def list_versions(session: Session, taxonomy_id: str) -> VersionListResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    versions = _versions(session, taxonomy.id)
    items = [_version_summary(session, version) for version in versions]
    return VersionListResponse(items=items, total=len(items))


def get_version(session: Session, taxonomy_id: str, version: int) -> VersionSummary:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    return _version_summary(session, _version_by_number(session, taxonomy.id, version))


def list_entities(
    session: Session,
    taxonomy_id: str,
    *,
    version: int | None = None,
    classification: str | None = None,
) -> TaxonomyEntityListResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    target = _resolve_read_version(session, taxonomy.id, version)
    items = _entity_responses(taxonomy, target, _entities(session, target.id))
    if classification is not None:
        classification = classification.strip()
    if classification:
        items = _filter_by_classification(target, items, classification)
    return TaxonomyEntityListResponse(
        items=items,
        total=len(items),
        version=target.version,
        status=target.status,
    )


def create_entity(
    session: Session, taxonomy_id: str, payload: TaxonomyEntityCreate
) -> TaxonomyEntityResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    draft = _require_draft(session, taxonomy.id)
    _ensure_classifications_allowed(draft, payload.classifications, payload.code)
    if _entity_by_code(session, draft.id, payload.code) is not None:
        raise AppError("code_conflict", f"Entity '{payload.code}' already exists", 409)
    entities = _entities(session, draft.id)
    by_code = {entity.code: entity for entity in entities}
    parent = _resolve_parent_for_create(taxonomy, entities, by_code, payload.parent_code)
    entity = TaxonomyEntity(
        taxonomy_version_id=draft.id,
        code=payload.code,
        name=payload.name,
        parent_id=parent.id if parent is not None else None,
        classifications=list(payload.classifications),
    )
    session.add(entity)
    draft.updated_at = utcnow()
    taxonomy.updated_at = utcnow()
    session.flush()
    entities.append(entity)
    return _one_entity_response(taxonomy, draft, entities, entity)


def get_entity(
    session: Session, taxonomy_id: str, code: str, *, version: int | None = None
) -> TaxonomyEntityResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    target = _resolve_read_version(session, taxonomy.id, version)
    entities = _entities(session, target.id)
    entity = next((item for item in entities if item.code == code), None)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    return _one_entity_response(taxonomy, target, entities, entity)


def update_entity(
    session: Session, taxonomy_id: str, code: str, payload: TaxonomyEntityUpdate
) -> TaxonomyEntityResponse:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    draft = _require_draft(session, taxonomy.id)
    entities = _entities(session, draft.id)
    entity = next((item for item in entities if item.code == code), None)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    fields = payload.model_fields_set
    _reject_null(fields, "name", payload.name, "name")
    _reject_null(fields, "classifications", payload.classifications, "classifications")
    if "name" in fields and payload.name is not None:
        entity.name = payload.name
    if "classifications" in fields and payload.classifications is not None:
        _ensure_classifications_allowed(draft, payload.classifications, code)
        entity.classifications = list(payload.classifications)
    if "parent_code" in fields:
        _reparent(taxonomy, entities, entity, payload.parent_code)
    entity.updated_at = utcnow()
    draft.updated_at = utcnow()
    taxonomy.updated_at = utcnow()
    session.flush()
    return _one_entity_response(taxonomy, draft, entities, entity)


def delete_entity(session: Session, taxonomy_id: str, code: str) -> None:
    taxonomy = _get_taxonomy(session, taxonomy_id)
    draft = _require_draft(session, taxonomy.id)
    entities = _entities(session, draft.id)
    entity = next((item for item in entities if item.code == code), None)
    if entity is None:
        raise AppError("not_found", f"Entity '{code}' not found", 404)
    child_codes = [item.code for item in entities if item.parent_id == entity.id]
    if child_codes:
        raise AppError(
            "has_children",
            f"Entity '{code}' has children and cannot be deleted",
            409,
            {"children": sorted(child_codes)},
        )
    session.delete(entity)
    draft.updated_at = utcnow()
    taxonomy.updated_at = utcnow()
    session.flush()


def _reject_null(fields: set[str], field: str, value: object, label: str) -> None:
    if field in fields and value is None:
        raise AppError("validation_error", f"{label} cannot be null", 400)


def _get_taxonomy(session: Session, taxonomy_id: str) -> Taxonomy:
    taxonomy = session.get(Taxonomy, taxonomy_id)
    if taxonomy is None:
        raise AppError("not_found", "Taxonomy not found", 404)
    return taxonomy


def _versions(session: Session, taxonomy_id: str) -> list[TaxonomyVersion]:
    return list(
        session.scalars(
            select(TaxonomyVersion)
            .where(TaxonomyVersion.taxonomy_id == taxonomy_id)
            .order_by(TaxonomyVersion.version)
        ).all()
    )


def _latest_version(session: Session, taxonomy_id: str) -> TaxonomyVersion:
    version = session.scalar(
        select(TaxonomyVersion)
        .where(TaxonomyVersion.taxonomy_id == taxonomy_id)
        .order_by(TaxonomyVersion.version.desc())
        .limit(1)
    )
    if version is None:
        raise AppError("data_integrity", "Taxonomy has no versions", 500)
    return version


def _version_by_number(session: Session, taxonomy_id: str, number: int) -> TaxonomyVersion:
    version = session.scalar(
        select(TaxonomyVersion).where(
            TaxonomyVersion.taxonomy_id == taxonomy_id,
            TaxonomyVersion.version == number,
        )
    )
    if version is None:
        raise AppError("not_found", f"Version {number} not found", 404)
    return version


def _require_draft(session: Session, taxonomy_id: str) -> TaxonomyVersion:
    latest = _latest_version(session, taxonomy_id)
    if latest.status != DRAFT:
        raise AppError(
            "draft_required",
            "The latest version is published. Open a draft before changing it.",
            409,
        )
    return latest


def _resolve_read_version(
    session: Session, taxonomy_id: str, number: int | None
) -> TaxonomyVersion:
    if number is None:
        return _latest_version(session, taxonomy_id)
    return _version_by_number(session, taxonomy_id, number)


def _entities(session: Session, version_id: str) -> list[TaxonomyEntity]:
    return list(
        session.scalars(
            select(TaxonomyEntity).where(TaxonomyEntity.taxonomy_version_id == version_id)
        ).all()
    )


def _entity_by_code(session: Session, version_id: str, code: str) -> TaxonomyEntity | None:
    return session.scalar(
        select(TaxonomyEntity).where(
            TaxonomyEntity.taxonomy_version_id == version_id,
            TaxonomyEntity.code == code,
        )
    )


def _entity_count(session: Session, version_id: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(TaxonomyEntity)
            .where(TaxonomyEntity.taxonomy_version_id == version_id)
        )
        or 0
    )


def _ensure_name_available(session: Session, name: str) -> None:
    existing = session.scalar(select(Taxonomy.id).where(Taxonomy.name == name))
    if existing is not None:
        raise AppError("name_conflict", f"Taxonomy '{name}' already exists", 409)


def _version_is_pinned(session: Session, version_ids: list[str]) -> bool:
    domain_ref = session.scalar(
        select(func.count())
        .select_from(DomainDimension)
        .where(DomainDimension.taxonomy_version_id.in_(version_ids))
    )
    instance_ref = session.scalar(
        select(func.count())
        .select_from(DomainInstanceDimension)
        .where(DomainInstanceDimension.taxonomy_version_id.in_(version_ids))
    )
    return bool(domain_ref or instance_ref)


def _ensure_classifications_allowed(
    version: TaxonomyVersion, classifications: list[str], code: str
) -> None:
    allowed = set(version.allowed_classifications or [])
    unknown = [value for value in classifications if value not in allowed]
    if unknown:
        raise AppError(
            "classification_not_allowed",
            f"Classifications {unknown} are not allowed on this taxonomy",
            400,
            {"code": code, "classifications": unknown},
        )


def _ensure_classifications_cover_entities(
    session: Session, version: TaxonomyVersion, allowed: list[str]
) -> None:
    allowed_set = set(allowed)
    in_use: dict[str, list[str]] = defaultdict(list)
    for entity in _entities(session, version.id):
        for value in entity.classifications or []:
            if value not in allowed_set:
                in_use[value].append(entity.code)
    if in_use:
        raise AppError(
            "classification_in_use",
            "Cannot remove classifications that entities still use",
            409,
            {"inUse": {key: sorted(codes) for key, codes in in_use.items()}},
        )


def _resolve_parent_for_create(
    taxonomy: Taxonomy,
    entities: list[TaxonomyEntity],
    by_code: dict[str, TaxonomyEntity],
    parent_code: str | None,
) -> TaxonomyEntity | None:
    if not taxonomy.is_hierarchical:
        if parent_code is not None:
            raise AppError(
                "hierarchy_error",
                "A flat taxonomy cannot have parent links",
                400,
            )
        return None
    if parent_code is None:
        if entities:
            raise AppError(
                "hierarchy_error",
                "A hierarchical taxonomy has one root. New entities need a parentCode.",
                400,
            )
        return None
    if not entities:
        raise AppError(
            "hierarchy_error",
            "Create the root entity before adding children",
            400,
        )
    parent = by_code.get(parent_code)
    if parent is None:
        raise AppError("not_found", f"Parent entity '{parent_code}' not found", 404)
    return parent


def _reparent(
    taxonomy: Taxonomy,
    entities: list[TaxonomyEntity],
    entity: TaxonomyEntity,
    parent_code: str | None,
) -> None:
    if not taxonomy.is_hierarchical:
        raise AppError("hierarchy_error", "A flat taxonomy cannot have parent links", 400)
    if parent_code is None:
        raise AppError(
            "hierarchy_error",
            "The root cannot be replaced by clearing a parent. A hierarchy has one root.",
            400,
        )
    by_id = {item.id: item for item in entities}
    by_code = {item.code: item for item in entities}
    if entity.parent_id is None:
        raise AppError("hierarchy_error", "The root entity cannot be given a parent", 400)
    parent = by_code.get(parent_code)
    if parent is None:
        raise AppError("not_found", f"Parent entity '{parent_code}' not found", 404)
    if parent.id == entity.id:
        raise AppError("hierarchy_error", "An entity cannot be its own parent", 400)
    current: TaxonomyEntity | None = parent
    seen: set[str] = set()
    while current is not None:
        if current.id == entity.id:
            raise AppError("hierarchy_error", "That parent would create a cycle", 400)
        if current.id in seen:
            raise AppError("data_integrity", "Taxonomy entity hierarchy contains a cycle", 500)
        seen.add(current.id)
        if current.parent_id is None:
            break
        current = by_id.get(current.parent_id)
    entity.parent_id = parent.id


def _version_summary(session: Session, version: TaxonomyVersion) -> VersionSummary:
    return VersionSummary(
        version=version.version,
        status=version.status,
        allowed_classifications=list(version.allowed_classifications or []),
        published_at=to_iso(version.published_at) if version.published_at else None,
        entity_count=_entity_count(session, version.id),
        created_at=to_iso(version.created_at),
        updated_at=to_iso(version.updated_at),
    )


def _taxonomy_response(session: Session, taxonomy: Taxonomy) -> TaxonomyResponse:
    versions = _versions(session, taxonomy.id)
    if not versions:
        raise AppError("data_integrity", "Taxonomy has no versions", 500)
    latest = versions[-1]
    published = [version.version for version in versions if version.status == PUBLISHED]
    return TaxonomyResponse(
        id=taxonomy.id,
        name=taxonomy.name,
        description=taxonomy.description,
        is_hierarchical=taxonomy.is_hierarchical,
        created_at=to_iso(taxonomy.created_at),
        updated_at=to_iso(taxonomy.updated_at),
        latest_version=_version_summary(session, latest),
        latest_published_version=published[-1] if published else None,
    )


def _entity_responses(
    taxonomy: Taxonomy, version: TaxonomyVersion, entities: list[TaxonomyEntity]
) -> list[TaxonomyEntityResponse]:
    by_id = {entity.id: entity for entity in entities}
    responses: list[TaxonomyEntityResponse] = []
    for entity in entities:
        responses.append(_build_entity_response(taxonomy, version, entity, by_id))
    if taxonomy.is_hierarchical:
        return _preorder(responses)
    return sorted(responses, key=lambda item: item.code)


def _one_entity_response(
    taxonomy: Taxonomy,
    version: TaxonomyVersion,
    entities: list[TaxonomyEntity],
    entity: TaxonomyEntity,
) -> TaxonomyEntityResponse:
    by_id = {item.id: item for item in entities}
    return _build_entity_response(taxonomy, version, entity, by_id)


def _build_entity_response(
    taxonomy: Taxonomy,
    version: TaxonomyVersion,
    entity: TaxonomyEntity,
    by_id: dict[str, TaxonomyEntity],
) -> TaxonomyEntityResponse:
    try:
        effective = effective_classifications(entity.id, by_id)
    except CycleError as exc:
        raise AppError("data_integrity", "Taxonomy entity hierarchy contains a cycle", 500) from exc
    parent_code = None
    if entity.parent_id is not None:
        parent = by_id.get(entity.parent_id)
        parent_code = parent.code if parent is not None else None
    return TaxonomyEntityResponse(
        id=entity.id,
        taxonomy_id=taxonomy.id,
        version=version.version,
        code=entity.code,
        name=entity.name,
        parent_code=parent_code,
        depth=_depth(entity, by_id),
        classifications=list(entity.classifications or []),
        effective_classifications=effective,
        is_base=not effective,
        created_at=to_iso(entity.created_at),
        updated_at=to_iso(entity.updated_at),
    )


def _depth(entity: TaxonomyEntity, by_id: dict[str, TaxonomyEntity]) -> int:
    depth = 0
    current = entity
    seen: set[str] = set()
    while current.parent_id is not None:
        if current.id in seen:
            break
        seen.add(current.id)
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        current = parent
        depth += 1
    return depth


def _preorder(entities: list[TaxonomyEntityResponse]) -> list[TaxonomyEntityResponse]:
    by_parent: dict[str | None, list[TaxonomyEntityResponse]] = defaultdict(list)
    for entity in entities:
        by_parent[entity.parent_code].append(entity)
    for group in by_parent.values():
        group.sort(key=lambda item: item.code)
    ordered: list[TaxonomyEntityResponse] = []

    def walk(node: TaxonomyEntityResponse) -> None:
        ordered.append(node)
        for child in by_parent.get(node.code, []):
            walk(child)

    for root in by_parent.get(None, []):
        walk(root)
    if len(ordered) != len(entities):
        # A broken link should still be visible rather than dropped.
        seen = {item.code for item in ordered}
        ordered.extend(sorted((item for item in entities if item.code not in seen), key=lambda item: item.code))
    return ordered


def entities_for_version(session: Session, version_id: str) -> list[TaxonomyEntity]:
    return _entities(session, version_id)


def render_entities(
    taxonomy: Taxonomy, version: TaxonomyVersion, entities: list[TaxonomyEntity]
) -> list[TaxonomyEntityResponse]:
    return _entity_responses(taxonomy, version, entities)


def _filter_by_classification(
    version: TaxonomyVersion, items: list[TaxonomyEntityResponse], classification: str
) -> list[TaxonomyEntityResponse]:
    if classification.lower() == "base":
        return [item for item in items if item.is_base]
    allowed = set(version.allowed_classifications or [])
    if classification not in allowed:
        raise AppError(
            "classification_not_allowed",
            f"Classification '{classification}' is not configured on this taxonomy version",
            400,
        )
    return [item for item in items if classification in item.effective_classifications]
