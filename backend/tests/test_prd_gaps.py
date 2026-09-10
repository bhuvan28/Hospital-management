from datetime import date, timedelta

from sqlalchemy import select

from app.models.audit import AuditLog, AuditLogImmutableError
from app.models.enums import RoomStatus, UserRole
from app.models.room import Room
from app.services.occupancy import occupancy_rate
from app.services.reports import REPORT_BUILDERS
from tests.conftest import add_user, auth_header, make_patient, seed_lookups_and_rooms
from tests.test_patients_rooms import _patient_payload


def test_social_worker_can_write_patients_not_finance_or_check_in(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=headers, json=_patient_payload(ward.id, state.id))
    assert created.status_code == 201
    assert client.get("/api/donations", headers=headers).status_code == 403
    assert client.get("/api/petty-cash", headers=headers).status_code == 403
    denied = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": created.json()["id"]},
    )
    assert denied.status_code == 403


def test_assessment_preserved_on_partial_patch(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    payload = _patient_payload(ward.id, state.id)
    payload["assessment"] = {
        "payload": {"confirmed_later": True, "ppk_note": "open question"},
        "notes": "Pending confirmed fee fields",
        "assessed_fee_amount": 12.5,
    }
    created = client.post("/api/patients", headers=headers, json=payload)
    assert created.status_code == 201
    patient_id = created.json()["id"]
    edited = client.patch(f"/api/patients/{patient_id}", headers=headers, json={"name": "Farid bin Updated"})
    assert edited.status_code == 200
    detail = client.get(f"/api/patients/{patient_id}", headers=headers).json()
    assert detail["name"] == "Farid bin Updated"
    assert detail["assessment"]["payload"]["confirmed_later"] is True
    assert detail["assessment"]["notes"] == "Pending confirmed fee fields"
    emptied = client.patch(
        f"/api/patients/{patient_id}",
        headers=headers,
        json={"assessment": {"payload": {}, "notes": "Updated notes only", "assessed_fee_amount": 12.5}},
    )
    assert emptied.status_code == 200
    assert emptied.json()["assessment"]["payload"]["confirmed_later"] is True
    assert emptied.json()["assessment"]["notes"] == "Updated notes only"


def test_maintenance_room_check_in_forbidden(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    marked = client.patch(f"/api/rooms/{rooms[0].id}", headers=headers, json={"status": "maintenance"})
    assert marked.status_code == 200
    denied = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": patient.id},
    )
    assert denied.status_code == 409


def test_stale_occupied_status_without_stay_allows_check_in(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    room = db.get(Room, rooms[0].id)
    room.status = RoomStatus.OCCUPIED
    db.commit()
    checkin = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": patient.id},
    )
    assert checkin.status_code == 200
    summary = client.get("/api/occupancy/summary", headers=headers).json()
    assert summary["occupied_rooms"] == 1
    assert summary["occupancy_rate"] == occupancy_rate(1, 4)


def test_stale_vacant_status_does_not_allow_second_occupant(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    first = make_patient(db, ward, state, "HCTM26-5101")
    second = make_patient(db, ward, state, "HCTM26-5102")
    headers = auth_header(client, "duty@rmh.example.com")
    assert client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": first.id},
    ).status_code == 200
    room = db.get(Room, rooms[0].id)
    room.status = RoomStatus.VACANT
    db.commit()
    denied = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": second.id},
    )
    assert denied.status_code == 409


def test_all_report_slugs_smoke_and_no_pii(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    duty = auth_header(client, "duty@rmh.example.com")
    client.post(f"/api/rooms/{rooms[0].id}/check-in", headers=duty, json={"patient_id": patient.id})
    admin = auth_header(client, "admin@rmh.example.com")
    for slug in REPORT_BUILDERS:
        response = client.get(f"/api/reports/{slug}", headers=admin)
        assert response.status_code == 200, slug
        dumped = str(response.json()).lower()
        assert "aisyah" not in dumped
        assert "nric" not in dumped
        assert "060101145678" not in dumped
    trend = client.get("/api/reports/occupancy-trend", headers=admin, params={"grain": "year"}).json()
    assert trend["grain"] == "year"
    assert trend["trend"]
    census = client.get(
        "/api/reports/census",
        headers=admin,
        params={"ward_clinic_id": ward.id, "status": "new"},
    ).json()
    assert census["patient_count"] == 1
    empty = client.get("/api/reports/census", headers=admin, params={"status": "returning"}).json()
    assert empty["patient_count"] == 0
    xlsx = client.get("/api/reports/donations-summary/export", headers=admin, params={"format": "xlsx"})
    assert xlsx.status_code == 200
    pdf = client.get("/api/reports/petty-cash/export", headers=admin, params={"format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_petty_cash_patch_rejects_duplicate_month_category(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    month = date.today().replace(day=1).isoformat()
    first = client.post(
        "/api/petty-cash",
        headers=headers,
        json={"month": month, "budgeted": 100, "actual": 10, "category": "groceries"},
    )
    second = client.post(
        "/api/petty-cash",
        headers=headers,
        json={"month": month, "budgeted": 50, "actual": 5, "category": "other"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    clash = client.patch(
        f"/api/petty-cash/{second.json()['id']}",
        headers=headers,
        json={"category": "groceries"},
    )
    assert clash.status_code == 409


def test_donation_patch_unknown_category(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    created = client.post(
        "/api/donations",
        headers=headers,
        json={
            "date": date.today().isoformat(),
            "donor_name": "Demo",
            "type": "cash",
            "quantity": 1,
            "amount": 10,
        },
    )
    assert created.status_code == 201
    missing = client.patch(
        f"/api/donations/{created.json()['id']}",
        headers=headers,
        json={"category_id": 99999},
    )
    assert missing.status_code == 404


def test_admin_can_delete_patient_without_stay_history(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    social = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=social, json=_patient_payload(ward.id, state.id, "HCTM26-8801"))
    patient_id = created.json()["id"]
    admin = auth_header(client, "admin@rmh.example.com")
    assert client.delete(f"/api/patients/{patient_id}", headers=admin).status_code == 204
    staying = make_patient(db, ward, state, "HCTM26-8802")
    duty = add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    duty_headers = auth_header(client, "duty@rmh.example.com")
    client.post(f"/api/rooms/{rooms[0].id}/check-in", headers=duty_headers, json={"patient_id": staying.id})
    blocked = client.delete(f"/api/patients/{staying.id}", headers=admin)
    assert blocked.status_code == 409
    assert duty.email == "duty@rmh.example.com"


def test_waitlist_search_and_days_waited(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, _ = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    added = date.today() - timedelta(days=3)
    created = client.post(
        "/api/waitlist",
        headers=headers,
        json={"patient_id": patient.id, "added_date": added.isoformat()},
    )
    assert created.status_code == 201
    found = client.get("/api/waitlist", headers=headers, params={"q": "Aisyah"})
    assert found.status_code == 200
    assert found.json()[0]["days_waited"] == 3
    missing = client.get("/api/waitlist", headers=headers, params={"q": "nobody-here"})
    assert missing.json() == []


def test_waitlist_rejects_patient_with_open_stay(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    assert client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": patient.id},
    ).status_code == 200
    denied = client.post("/api/waitlist", headers=headers, json={"patient_id": patient.id})
    assert denied.status_code == 409


def test_patient_audit_includes_guardians_and_assessment(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    social = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=social, json=_patient_payload(ward.id, state.id, "HCTM26-6101"))
    assert created.status_code == 201
    admin = auth_header(client, "admin@rmh.example.com")
    logs = client.get("/api/audit-log", headers=admin, params={"entity": "Patient"}).json()
    after = logs["items"][0]["after_values"]
    assert after["guardians"][0]["name"] == "Fatimah Demo"
    assert after["guardians"][0]["contact"] == "013-1111111"
    assert after["assessment"]["notes"] == "Pending confirmed fee fields"


def test_finance_patch_audit_includes_changed_fields(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    created = client.post(
        "/api/donations",
        headers=headers,
        json={
            "date": date.today().isoformat(),
            "donor_name": "Audit Corp",
            "type": "cash",
            "item_remark": "Original",
            "quantity": 1,
            "amount": 10,
        },
    )
    assert created.status_code == 201
    patched = client.patch(
        f"/api/donations/{created.json()['id']}",
        headers=headers,
        json={"item_remark": "Updated remark", "quantity": 3},
    )
    assert patched.status_code == 200
    admin = auth_header(client, "admin@rmh.example.com")
    logs = client.get("/api/audit-log", headers=admin, params={"entity": "Donation", "action": "update"}).json()
    after = logs["items"][0]["after_values"]
    assert after["item_remark"] == "Updated remark"
    assert after["quantity"] == 3
    assert "item_remark" in logs["items"][0]["changed_fields"]


def test_report_rejects_inverted_date_range(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    headers = auth_header(client, "admin@rmh.example.com")
    response = client.get(
        "/api/reports/occupancy",
        headers=headers,
        params={"start": "2026-12-01", "end": "2026-01-01"},
    )
    assert response.status_code == 422


def test_stay_history_and_derived_occupancy_status(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    checkin = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": patient.id},
    )
    assert checkin.status_code == 200
    stay_id = checkin.json()["id"]
    listed = client.get("/api/stays", headers=headers, params={"open_only": True})
    assert listed.status_code == 200
    assert listed.json()[0]["patient_name"] == "Aisyah binti Demo"
    assert listed.json()[0]["room_number"] == rooms[0].room_number
    detail = client.get(f"/api/stays/{stay_id}", headers=headers)
    assert detail.status_code == 200
    room = client.get(f"/api/rooms/{rooms[0].id}", headers=headers)
    assert room.status_code == 200
    assert room.json()["occupancy_status"] == "occupied"
    assert room.json()["current_occupant"]["stay_id"] == stay_id


def test_audit_logs_are_immutable_in_application(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=headers, json=_patient_payload(ward.id, state.id, "HCTM26-6201"))
    assert created.status_code == 201
    log = db.scalar(select(AuditLog).where(AuditLog.entity == "Patient"))
    assert log is not None
    log.entity = "Hacked"
    try:
        db.commit()
        raise AssertionError("audit update should be rejected")
    except AuditLogImmutableError:
        db.rollback()
    log = db.scalar(select(AuditLog).where(AuditLog.entity == "Patient"))
    try:
        db.delete(log)
        db.commit()
        raise AssertionError("audit delete should be rejected")
    except AuditLogImmutableError:
        db.rollback()

