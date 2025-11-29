def test_upload_and_list_policies(client, monkeypatch):
    monkeypatch.setattr("app.ingestion.extract_text_from_pdf", lambda x: "test pdf")
    monkeypatch.setattr("app.ingestion.index_policy_chunks", lambda x: None)

    file = ("policy.pdf", b"hello world", "application/pdf")

    resp = client.post(
        "/policies/upload",
        files={"file": file},
        data={"title": "Test Policy", "policy_type": "security"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Policy"

    # list
    resp2 = client.get("/policies")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
