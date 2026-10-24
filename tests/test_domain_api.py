from tests.helpers import publish_account_type


def _entity(client, instance_id: str, code: str, account_type: str, status: int = 201):
    response = client.post(
        f"/api/v1/domain-instances/{instance_id}/entities",
        json={
            "code": code,
            "name": code,
            "dimensions": {"accountType": account_type},
        },
    )
    assert response.status_code == status, response.text
    return response


def test_general_ledger_instance_admits_base_and_selected_classifications(client):
    taxonomy_id = publish_account_type(client)
    product = client.get(f"/api/v1/taxonomies/{taxonomy_id}/entities/productRevenue")
    assert product.json()["classifications"] == []
    assert product.json()["effectiveClassifications"] == ["CIQ", "EDGAR"]

    unpublished = client.post(
        "/api/v1/domains",
        json={
            "name": "tooSoon",
            "dimensions": [{"name": "accountType", "taxonomyName": "accountType", "version": 1}],
        },
    )
    # Version 1 is published by the helper, so this pin is legal. A draft pin is not.
    assert unpublished.status_code == 201

    draft = client.post("/api/v1/taxonomies", json={"name": "draftOnly", "isHierarchical": False})
    assert draft.status_code == 201
    pinned_draft = client.post(
        "/api/v1/domains",
        json={
            "name": "draftPin",
            "dimensions": [{"name": "kind", "taxonomyName": "draftOnly"}],
        },
    )
    assert pinned_draft.status_code == 400
    assert pinned_draft.json()["error"]["code"] == "version_not_published"

    domain = client.post(
        "/api/v1/domains",
        json={
            "name": "generalLedger",
            "description": "GL",
            "dimensions": [{"name": "accountType", "taxonomyName": "accountType"}],
        },
    )
    assert domain.status_code == 201, domain.text
    domain_body = domain.json()
    assert domain_body["inheritedClassifications"] == ["CIQ", "EDGAR"]
    assert domain_body["dimensions"][0]["taxonomyVersion"] == 1
    assert domain_body["dimensions"][0]["taxonomyId"] == taxonomy_id
    domain_id = domain_body["id"]

    bad_selection = client.post(
        f"/api/v1/domains/{domain_id}/instances",
        json={"name": "bad", "classifications": ["SOX"]},
    )
    assert bad_selection.status_code == 400

    instance = client.post(
        f"/api/v1/domains/{domain_id}/instances",
        json={"name": "ciqGl", "classifications": ["CIQ"]},
    )
    assert instance.status_code == 201, instance.text
    instance_id = instance.json()["id"]
    assert instance.json()["classifications"] == ["CIQ"]
    assert instance.json()["dimensions"][0]["taxonomyVersion"] == 1

    product_line = _entity(client, instance_id, "lineProduct", "productRevenue")
    assert product_line.json()["dimensions"]["accountType"]["effectiveClassifications"] == [
        "CIQ",
        "EDGAR",
    ]
    _entity(client, instance_id, "lineExpense", "expense")
    rejected = _entity(client, instance_id, "lineEdgar", "edgarOnly", status=400)
    assert rejected.json()["error"]["code"] == "entity_not_admissible"
    assert rejected.json()["error"]["details"]["effectiveClassifications"] == ["EDGAR"]

    legal = client.get(f"/api/v1/domain-instances/{instance_id}/dimensions/accountType/values")
    assert legal.status_code == 200
    legal_codes = [item["code"] for item in legal.json()["items"]]
    assert legal_codes == ["accountType", "expense", "revenue", "productRevenue"]
    assert "edgarOnly" not in legal_codes

    both = client.post(
        f"/api/v1/domains/{domain_id}/instances",
        json={"name": "both", "classifications": ["CIQ", "EDGAR"]},
    )
    both_id = both.json()["id"]
    _entity(client, both_id, "lineEdgar", "edgarOnly")
    _entity(client, both_id, "lineProduct", "productRevenue")

    base_only = client.post(
        f"/api/v1/domains/{domain_id}/instances",
        json={"name": "baseOnly", "classifications": []},
    )
    base_id = base_only.json()["id"]
    _entity(client, base_id, "lineExpense", "expense")
    _entity(client, base_id, "lineProduct", "productRevenue", status=400)

    listed = client.get(f"/api/v1/domain-instances/{instance_id}/entities")
    assert [item["code"] for item in listed.json()["items"]] == ["lineExpense", "lineProduct"]

    renamed = client.patch(
        f"/api/v1/domain-instances/{instance_id}/entities/lineProduct",
        json={"name": "Product revenue line", "attributes": {"note": "primary"}},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Product revenue line"
    assert renamed.json()["attributes"] == {"note": "primary"}

    missing_dimension = client.post(
        f"/api/v1/domain-instances/{instance_id}/entities",
        json={"code": "incomplete", "name": "Incomplete", "dimensions": {}},
    )
    assert missing_dimension.status_code == 400
    assert missing_dimension.json()["error"]["code"] == "dimension_invalid"

    narrow = client.patch(
        f"/api/v1/domain-instances/{both_id}",
        json={"classifications": ["CIQ"]},
    )
    assert narrow.status_code == 409
    assert narrow.json()["error"]["details"]["entities"] == ["lineEdgar"]

    removed = client.delete(f"/api/v1/domain-instances/{both_id}/entities/lineEdgar")
    assert removed.status_code == 204
    narrowed = client.patch(
        f"/api/v1/domain-instances/{both_id}",
        json={"classifications": ["CIQ"]},
    )
    assert narrowed.status_code == 200
    assert narrowed.json()["classifications"] == ["CIQ"]


def test_pins_are_snapshot_and_default_to_the_latest_published_version(client):
    taxonomy_id = publish_account_type(client)
    base = f"/api/v1/taxonomies/{taxonomy_id}"
    opened = client.post(f"{base}/draft")
    assert opened.status_code == 200
    client.patch(f"{base}/entities/revenue", json={"classifications": ["CIQ"]})
    client.post(
        f"{base}/entities",
        json={"code": "other", "name": "Other", "parentCode": "accountType"},
    )
    published = client.post(f"{base}/publish")
    assert published.json()["latestPublishedVersion"] == 2

    latest = client.post(
        "/api/v1/domains",
        json={
            "name": "generalLedger",
            "dimensions": [{"name": "accountType", "taxonomyId": taxonomy_id}],
        },
    )
    assert latest.status_code == 201, latest.text
    assert latest.json()["dimensions"][0]["taxonomyVersion"] == 2
    assert latest.json()["inheritedClassifications"] == ["CIQ", "EDGAR"]

    pinned = client.post(
        "/api/v1/domains",
        json={
            "name": "archivedLedger",
            "dimensions": [{"name": "accountType", "taxonomyName": "accountType", "version": 1}],
        },
    )
    assert pinned.status_code == 201
    assert pinned.json()["dimensions"][0]["taxonomyVersion"] == 1

    explicit_draft = client.post(f"{base}/draft")
    assert explicit_draft.status_code == 200
    draft_number = explicit_draft.json()["latestVersion"]["version"]
    rejected = client.post(
        "/api/v1/domains",
        json={
            "name": "draftLedger",
            "dimensions": [
                {"name": "accountType", "taxonomyName": "accountType", "version": draft_number}
            ],
        },
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "version_not_published"

    instance = client.post(
        f"/api/v1/domains/{pinned.json()['id']}/instances",
        json={"name": "ciqGl", "classifications": ["CIQ"]},
    )
    instance_id = instance.json()["id"]
    # Version 1 still has revenue classified as both, so the child is admissible.
    assert (
        client.post(
            f"/api/v1/domain-instances/{instance_id}/entities",
            json={
                "code": "line",
                "name": "Line",
                "dimensions": {"accountType": "productRevenue"},
            },
        ).status_code
        == 201
    )
    # The new entity exists only on version 2 and must not resolve through the version 1 pin.
    missing = client.post(
        f"/api/v1/domain-instances/{instance_id}/entities",
        json={"code": "otherLine", "name": "Other", "dimensions": {"accountType": "other"}},
    )
    assert missing.status_code == 404

    blocked_taxonomy = client.delete(f"/api/v1/taxonomies/{taxonomy_id}")
    assert blocked_taxonomy.status_code == 409
    assert blocked_taxonomy.json()["error"]["code"] == "taxonomy_in_use"
    blocked_domain = client.delete(f"/api/v1/domains/{pinned.json()['id']}")
    assert blocked_domain.status_code == 409

    assert client.delete(f"/api/v1/domain-instances/{instance_id}").status_code == 204
    assert client.delete(f"/api/v1/domains/{pinned.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/domains/{latest.json()['id']}").status_code == 204
    assert client.get("/api/v1/domains").json()["total"] == 0
    assert client.delete(f"/api/v1/taxonomies/{taxonomy_id}").status_code == 204


def test_second_dimension_unions_classifications_and_attributes_are_bounded(client):
    publish_account_type(client)
    region = client.post(
        "/api/v1/taxonomies",
        json={"name": "region", "isHierarchical": False, "allowedClassifications": ["IFRS"]},
    )
    region_id = region.json()["id"]
    assert (
        client.post(
            f"/api/v1/taxonomies/{region_id}/entities",
            json={"code": "us", "name": "United States", "classifications": ["IFRS"]},
        ).status_code
        == 201
    )
    assert client.post(f"/api/v1/taxonomies/{region_id}/publish").status_code == 200

    domain = client.post(
        "/api/v1/domains",
        json={
            "name": "inventory",
            "dimensions": [
                {"name": "accountType", "taxonomyName": "accountType"},
                {"name": "region", "taxonomyName": "region"},
            ],
        },
    )
    assert domain.status_code == 201, domain.text
    assert domain.json()["inheritedClassifications"] == ["CIQ", "EDGAR", "IFRS"]
    domain_id = domain.json()["id"]
    instance = client.post(
        f"/api/v1/domains/{domain_id}/instances",
        json={"name": "ifrsBooks", "classifications": ["IFRS"]},
    )
    instance_id = instance.json()["id"]
    # expense is base, so it is legal even though the instance did not select CIQ or EDGAR.
    created = client.post(
        f"/api/v1/domain-instances/{instance_id}/entities",
        json={
            "code": "sku",
            "name": "SKU",
            "dimensions": {"accountType": "expense", "region": "us"},
            "attributes": {"aisle": 4},
        },
    )
    assert created.status_code == 201, created.text
    assert set(created.json()["dimensions"]) == {"accountType", "region"}

    oversized = client.post(
        f"/api/v1/domain-instances/{instance_id}/entities",
        json={
            "code": "huge",
            "name": "Huge",
            "dimensions": {"accountType": "expense", "region": "us"},
            "attributes": {"blob": "x" * 17000},
        },
    )
    assert oversized.status_code == 400

    replaced = client.patch(
        f"/api/v1/domains/{domain_id}",
        json={"dimensions": [{"name": "region", "taxonomyName": "region", "version": 1}]},
    )
    assert replaced.status_code == 200
    assert [item["name"] for item in replaced.json()["dimensions"]] == ["region"]
    # The instance kept the pins it was created with.
    snapshot = client.get(f"/api/v1/domain-instances/{instance_id}")
    assert [item["name"] for item in snapshot.json()["dimensions"]] == ["accountType", "region"]
