from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..models.company import PeriodGranularity


class CompanySnapshotCreate(BaseModel):
    period_type: PeriodGranularity
    period_value: str = Field(..., min_length=1)
    # Optional override; normally the service assigns next ord.
    ord: int | None = Field(default=None, gt=0)


class CompanySnapshotResponse(BaseModel):
    id: UUID
    company_id: UUID
    period_type: PeriodGranularity
    period_value: str
    ord: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanySnapshotDefaultQuery(BaseModel):
    period_type: PeriodGranularity
    period_value: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def non_empty_period(self) -> CompanySnapshotDefaultQuery:
        if not self.period_value.strip():
            raise ValueError("period_value must not be blank")
        return self
