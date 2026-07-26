"""
Shared pytest fixtures.

Runs the real FastAPI app (same routes, same RBAC) but points it at a
throwaway SQLite file so tests never touch your real enterprise_ai.db.
"""
import os
import pytest

TEST_DIR = os.path.dirname(__file__)
TEST_DB_PATH = os.path.join(TEST_DIR, "test.db")

# IMPORTANT: these env vars must be set BEFORE `app.main` (and therefore
# app.core.config.settings) gets imported, since Settings reads them once
# at import time.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["UPLOAD_DIR"] = os.path.join(TEST_DIR, "test_uploads")
os.environ["CHROMA_PERSIST_DIR"] = os.path.join(TEST_DIR, "test_vectorstore")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_CREDS = {
    "email": "admin@test.com",
    "full_name": "Admin User",
    "password": "adminpass123",
}
EMPLOYEE_CREDS = {
    "email": "employee@test.com",
    "full_name": "Employee User",
    "password": "employeepass123",
}


@pytest.fixture(scope="session")
def client():
    """A TestClient backed by a fresh test DB, seeded with one admin
    (the first account ever registered — see auth_service.register_user)
    and one regular employee."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    with TestClient(app) as c:
        c.post("/api/v1/auth/register", json=ADMIN_CREDS)
        c.post("/api/v1/auth/register", json=EMPLOYEE_CREDS)
        yield c

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def _login(client, creds):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return _login(client, ADMIN_CREDS)


@pytest.fixture(scope="session")
def employee_headers(client):
    return _login(client, EMPLOYEE_CREDS)
