"""Validation helpers for application expected-schema and bind containment."""

from __future__ import annotations

import calendar
import hashlib
import json
from datetime import date

from ...core.exceptions import ValidationError
from ...models.company import CompanySnapshot, PeriodGranularity
from ...models.domain import DomainDefinition, DomainKind
from .schemas import ExpectedDomainSchema


def schema_hash_for_expected(expected: ExpectedDomainSchema) -> str:
    payload = expected.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_expected_against_domain(
    domain: DomainDefinition, expected: ExpectedDomainSchema
) -> str:
    """Ensure ``expected`` is a required subset of ``domain``; return schema hash."""
    if domain.kind != expected.kind:
        raise ValidationError(
            f"Domain '{domain.domain_id}' kind is {domain.kind.value}, expected {expected.kind.value}."
        )

    dims_by_name = {d.name: d for d in domain.dimensions}
    metrics_by_name = {m.name: m for m in domain.metrics}

    if expected.kind == DomainKind.TIME_SERIES:
        time_series = [d for d in domain.dimensions if d.is_time_series]
        if len(time_series) != 1:
            raise ValidationError(
                f"Domain '{domain.domain_id}' must have exactly one time-series dimension."
            )
        live = time_series[0]
        if expected.time_series_dimension and expected.time_series_dimension != live.name:
            raise ValidationError(
                f"Expected time-series dimension '{expected.time_series_dimension}', "
                f"domain has '{live.name}'."
            )
        if expected.period_type and expected.period_type != live.period_type:
            raise ValidationError(
                f"Expected period_type {expected.period_type.value}, "
                f"domain has {live.period_type.value if live.period_type else None}."
            )

    for dim in expected.dimensions:
        live = dims_by_name.get(dim.name)
        if live is None:
            raise ValidationError(
                f"Domain '{domain.domain_id}' is missing required dimension '{dim.name}'."
            )
        if live.data_type != dim.data_type:
            raise ValidationError(
                f"Dimension '{dim.name}' has type {live.data_type.value}, "
                f"expected {dim.data_type.value}."
            )
        if dim.taxonomy_id is not None and live.taxonomy_id != dim.taxonomy_id:
            raise ValidationError(
                f"Dimension '{dim.name}' taxonomy_id is '{live.taxonomy_id}', "
                f"expected '{dim.taxonomy_id}'."
            )
        if dim.taxonomy_version is not None and live.taxonomy_version != dim.taxonomy_version:
            raise ValidationError(
                f"Dimension '{dim.name}' taxonomy_version is '{live.taxonomy_version}', "
                f"expected '{dim.taxonomy_version}'."
            )

    for metric in expected.metrics:
        live = metrics_by_name.get(metric.name)
        if live is None:
            raise ValidationError(
                f"Domain '{domain.domain_id}' is missing required metric '{metric.name}'."
            )
        if live.data_type != metric.data_type:
            raise ValidationError(
                f"Metric '{metric.name}' has type {live.data_type.value}, "
                f"expected {metric.data_type.value}."
            )

    return schema_hash_for_expected(expected)


def period_contained(
    inner_type: PeriodGranularity,
    inner_value: str,
    outer_type: PeriodGranularity,
    outer_value: str,
) -> bool:
    """Return True when an independent snapshot period falls inside a company snapshot period."""
    if _rank(inner_type) < _rank(outer_type):
        return False
    inner_start, inner_end = _period_bounds(inner_type, inner_value)
    outer_start, outer_end = _period_bounds(outer_type, outer_value)
    return inner_start >= outer_start and inner_end <= outer_end


def _rank(period_type: PeriodGranularity) -> int:
    return {
        PeriodGranularity.YEAR: 1,
        PeriodGranularity.QUARTER: 2,
        PeriodGranularity.MONTH: 3,
        PeriodGranularity.DATE: 4,
    }[period_type]


def _period_bounds(period_type: PeriodGranularity, value: str) -> tuple[date, date]:
    if period_type is PeriodGranularity.YEAR:
        year = int(value)
        return date(year, 1, 1), date(year, 12, 31)
    if period_type is PeriodGranularity.QUARTER:
        year = int(value[:4])
        quarter = int(value[-1])
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        end_day = 30 if end_month in {4, 6, 9, 11} else 31
        if end_month == 2:
            end_day = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
        return date(year, start_month, 1), date(year, end_month, end_day)
    if period_type is PeriodGranularity.MONTH:
        year = int(value[:4])
        month = int(value[5:7])
        end_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, end_day)
    year = int(value[:4])
    month = int(value[5:7])
    day = int(value[8:10])
    day_value = date(year, month, day)
    return day_value, day_value


def company_snapshot_period(snapshot: CompanySnapshot) -> tuple[PeriodGranularity, str]:
    return snapshot.period_type, str(snapshot.period_value)
