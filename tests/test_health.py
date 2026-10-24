def test_health_and_openapi(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert "/api/v1/taxonomies" in paths
    assert "/api/v1/domains" in paths
    assert "/api/v1/domain-instances/{instance_id}/entities" in paths
