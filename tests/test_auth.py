from tests.conftest import ADMIN_CREDS, EMPLOYEE_CREDS


def test_first_registered_user_becomes_admin(client):
    # ADMIN_CREDS was registered first by the `client` fixture in conftest.
    res = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_CREDS["email"], "password": ADMIN_CREDS["password"]},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


def test_second_registered_user_is_employee(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": EMPLOYEE_CREDS["email"], "password": EMPLOYEE_CREDS["password"]},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "employee"


def test_register_duplicate_email_is_rejected(client):
    res = client.post("/api/v1/auth/register", json=ADMIN_CREDS)
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"].lower()


def test_register_short_password_is_rejected(client):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "shortpw@test.com", "full_name": "Short PW", "password": "abc"},
    )
    assert res.status_code == 422  # pydantic validation error


def test_login_with_wrong_password_fails(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_CREDS["email"], "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_with_unknown_email_fails(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "whatever123"},
    )
    assert res.status_code == 401


def test_me_without_token_is_rejected(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code in (401, 403)


def test_me_with_valid_token_returns_current_user(client, employee_headers):
    res = client.get("/api/v1/auth/me", headers=employee_headers)
    assert res.status_code == 200
    assert res.json()["email"] == EMPLOYEE_CREDS["email"]
