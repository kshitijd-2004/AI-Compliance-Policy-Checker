def test_compliance_check_flow(client, monkeypatch):
    # stub graph output
    fake_response = {
        "overall_risk": "LOW",
        "issues": [],
        "suggested_text": "safe text"
    }

    class FakeGraph:
        def invoke(self, state):
            return {"response": fake_response}

    monkeypatch.setattr("app.routers_compliance.compliance_app", FakeGraph())

    body = {
        "text": "This is a test",
        "department": "Sales",
        "policy_type": None,
        "top_k": 2
    }

    resp = client.post("/compliance/check", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_risk"] == "LOW"

    # verify DB log exists
    resp2 = client.get("/compliance/logs")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
