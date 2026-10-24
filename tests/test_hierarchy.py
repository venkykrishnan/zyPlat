from types import SimpleNamespace

import pytest

from zyplat.hierarchy import HierarchyError, validate_entities


def node(identifier: str, parent_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=identifier, parent_id=parent_id, classifications=[], code=identifier)


def test_flat_taxonomy_rejects_parents_and_accepts_a_set():
    validate_entities([node("a", None), node("b", None)], hierarchical=False)
    with pytest.raises(HierarchyError, match="flat"):
        validate_entities([node("a", None), node("b", "a")], hierarchical=False)


def test_hierarchical_taxonomy_requires_one_connected_root():
    with pytest.raises(HierarchyError, match="root"):
        validate_entities([], hierarchical=True)
    with pytest.raises(HierarchyError, match="exactly one root"):
        validate_entities([node("a", None), node("b", None)], hierarchical=True)
    with pytest.raises(HierarchyError, match="missing parent"):
        validate_entities([node("a", None), node("b", "missing")], hierarchical=True)


def test_hierarchical_cycle_is_rejected_and_a_tree_is_accepted():
    with pytest.raises(HierarchyError, match="cycle"):
        validate_entities(
            [node("root", None), node("b", "c"), node("c", "b")],
            hierarchical=True,
        )
    validate_entities(
        [node("root", None), node("b", "root"), node("c", "b")],
        hierarchical=True,
    )
