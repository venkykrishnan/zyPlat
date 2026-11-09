from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import company as crud
from ..models.company import PeriodGranularity
from ..schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from ..schemas.company_snapshot import CompanySnapshotCreate, CompanySnapshotResponse

router = APIRouter()


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    db_company = crud.get_company_by_company_id(db, company.company_id)
    if db_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with company_id '{company.company_id}' already exists",
        )
    return crud.create_company(db, company)


@router.get("/", response_model=list[CompanyResponse])
def list_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_companies(db, skip=skip, limit=limit)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    db_company = crud.get_company(db, company_id)
    if not db_company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return db_company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: UUID, company: CompanyUpdate, db: Session = Depends(get_db)):
    db_company = crud.update_company(db, company_id, company)
    if not db_company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return db_company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: UUID, db: Session = Depends(get_db)):
    if not crud.delete_company(db, company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")


@router.post(
    "/{company_id}/snapshots",
    response_model=CompanySnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_snapshot(
    company_id: UUID, payload: CompanySnapshotCreate, db: Session = Depends(get_db)
):
    return crud.create_company_snapshot(db, company_id, payload)


@router.get("/{company_id}/snapshots", response_model=list[CompanySnapshotResponse])
def list_company_snapshots(
    company_id: UUID,
    period_type: PeriodGranularity | None = None,
    period_value: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_company_snapshots(
        db, company_id, period_type=period_type, period_value=period_value
    )


@router.get("/{company_id}/snapshots/default", response_model=CompanySnapshotResponse)
def get_default_company_snapshot(
    company_id: UUID,
    period_type: PeriodGranularity,
    period_value: str,
    db: Session = Depends(get_db),
):
    return crud.get_default_company_snapshot(db, company_id, period_type, period_value)


@router.get("/{company_id}/snapshots/{snapshot_id}", response_model=CompanySnapshotResponse)
def get_company_snapshot(company_id: UUID, snapshot_id: UUID, db: Session = Depends(get_db)):
    return crud.get_company_snapshot(db, company_id, snapshot_id)


@router.delete("/{company_id}/snapshots/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_snapshot(company_id: UUID, snapshot_id: UUID, db: Session = Depends(get_db)):
    crud.delete_company_snapshot(db, company_id, snapshot_id)
