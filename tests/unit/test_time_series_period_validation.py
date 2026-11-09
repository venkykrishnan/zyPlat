"""Unit tests for time-series period alignment at import time."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from backend.app.core.exceptions import ValidationError
from backend.app.models.company import PeriodGranularity
from backend.app.models.domain import DomainDimensionDataType, DomainMetricDataType
from backend.app.storage.instance_data import ColumnKind, ColumnSpec, FrameSpec, validate_frame


@pytest.fixture
def month_spec() -> FrameSpec:
    return FrameSpec(
        "GL",
        (
            ColumnSpec(
                "period",
                ColumnKind.DIMENSION,
                DomainDimensionDataType.DATETIME,
                True,
                is_time_series=True,
                period_type=PeriodGranularity.MONTH,
            ),
            ColumnSpec("amount", ColumnKind.METRIC, DomainMetricDataType.NUMBER, True),
        ),
    )


def test_aligned_month_succeeds(month_spec):
    """Month-start UTC midnight values are accepted."""
    frame = pd.DataFrame(
        {
            "period": [datetime(2026, 7, 1, tzinfo=UTC)],
            "amount": [1.0],
        }
    )

    table = validate_frame(frame, month_spec)

    assert table.num_rows == 1


def test_mid_month_value_fails(month_spec):
    """A non-period-start DATETIME on a MONTH field is rejected."""
    frame = pd.DataFrame(
        {
            "period": [datetime(2026, 7, 15, tzinfo=UTC)],
            "amount": [1.0],
        }
    )

    with pytest.raises(ValidationError, match="not aligned to period start"):
        validate_frame(frame, month_spec)
