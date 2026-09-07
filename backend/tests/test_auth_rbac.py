from app.models.enums import UserRole
from tests.conftest import add_user, auth_header, login


def test_valid_login(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    response = login(client, "admin@rmh.example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "admin@rmh.example.com"
    assert body["user"]["role"] == "admin"
    assert "patients:write" in body["user"]["permissions"]
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@rmh.example.com"


def test_invalid_login(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    response = login(client, "admin@rmh.example.com", "wrong-password")
    assert response.status_code == 401


def test_disabled_user_cannot_login(client, db):
    add_user(db, "inactive@rmh.example.com", UserRole.DUTY_OFFICER, active=False)
    response = login(client, "inactive@rmh.example.com")
    assert response.status_code == 403


def test_logout(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    login(client, "admin@rmh.example.com")
    csrf = client.cookies.get("rmh_csrf")
    out = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert out.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_csrf_required_for_cookie_mutations(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    login(client, "admin@rmh.example.com")
    payload = {
        "name": "CSRF Duty",
        "email": "csrf-duty@rmh.example.com",
        "password": "DevPass!2026",
        "role": "duty_officer",
    }
    blocked = client.post("/api/users", json=payload)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "csrf"
    csrf = client.cookies.get("rmh_csrf")
    allowed = client.post("/api/users", headers={"X-CSRF-Token": csrf}, json=payload)
    assert allowed.status_code == 201


def test_duty_officer_cannot_access_finance(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    headers = auth_header(client, "duty@rmh.example.com")
    assert client.get("/api/donations", headers=headers).status_code == 403
    assert client.get("/api/petty-cash", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/donations",
            headers=headers,
            json={
                "date": "2026-01-01",
                "donor_name": "X",
                "type": "cash",
                "quantity": 1,
                "amount": 10,
            },
        ).status_code
        == 403
    )


def test_finance_cannot_modify_patients(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    response = client.post(
        "/api/patients",
        headers=headers,
        json={
            "name": "Test",
            "registration_no": "HCTM26-0001",
            "nric": "000000000000",
            "gender": "female",
            "dob": "2018-01-01",
            "address": "A",
            "diagnosis": "secret",
            "ward_clinic_id": 1,
            "state_id": 1,
        },
    )
    assert response.status_code == 403


def test_viewer_cannot_access_pii(client, db):
    add_user(db, "viewer@rmh.example.com", UserRole.VIEWER)
    headers = auth_header(client, "viewer@rmh.example.com")
    assert client.get("/api/patients", headers=headers).status_code == 403
    assert client.get("/api/audit-log", headers=headers).status_code == 403


def test_admin_can_access_users(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    headers = auth_header(client, "admin@rmh.example.com")
    assert client.get("/api/users", headers=headers).status_code == 200
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "name": "New Duty",
            "email": "newduty@rmh.example.com",
            "password": "DevPass!2026",
            "role": "duty_officer",
        },
    )
    assert created.status_code == 201


def test_admin_can_deactivate_user(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    duty = add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    headers = auth_header(client, "admin@rmh.example.com")
    patched = client.patch(f"/api/users/{duty.id}", headers=headers, json={"active": False})
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert login(client, "duty@rmh.example.com").status_code == 403
    logs = client.get("/api/audit-log", headers=headers, params={"entity": "User"}).json()
    assert any(item["action"] == "deactivate" for item in logs["items"])
