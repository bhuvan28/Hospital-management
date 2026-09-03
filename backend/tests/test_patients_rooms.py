from datetime import date, timedelta

from app.models.enums import UserRole
from app.services.occupancy import occupancy_rate
from tests.conftest import add_user, auth_header, make_patient, seed_lookups_and_rooms


def _patient_payload(ward_id: int, state_id: int, reg: str = "HCTM26-2001"):
    return {
        "name": "Farid bin Demo",
        "registration_no": reg,
        "nric": "050505105555",
        "gender": "male",
        "dob": "2019-05-05",
        "address": "Jalan Fiksyen 1",
        "diagnosis": "Fictional diagnosis",
        "referring_doctor": "Dr. Example",
        "ward_clinic_id": ward_id,
        "state_id": state_id,
        "status": "new",
        "registered_online": False,
        "sibling_count": 2,
        "sibling_names": "Aina, Amir",
        "guardians": [{"name": "Fatimah Demo", "relationship": "Mother", "contact": "013-1111111"}],
        "assessment": {"payload": {}, "notes": "Pending confirmed fee fields", "assessed_fee_amount": 0},
    }


def test_create_edit_search_patient(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=headers, json=_patient_payload(ward.id, state.id))
    assert created.status_code == 201
    patient_id = created.json()["id"]
    assert created.json()["nric"] == "050505105555"
    edited = client.patch(
        f"/api/patients/{patient_id}",
        headers=headers,
        json={"name": "Farid bin Updated"},
    )
    assert edited.status_code == 200
    assert edited.json()["name"] == "Farid bin Updated"
    search = client.get("/api/patients", headers=headers, params={"q": "Farid"})
    assert search.status_code == 200
    assert search.json()["total"] == 1
    filtered = client.get("/api/patients", headers=headers, params={"ward_clinic_id": ward.id, "status": "new"})
    assert filtered.json()["total"] == 1


def test_duty_officer_does_not_see_nric_or_diagnosis(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    social = auth_header(client, "social@rmh.example.com")
    created = client.post("/api/patients", headers=social, json=_patient_payload(ward.id, state.id))
    duty = auth_header(client, "duty@rmh.example.com")
    listed = client.get("/api/patients", headers=duty)
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["nric"] is None
    assert item["diagnosis"] is None
    detail = client.get(f"/api/patients/{created.json()['id']}", headers=duty)
    assert detail.json()["nric"] is None
    assert detail.json()["guardians"] == []


def test_patient_validation(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    payload = _patient_payload(ward.id, state.id)
    payload["dob"] = "2999-01-01"
    response = client.post("/api/patients", headers=headers, json=payload)
    assert response.status_code == 422


def test_duplicate_registration_rejected(client, db):
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    ward, state, _ = seed_lookups_and_rooms(db)
    headers = auth_header(client, "social@rmh.example.com")
    first = client.post("/api/patients", headers=headers, json=_patient_payload(ward.id, state.id))
    assert first.status_code == 201
    second = client.post("/api/patients", headers=headers, json=_patient_payload(ward.id, state.id))
    assert second.status_code == 409


def test_check_in_out_and_occupancy(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    room_id = rooms[0].id
    checkin = client.post(
        f"/api/rooms/{room_id}/check-in",
        headers=headers,
        json={"patient_id": patient.id, "room_inspected": True},
    )
    assert checkin.status_code == 200
    stay_id = checkin.json()["id"]
    occupied = client.post(
        f"/api/rooms/{room_id}/check-in",
        headers=headers,
        json={"patient_id": patient.id},
    )
    assert occupied.status_code == 409
    summary = client.get("/api/occupancy/summary", headers=headers).json()
    assert summary["occupied_rooms"] == 1
    assert summary["occupancy_rate"] == occupancy_rate(1, 4)
    checkout = client.post(f"/api/stays/{stay_id}/check-out", headers=headers, json={})
    assert checkout.status_code == 200
    after = client.get("/api/occupancy/summary", headers=headers).json()
    assert after["occupied_rooms"] == 0
    assert after["occupancy_rate"] == 0


def test_cannot_check_out_before_check_in(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    checkin = client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=headers,
        json={"patient_id": patient.id, "check_in_date": date.today().isoformat()},
    )
    stay_id = checkin.json()["id"]
    too_early = date.today() - timedelta(days=2)
    response = client.post(
        f"/api/stays/{stay_id}/check-out",
        headers=headers,
        json={"check_out_date": too_early.isoformat()},
    )
    assert response.status_code == 409


def test_waitlist_days_waited(client, db):
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, _ = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    headers = auth_header(client, "duty@rmh.example.com")
    added = date.today() - timedelta(days=5)
    created = client.post(
        "/api/waitlist",
        headers=headers,
        json={"patient_id": patient.id, "added_date": added.isoformat()},
    )
    assert created.status_code == 201
    assert created.json()["days_waited"] == 5


def test_occupancy_rate_unit():
    assert occupancy_rate(0, 18) == 0
    assert occupancy_rate(9, 18) == 50.0
    assert occupancy_rate(18, 18) == 100.0
    assert occupancy_rate(1, 0) == 0.0
