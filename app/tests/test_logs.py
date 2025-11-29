def test_logs_filtering(client, monkeypatch):
    # stub graph again
    class FakeGraph:
        def invoke(self, state):
            return {"response": {
                "overall_risk": "HIGH",
                "issues": [],
                "suggested_text": "rewrite"
            }}

    monkeypatch.setattr("app.routers_compliance.compliance_app", FakeGraph())

    body = {"text": "x", "department": "HR", "policy_type": None, "top_k": 3}
    client.post("/compliance/check", json=body)

    # filter by department
    resp = client.get("/compliance/logs?department=HR")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["department"] == "HR"
