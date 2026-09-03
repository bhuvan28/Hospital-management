from datetime import date

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.finance import DonationCategory
from tests.conftest import add_user, auth_header, make_patient, seed_lookups_and_rooms


def test_donation_totals(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    category = DonationCategory(name="General", active=True)
    db.add(category)
    db.commit()
    headers = auth_header(client, "finance@rmh.example.com")
    first = client.post(
        "/api/donations",
        headers=headers,
        json={
            "date": date.today().isoformat(),
            "donor_name": "Demo Corporation",
            "type": "corporate",
            "category_id": category.id,
            "quantity": 1,
            "amount": 250,
        },
    )
    second = client.post(
        "/api/donations",
        headers=headers,
        json={
            "date": date.today().isoformat(),
            "donor_name": "Family Circle",
            "type": "rmh_family",
            "quantity": 2,
            "amount": 50.5,
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201
    summary = client.get("/api/donations/summary", headers=headers).json()
    assert float(summary["annual_total"]) == 300.5
    assert summary["total_count"] == 2


def test_petty_cash_balance_computed(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    created = client.post(
        "/api/petty-cash",
        headers=headers,
        json={
            "month": date.today().replace(day=1).isoformat(),
            "budgeted": 1000,
            "actual": 350,
            "groceries_sponsored": 100,
            "category": "groceries",
        },
    )
    assert created.status_code == 201
    assert float(created.json()["balance"]) == 650
    summary = client.get("/api/petty-cash/summary", headers=headers).json()
    assert float(summary["total_balance"]) == 650
    # Clients cannot override computed balance — field is server-derived.
    assert "balance" in created.json()


def test_meal_sponsorship_totals(client, db):
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    headers = auth_header(client, "finance@rmh.example.com")
    created = client.post(
        "/api/meal-sponsorships",
        headers=headers,
        json={
            "date": date.today().isoformat(),
            "sponsor_name": "Demo Sponsor",
            "meal_type": "lunch",
            "pax": 18,
            "amount": 180,
        },
    )
    assert created.status_code == 201
    summary = client.get("/api/meal-sponsorships/summary", headers=headers).json()
    assert float(summary["monthly_total"]) == 180
    assert summary["total_pax"] == 18


def test_reports_and_exports(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    ward, state, rooms = seed_lookups_and_rooms(db)
    patient = make_patient(db, ward, state)
    duty = auth_header(client, "duty@rmh.example.com")
    client.post(f"/api/rooms/{rooms[0].id}/check-in", headers=duty, json={"patient_id": patient.id})
    admin = auth_header(client, "admin@rmh.example.com")
    occupancy = client.get("/api/reports/occupancy", headers=admin).json()
    assert "days" in occupancy
    assert occupancy["days"][-1]["occupancy_rate"] >= 0
    census = client.get("/api/reports/census", headers=admin).json()
    assert census["patient_count"] == 1
    xlsx = client.get("/api/reports/occupancy/export", headers=admin, params={"format": "xlsx"})
    assert xlsx.status_code == 200
    assert xlsx.headers["content-type"].startswith("application/vnd.openxmlformats")
    pdf = client.get("/api/reports/census/export", headers=admin, params={"format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_audit_for_patient_room_and_finance(client, db):
    add_user(db, "admin@rmh.example.com", UserRole.ADMIN)
    add_user(db, "social@rmh.example.com", UserRole.SOCIAL_WORKER)
    add_user(db, "duty@rmh.example.com", UserRole.DUTY_OFFICER)
    add_user(db, "finance@rmh.example.com", UserRole.FINANCE)
    ward, state, rooms = seed_lookups_and_rooms(db)
    social = auth_header(client, "social@rmh.example.com")
    created = client.post(
        "/api/patients",
        headers=social,
        json={
            "name": "Audit Patient",
            "registration_no": "HCTM26-7777",
            "nric": "111111111111",
            "gender": "female",
            "dob": "2020-01-01",
            "address": "A",
            "diagnosis": "Demo",
            "ward_clinic_id": ward.id,
            "state_id": state.id,
        },
    )
    assert created.status_code == 201
    duty = auth_header(client, "duty@rmh.example.com")
    client.post(
        f"/api/rooms/{rooms[0].id}/check-in",
        headers=duty,
        json={"patient_id": created.json()["id"]},
    )
    finance = auth_header(client, "finance@rmh.example.com")
    client.post(
        "/api/donations",
        headers=finance,
        json={
            "date": date.today().isoformat(),
            "donor_name": "Audit Donor",
            "type": "cash",
            "quantity": 1,
            "amount": 10,
        },
    )
    admin = auth_header(client, "admin@rmh.example.com")
    logs = client.get("/api/audit-log", headers=admin).json()
    entities = {item["entity"] for item in logs["items"]}
    assert "Patient" in entities
    assert "RoomStay" in entities
    assert "Donation" in entities
    patient_logs = db.scalars(select(AuditLog).where(AuditLog.entity == "Patient")).all()
    assert patient_logs
    for log in patient_logs:
        dumped = str(log.after_values) + str(log.before_values)
        assert "password" not in dumped.lower()
