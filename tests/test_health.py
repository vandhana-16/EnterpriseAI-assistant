def test_health_check_returns_ok(client):
    res = client.get("/health")
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "ok"
    assert "app" in body
