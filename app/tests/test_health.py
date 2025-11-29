def test_health_endpoint(client, monkeypatch):
    # stub pinecone
    monkeypatch.setattr("app.routers_health.index.describe_index_stats", lambda: {})
    
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert "db_ok" in response.json()
    assert "pinecone_ok" in response.json()