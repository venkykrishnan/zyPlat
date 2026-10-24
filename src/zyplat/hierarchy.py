"""Tree rules for hierarchical taxonomies and the flat-taxonomy parent ban."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any


class HierarchyError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_entities(entities: Sequence[Any], *, hierarchical: bool) -> None:
    if not hierarchical:
        linked = [entity.code for entity in entities if entity.parent_id is not None]
        if linked:
            raise HierarchyError("A flat taxonomy cannot have parent links")
        return

    if not entities:
        raise HierarchyError(
            "A hierarchical taxonomy needs a root entity before it can be published"
        )

    by_id = {entity.id: entity for entity in entities}
    children: dict[str, list[Any]] = defaultdict(list)
    for entity in entities:
        if entity.parent_id is None:
            continue
        if entity.parent_id not in by_id:
            raise HierarchyError(f"Entity '{entity.code}' references a missing parent")
        children[entity.parent_id].append(entity)

    color = {entity.id: 0 for entity in entities}

    def walk(entity_id: str) -> None:
        color[entity_id] = 1
        for child in children.get(entity_id, []):
            if color[child.id] == 1:
                raise HierarchyError("Taxonomy entities contain a cycle")
            if color[child.id] == 0:
                walk(child.id)
        color[entity_id] = 2

    for entity in entities:
        if color[entity.id] == 0:
            walk(entity.id)

    roots = [entity for entity in entities if entity.parent_id is None]
    if len(roots) != 1:
        raise HierarchyError(
            f"A hierarchical taxonomy needs exactly one root entity (found {len(roots)})"
        )

    seen: set[str] = set()
    stack = [roots[0].id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(child.id for child in children.get(current, []))
    if len(seen) != len(entities):
        raise HierarchyError("Every entity must be connected to the root")
