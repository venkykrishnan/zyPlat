"""Effective classifications and instance admissibility.

Direct classifications are stored on the entity that was tagged. Descendants
inherit them by walking to the root. Inherited values are not copied onto
children, and a child cannot drop a classification it inherited.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class CycleError(Exception):
    """The parent chain visits the same entity twice."""


def effective_classifications(entity_id: str, by_id: Mapping[str, Any]) -> list[str]:
    """Union of direct classifications from the root down to ``entity_id``.

    Order is ancestor-first, then the entity's own values, with duplicates removed.
    """

    chain: list[Any] = []
    seen: set[str] = set()
    current = by_id.get(entity_id)
    if current is None:
        raise KeyError(entity_id)
    while current is not None:
        if current.id in seen:
            raise CycleError(current.id)
        seen.add(current.id)
        chain.append(current)
        parent_id = current.parent_id
        if parent_id is None:
            break
        parent = by_id.get(parent_id)
        if parent is None:
            break
        current = parent

    result: list[str] = []
    for node in reversed(chain):
        for value in node.classifications or []:
            if value not in result:
                result.append(value)
    return result


def is_admissible(effective: list[str], selected: list[str]) -> bool:
    """A base entity is always admissible. Otherwise at least one tag must be selected."""

    if not effective:
        return True
    selected_set = set(selected)
    return any(value in selected_set for value in effective)
