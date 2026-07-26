from tests.conftest import ADMIN_CREDS, EMPLOYEE_CREDS


def test_admin_can_list_all_users(client, admin_headers):
    res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200

    users = res.json()
    emails = {u["email"] for u in users}
    assert ADMIN_CREDS["email"] in emails
    assert EMPLOYEE_CREDS["email"] in emails


def test_employee_cannot_list_users(client, employee_headers):
    res = client.get("/api/v1/admin/users", headers=employee_headers)
    assert res.status_code == 403


def test_unauthenticated_cannot_list_users(client):
    res = client.get("/api/v1/admin/users")
    assert res.status_code in (401, 403)
