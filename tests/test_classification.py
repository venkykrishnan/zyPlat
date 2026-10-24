from types import SimpleNamespace

import pytest

from zyplat.classification import CycleError, effective_classifications, is_admissible


def node(identifier: str, parent_id: str | None, classifications: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        id=identifier, parent_id=parent_id, classifications=classifications, code=identifier
    )


def test_effective_classifications_are_ancestor_first_and_not_duplicated():
    root = node("root", None, ["CIQ"])
    child = node("child", "root", ["CIQ", "EDGAR"])
    grandchild = node("grandchild", "child", ["SOX"])
    by_id = {item.id: item for item in (root, child, grandchild)}

    assert effective_classifications("root", by_id) == ["CIQ"]
    assert effective_classifications("child", by_id) == ["CIQ", "EDGAR"]
    assert effective_classifications("grandchild", by_id) == ["CIQ", "EDGAR", "SOX"]


def test_child_with_no_direct_classifications_still_inherits():
    root = node("root", None, [])
    revenue = node("revenue", "root", ["CIQ", "EDGAR"])
    product = node("product", "revenue", [])
    by_id = {item.id: item for item in (root, revenue, product)}

    assert effective_classifications("product", by_id) == ["CIQ", "EDGAR"]


def test_cycle_in_parent_chain_is_rejected():
    left = node("left", "right", ["CIQ"])
    right = node("right", "left", ["EDGAR"])
    by_id = {item.id: item for item in (left, right)}

    with pytest.raises(CycleError):
        effective_classifications("left", by_id)


def test_base_entity_is_always_admissible_and_tags_use_intersection():
    assert is_admissible([], []) is True
    assert is_admissible([], ["CIQ"]) is True
    assert is_admissible(["EDGAR"], []) is False
    assert is_admissible(["EDGAR"], ["CIQ"]) is False
    assert is_admissible(["CIQ", "EDGAR"], ["CIQ"]) is True
    assert is_admissible(["CIQ"], ["CIQ", "EDGAR"]) is True
