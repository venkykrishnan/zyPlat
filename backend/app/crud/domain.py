from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from ..core.exceptions import ConflictError, NotFoundError, ValidationError
from ..models.domain import (
    DomainDefinition,
    DomainDimension,
    DomainKind,
    DomainMetric,
)
from ..schemas.domain import (
    DomainDefinitionCreate,
    DomainDefinitionUpdate,
    DomainDimensionCreate,
    DomainDimensionUpdate,
    DomainMetricCreate,
)


def _definition_query(db: Session):
    return db.query(DomainDefinition).options(
        selectinload(DomainDefinition.dimensions),
        selectinload(DomainDefinition.metrics),
    )


def get_domain_definition(db: Session, domain_id: UUID) -> DomainDefinition | None:
    return cast(
        DomainDefinition | None,
        _definition_query(db).filter(DomainDefinition.id == domain_id).first(),
    )


def get_domain_definition_by_logical_id(
    db: Session,
    domain_id: str,
    *,
    owner_company_id: UUID | None = None,
) -> DomainDefinition | None:
    query = _definition_query(db).filter(DomainDefinition.domain_id == domain_id)
    if owner_company_id is None:
        query = query.filter(DomainDefinition.owner_company_id.is_(None))
    else:
        query = query.filter(DomainDefinition.owner_company_id == owner_company_id)
    return cast(DomainDefinition | None, query.first())


def get_domain_definitions(db: Session, skip: int = 0, limit: int = 100) -> list[DomainDefinition]:
    return cast(list[DomainDefinition], _definition_query(db).offset(skip).limit(limit).all())


def _validate_time_series_rules(
    kind: DomainKind, dimensions: list[DomainDimensionCreate] | list[DomainDimension]
) -> None:
    """Enforce time-series field rules once dimensions are present.

    Empty dimension lists are allowed at create time so fields can be added later; import and
    application binding require exactly one time-series dimension on TIME_SERIES domains.
    """
    time_series = [d for d in dimensions if getattr(d, "is_time_series", False)]
    if kind == DomainKind.SCALAR and time_series:
        raise ValidationError("SCALAR domains cannot have a time-series dimension.")
    if not dimensions:
        return
    if kind == DomainKind.TIME_SERIES and len(time_series) != 1:
        raise ValidationError(
            f"TIME_SERIES domains require exactly one time-series dimension; found {len(time_series)}."
        )


def create_domain_definition(db: Session, domain: DomainDefinitionCreate) -> DomainDefinition:
    _validate_time_series_rules(domain.kind, domain.dimensions)
    payload = domain.model_dump(exclude={"dimensions", "metrics"})
    db_domain = DomainDefinition(**payload)
    db_domain.dimensions = [DomainDimension(**d.model_dump()) for d in domain.dimensions]
    db_domain.metrics = [DomainMetric(**m.model_dump()) for m in domain.metrics]
    db.add(db_domain)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001 - map unique violations
        db.rollback()
        raise ConflictError(f"Domain '{domain.domain_id}' already exists in this scope.") from exc
    loaded = get_domain_definition(db, cast(UUID, db_domain.id))
    if loaded is None:
        raise NotFoundError(f"Domain '{domain.domain_id}' was not found after create.")
    return loaded


def update_domain_definition(
    db: Session, domain_id: UUID, domain_update: DomainDefinitionUpdate
) -> DomainDefinition | None:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        return None

    update_data = domain_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_domain, field, value)

    db.commit()
    return get_domain_definition(db, domain_id)


def delete_domain_definition(db: Session, domain_id: UUID) -> bool:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        return False

    db.delete(db_domain)
    db.commit()
    return True


def add_domain_dimension(
    db: Session, domain_id: UUID, dimension: DomainDimensionCreate
) -> DomainDimension:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        raise NotFoundError(f"Domain definition {domain_id} not found.")

    proposed = list(db_domain.dimensions) + [
        DomainDimension(**dimension.model_dump(), domain_definition_id=domain_id)
    ]
    _validate_time_series_rules(db_domain.kind, proposed)

    db_dimension = DomainDimension(**dimension.model_dump(), domain_definition_id=domain_id)
    db.add(db_dimension)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ConflictError(
            f"Dimension '{dimension.name}' conflicts with an existing dimension on this domain."
        ) from exc
    db.refresh(db_dimension)
    return db_dimension


def update_domain_dimension(
    db: Session, domain_id: UUID, dimension_name: str, update: DomainDimensionUpdate
) -> DomainDimension:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        raise NotFoundError(f"Domain definition {domain_id} not found.")

    db_dimension = next((d for d in db_domain.dimensions if d.name == dimension_name), None)
    if db_dimension is None:
        raise NotFoundError(f"Dimension '{dimension_name}' not found on domain {domain_id}.")

    data = update.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_dimension, field, value)

    # Re-validate after mutation using ORM objects.
    _validate_time_series_rules(db_domain.kind, list(db_domain.dimensions))
    if db_dimension.is_time_series and db_dimension.period_type is None:
        raise ValidationError("period_type is required when is_time_series is true")
    if db_dimension.is_time_series and db_dimension.data_type.value != "DATETIME":
        raise ValidationError("time-series dimensions must have data_type DATETIME")
    if not db_dimension.is_time_series and db_dimension.period_type is not None:
        raise ValidationError("period_type is only allowed when is_time_series is true")

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ConflictError(
            f"Updated dimension '{dimension_name}' violates a domain constraint."
        ) from exc
    db.refresh(db_dimension)
    return cast(DomainDimension, db_dimension)


def list_domain_dimensions(db: Session, domain_id: UUID) -> list[DomainDimension]:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        raise NotFoundError(f"Domain definition {domain_id} not found.")
    return list(db_domain.dimensions)


def add_domain_metric(db: Session, domain_id: UUID, metric: DomainMetricCreate) -> DomainMetric:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        raise NotFoundError(f"Domain definition {domain_id} not found.")
    db_metric = DomainMetric(**metric.model_dump(), domain_definition_id=domain_id)
    db.add(db_metric)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ConflictError(
            f"Metric '{metric.name}' conflicts with an existing metric on this domain."
        ) from exc
    db.refresh(db_metric)
    return db_metric


def list_domain_metrics(db: Session, domain_id: UUID) -> list[DomainMetric]:
    db_domain = get_domain_definition(db, domain_id)
    if not db_domain:
        raise NotFoundError(f"Domain definition {domain_id} not found.")
    return list(db_domain.metrics)
