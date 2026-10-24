def _codes(response) -> list[str]:
    return [item["code"] for item in response.json()["items"]]


def test_create_lists_camel_case_and_rejects_bad_names(client):
    created = client.post(
        "/api/v1/taxonomies",
        json={
            "name": "accountType",
            "description": "Account types",
            "isHierarchical": True,
            "allowedClassifications": ["CIQ", "EDGAR"],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "accountType"
    assert body["isHierarchical"] is True
    assert body["latestVersion"]["version"] == 1
    assert body["latestVersion"]["status"] == "draft"
    assert body["latestVersion"]["allowedClassifications"] == ["CIQ", "EDGAR"]
    assert body["latestPublishedVersion"] is None
    assert "T" in body["createdAt"]

    duplicate = client.post(
        "/api/v1/taxonomies",
        json={"name": "accountType", "isHierarchical": False, "allowedClassifications": []},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "name_conflict"

    reserved = client.post(
        "/api/v1/taxonomies",
        json={"name": "bad", "isHierarchical": False, "allowedClassifications": ["base"]},
    )
    assert reserved.status_code == 422

    numeric = client.post(
        "/api/v1/taxonomies",
        json={"name": "1bad", "isHierarchical": False, "allowedClassifications": []},
    )
    assert numeric.status_code == 422

    listed = client.get("/api/v1/taxonomies")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_hierarchy_writes_inheritance_and_filters(client):
    created = client.post(
        "/api/v1/taxonomies",
        json={
            "name": "accountType",
            "isHierarchical": True,
            "allowedClassifications": ["CIQ", "EDGAR"],
        },
    )
    taxonomy_id = created.json()["id"]
    base = f"/api/v1/taxonomies/{taxonomy_id}"

    child_first = client.post(
        f"{base}/entities",
        json={"code": "revenue", "name": "Revenue", "parentCode": "accountType"},
    )
    assert child_first.status_code == 400
    assert child_first.json()["error"]["code"] == "hierarchy_error"

    root = client.post(f"{base}/entities", json={"code": "accountType", "name": "Account Type"})
    assert root.status_code == 201
    assert root.json()["isBase"] is True
    assert root.json()["effectiveClassifications"] == []
    assert root.json()["depth"] == 0

    second_root = client.post(f"{base}/entities", json={"code": "other", "name": "Other"})
    assert second_root.status_code == 400

    unknown = client.post(
        f"{base}/entities",
        json={
            "code": "revenue",
            "name": "Revenue",
            "parentCode": "accountType",
            "classifications": ["SOX"],
        },
    )
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "classification_not_allowed"

    revenue = client.post(
        f"{base}/entities",
        json={
            "code": "revenue",
            "name": "Revenue",
            "parentCode": "accountType",
            "classifications": ["CIQ", "EDGAR"],
        },
    )
    assert revenue.status_code == 201
    product = client.post(
        f"{base}/entities",
        json={"code": "productRevenue", "name": "Product Revenue", "parentCode": "revenue"},
    )
    assert product.status_code == 201
    assert product.json()["classifications"] == []
    assert product.json()["effectiveClassifications"] == ["CIQ", "EDGAR"]
    assert product.json()["isBase"] is False
    assert product.json()["parentCode"] == "revenue"
    assert product.json()["depth"] == 2

    client.post(
        f"{base}/entities",
        json={"code": "expense", "name": "Expense", "parentCode": "accountType"},
    )
    client.post(
        f"{base}/entities",
        json={
            "code": "edgarOnly",
            "name": "EDGAR only",
            "parentCode": "accountType",
            "classifications": ["EDGAR"],
        },
    )

    duplicate = client.post(
        f"{base}/entities",
        json={"code": "expense", "name": "Again", "parentCode": "accountType"},
    )
    assert duplicate.status_code == 409

    listed = client.get(f"{base}/entities")
    assert _codes(listed) == ["accountType", "edgarOnly", "expense", "revenue", "productRevenue"]

    ciq = client.get(f"{base}/entities", params={"classification": "CIQ"})
    assert _codes(ciq) == ["revenue", "productRevenue"]
    base_only = client.get(f"{base}/entities", params={"classification": "base"})
    assert _codes(base_only) == ["accountType", "expense"]
    missing = client.get(f"{base}/entities", params={"classification": "SOX"})
    assert missing.status_code == 400

    # Inheritance is computed. Clearing the child's direct tags does not clear the parent's.
    cleared = client.patch(
        f"{base}/entities/productRevenue",
        json={"classifications": []},
    )
    assert cleared.json()["classifications"] == []
    assert cleared.json()["effectiveClassifications"] == ["CIQ", "EDGAR"]

    widened = client.patch(
        f"{base}/entities/revenue",
        json={"classifications": ["CIQ"]},
    )
    assert widened.status_code == 200
    product_after = client.get(f"{base}/entities/productRevenue")
    assert product_after.json()["effectiveClassifications"] == ["CIQ"]
    assert product_after.json()["classifications"] == []

    cycle = client.patch(f"{base}/entities/revenue", json={"parentCode": "productRevenue"})
    assert cycle.status_code == 400
    assert cycle.json()["error"]["code"] == "hierarchy_error"
    root_parent = client.patch(f"{base}/entities/accountType", json={"parentCode": "revenue"})
    assert root_parent.status_code == 400

    blocked = client.delete(f"{base}/entities/revenue")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "has_children"

    removed = client.patch(
        f"{base}/entities/revenue",
        json={"classifications": []},
    )
    assert removed.status_code == 200
    drop_ciq = client.patch(f"{base}", json={"allowedClassifications": ["EDGAR"]})
    assert drop_ciq.status_code == 200
    still_used = client.patch(
        f"{base}/entities/edgarOnly",
        json={"classifications": ["EDGAR"]},
    )
    assert still_used.status_code == 200
    drop_edgar = client.patch(f"{base}", json={"allowedClassifications": []})
    assert drop_edgar.status_code == 409
    assert drop_edgar.json()["error"]["code"] == "classification_in_use"


def test_flat_taxonomy_rejects_parents(client):
    created = client.post(
        "/api/v1/taxonomies",
        json={"name": "currency", "isHierarchical": False, "allowedClassifications": ["CIQ"]},
    )
    taxonomy_id = created.json()["id"]
    base = f"/api/v1/taxonomies/{taxonomy_id}"
    first = client.post(
        f"{base}/entities",
        json={"code": "usd", "name": "US Dollar", "classifications": ["CIQ"]},
    )
    assert first.status_code == 201
    assert first.json()["effectiveClassifications"] == ["CIQ"]
    second = client.post(f"{base}/entities", json={"code": "eur", "name": "Euro"})
    assert second.status_code == 201
    assert second.json()["isBase"] is True
    parented = client.post(
        f"{base}/entities",
        json={"code": "gbp", "name": "Pound", "parentCode": "usd"},
    )
    assert parented.status_code == 400
    published = client.post(f"{base}/publish")
    assert published.status_code == 200
    assert published.json()["latestPublishedVersion"] == 1


def test_publish_freezes_version_and_draft_is_a_clone(client):
    created = client.post(
        "/api/v1/taxonomies",
        json={
            "name": "accountType",
            "isHierarchical": True,
            "allowedClassifications": ["CIQ", "EDGAR"],
        },
    )
    taxonomy_id = created.json()["id"]
    base = f"/api/v1/taxonomies/{taxonomy_id}"
    empty = client.post(f"{base}/publish")
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "hierarchy_error"

    client.post(f"{base}/entities", json={"code": "accountType", "name": "Account Type"})
    client.post(
        f"{base}/entities",
        json={
            "code": "revenue",
            "name": "Revenue",
            "parentCode": "accountType",
            "classifications": ["CIQ", "EDGAR"],
        },
    )
    client.post(
        f"{base}/entities",
        json={"code": "productRevenue", "name": "Product Revenue", "parentCode": "revenue"},
    )
    published = client.post(f"{base}/publish")
    assert published.status_code == 200
    published_product_id = client.get(f"{base}/entities/productRevenue").json()["id"]

    edit = client.patch(f"{base}/entities/revenue", json={"classifications": []})
    assert edit.status_code == 409
    assert edit.json()["error"]["code"] == "draft_required"
    locked = client.patch(f"{base}", json={"allowedClassifications": ["CIQ"]})
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "draft_required"
    renamed = client.patch(f"{base}", json={"description": "Published, description still editable"})
    assert renamed.status_code == 200
    assert renamed.json()["description"] == "Published, description still editable"
    again = client.post(f"{base}/publish")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "no_draft"

    draft = client.post(f"{base}/draft")
    assert draft.status_code == 200
    assert draft.json()["latestVersion"]["version"] == 2
    assert draft.json()["latestVersion"]["status"] == "draft"
    assert draft.json()["latestPublishedVersion"] == 1
    second_draft = client.post(f"{base}/draft")
    assert second_draft.status_code == 409

    draft_product = client.get(f"{base}/entities/productRevenue")
    assert draft_product.json()["id"] != published_product_id
    assert draft_product.json()["effectiveClassifications"] == ["CIQ", "EDGAR"]
    assert draft_product.json()["classifications"] == []

    client.patch(f"{base}/entities/revenue", json={"classifications": []})
    assert client.get(f"{base}/entities/productRevenue").json()["effectiveClassifications"] == []
    frozen = client.get(f"{base}/entities/productRevenue", params={"version": 1})
    assert frozen.json()["effectiveClassifications"] == ["CIQ", "EDGAR"]
    assert frozen.json()["version"] == 1

    client.post(f"{base}/entities", json={"code": "other", "name": "Other", "parentCode": "accountType"})
    current = client.get(f"{base}/entities")
    assert current.json()["version"] == 2
    assert "other" in _codes(current)
    historical = client.get(f"{base}/entities", params={"version": 1})
    assert "other" not in _codes(historical)

    versions = client.get(f"{base}/versions")
    assert [item["version"] for item in versions.json()["items"]] == [1, 2]
    assert versions.json()["items"][0]["status"] == "published"
    assert client.get(f"{base}/versions/1").json()["entityCount"] == 3
    assert client.get(f"{base}/versions/9").status_code == 404


def test_rename_description_and_delete(client):
    created = client.post(
        "/api/v1/taxonomies",
        json={"name": "region", "description": "old", "isHierarchical": False},
    )
    taxonomy_id = created.json()["id"]
    renamed = client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}",
        json={"name": "regionCode", "description": "Regions"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "regionCode"
    assert renamed.json()["description"] == "Regions"

    missing = client.get("/api/v1/taxonomies/missing")
    assert missing.status_code == 404
    deleted = client.delete(f"/api/v1/taxonomies/{taxonomy_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/taxonomies/{taxonomy_id}").status_code == 404
