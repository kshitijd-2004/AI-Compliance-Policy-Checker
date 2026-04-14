def test_health_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.routers_health.index.describe_index_stats", lambda: {})

    response = client.get("/health/")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "db_ok" in data or "detail" in data
