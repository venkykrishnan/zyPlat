from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.exceptions import ConflictError, NotFoundError, ValidationError
from ..models.company import Company, CompanySnapshot, CompanySnapshotHead, PeriodGranularity
from ..schemas.company import CompanyCreate, CompanyUpdate
from ..schemas.company_snapshot import CompanySnapshotCreate


def get_company(db: Session, company_id: UUID) -> Company | None:
    return db.query(Company).filter(Company.id == company_id).first()


def get_company_by_company_id(db: Session, company_id: str) -> Company | None:
    return db.query(Company).filter(Company.company_id == company_id).first()


def get_companies(db: Session, skip: int = 0, limit: int = 100) -> list[Company]:
    return db.query(Company).offset(skip).limit(limit).all()


def _to_model_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Rename the public ``metadata`` field to the ORM attribute ``metadata_``.

    Passing ``metadata`` straight to the model would not fail: ``Company.metadata`` exists
    (it is the table registry), so SQLAlchemy would set a plain Python attribute and the value
    would never be saved.
    """
    fields = dict(data)
    if "metadata" in fields:
        fields["metadata_"] = fields.pop("metadata")
    return fields


def create_company(db: Session, company: CompanyCreate) -> Company:
    db_company = Company(**_to_model_fields(company.model_dump()))
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


def update_company(db: Session, company_id: UUID, company_update: CompanyUpdate) -> Company | None:
    db_company = get_company(db, company_id)
    if not db_company:
        return None

    update_data = _to_model_fields(company_update.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(db_company, field, value)

    db.commit()
    db.refresh(db_company)
    return db_company


def delete_company(db: Session, company_id: UUID) -> bool:
    db_company = get_company(db, company_id)
    if not db_company:
        return False

    db.delete(db_company)
    db.commit()
    return True


def _require_company(db: Session, company_id: UUID) -> Company:
    company = get_company(db, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")
    return company


def create_company_snapshot(
    db: Session, company_id: UUID, payload: CompanySnapshotCreate
) -> CompanySnapshot:
    _require_company(db, company_id)
    next_ord = payload.ord
    if next_ord is None:
        current_max = (
            db.query(func.max(CompanySnapshot.ord))
            .filter(
                CompanySnapshot.company_id == company_id,
                CompanySnapshot.period_type == payload.period_type,
                CompanySnapshot.period_value == payload.period_value,
            )
            .scalar()
        )
        next_ord = 1 if current_max is None else int(current_max) + 1

    snapshot = CompanySnapshot(
        company_id=company_id,
        period_type=payload.period_type,
        period_value=payload.period_value,
        ord=next_ord,
    )
    db.add(snapshot)
    try:
        db.flush()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ValidationError(
            f"Invalid company snapshot period {payload.period_type.value}={payload.period_value} "
            f"or duplicate ord={next_ord}."
        ) from exc

    head = (
        db.query(CompanySnapshotHead)
        .filter(
            CompanySnapshotHead.company_id == company_id,
            CompanySnapshotHead.period_type == payload.period_type,
            CompanySnapshotHead.period_value == payload.period_value,
        )
        .one_or_none()
    )
    if head is None:
        db.add(
            CompanySnapshotHead(
                company_id=company_id,
                period_type=payload.period_type,
                period_value=payload.period_value,
                snapshot_id=snapshot.id,
            )
        )
    else:
        # Keep the head pointing at the highest-ord snapshot for this period.
        current = db.get(CompanySnapshot, head.snapshot_id)
        if current is None or snapshot.ord >= current.ord:
            head.snapshot_id = snapshot.id

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ConflictError("Could not create company snapshot.") from exc
    db.refresh(snapshot)
    return snapshot


def list_company_snapshots(
    db: Session,
    company_id: UUID,
    *,
    period_type: PeriodGranularity | None = None,
    period_value: str | None = None,
) -> list[CompanySnapshot]:
    _require_company(db, company_id)
    query = db.query(CompanySnapshot).filter(CompanySnapshot.company_id == company_id)
    if period_type is not None:
        query = query.filter(CompanySnapshot.period_type == period_type)
    if period_value is not None:
        query = query.filter(CompanySnapshot.period_value == period_value)
    return query.order_by(
        CompanySnapshot.period_type, CompanySnapshot.period_value, CompanySnapshot.ord.desc()
    ).all()


def get_company_snapshot(db: Session, company_id: UUID, snapshot_id: UUID) -> CompanySnapshot:
    _require_company(db, company_id)
    snapshot = (
        db.query(CompanySnapshot)
        .filter(CompanySnapshot.id == snapshot_id, CompanySnapshot.company_id == company_id)
        .one_or_none()
    )
    if snapshot is None:
        raise NotFoundError(f"Company snapshot {snapshot_id} not found.")
    return snapshot


def get_default_company_snapshot(
    db: Session,
    company_id: UUID,
    period_type: PeriodGranularity,
    period_value: str,
) -> CompanySnapshot:
    _require_company(db, company_id)
    snapshot = (
        db.query(CompanySnapshot)
        .filter(
            CompanySnapshot.company_id == company_id,
            CompanySnapshot.period_type == period_type,
            CompanySnapshot.period_value == period_value,
        )
        .order_by(CompanySnapshot.ord.desc())
        .first()
    )
    if snapshot is None:
        raise NotFoundError(
            f"No company snapshot for {period_type.value}={period_value} on company {company_id}."
        )
    return snapshot


def delete_company_snapshot(db: Session, company_id: UUID, snapshot_id: UUID) -> None:
    snapshot = get_company_snapshot(db, company_id, snapshot_id)
    head = (
        db.query(CompanySnapshotHead)
        .filter(CompanySnapshotHead.snapshot_id == snapshot_id)
        .one_or_none()
    )
    db.delete(snapshot)
    db.flush()
    if head is not None:
        replacement = (
            db.query(CompanySnapshot)
            .filter(
                CompanySnapshot.company_id == company_id,
                CompanySnapshot.period_type == snapshot.period_type,
                CompanySnapshot.period_value == snapshot.period_value,
            )
            .order_by(CompanySnapshot.ord.desc())
            .first()
        )
        if replacement is None:
            db.delete(head)
        else:
            head.snapshot_id = replacement.id
    db.commit()
