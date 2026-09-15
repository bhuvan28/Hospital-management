"""Development seed data. DEVELOPMENT ONLY — never use real patient information."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.models.enums import DonationType, Gender, MealType, PatientStatus, PettyCashCategory, RoomStatus, UserRole
from app.models.finance import Donation, DonationCategory, MealSponsorship, PettyCashEntry
from app.models.lookup import State, WardClinic
from app.models.patient import Guardian, Patient, SocialWorkerAssessment
from app.models.room import Room, RoomStay, WaitlistEntry
from app.models.user import User
from app.security.hashing import hash_password

logger = get_logger("seed")

# Configurable lookups. These are seed values, not hardcoded frontend enums.
WARD_CLINICS = [
    "Wad Pediatrik 4A",
    "Wad Pediatrik 4B",
    "Wad Onkologi Pediatrik",
    "PICU",
    "NICU",
    "Wad Hematologi",
    "Klinik Pakar Pediatrik",
    "Wad Pembedahan Pediatrik",
    "Jabatan Kecemasan",
    "Lain-lain",
]

MALAYSIAN_STATES = [
    "Johor",
    "Kedah",
    "Kelantan",
    "Melaka",
    "Negeri Sembilan",
    "Pahang",
    "Pulau Pinang",
    "Perak",
    "Perlis",
    "Sabah",
    "Sarawak",
    "Selangor",
    "Terengganu",
    "W.P. Kuala Lumpur",
    "W.P. Labuan",
    "W.P. Putrajaya",
    "Luar Negara",
]

DONATION_CATEGORIES = [
    "General",
    "Food",
    "Household",
    "Medical Comfort",
    "Festive / Event",
    "Corporate Programme",
    "Volunteer Support",
]

DEV_USERS = [
    ("Operations Administrator", "admin@rmh.example.com", "DevAdmin!2026", UserRole.ADMIN),
    ("Duty Officer", "duty@rmh.example.com", "DevDuty!2026", UserRole.DUTY_OFFICER),
    ("Social Worker", "social@rmh.example.com", "DevSocial!2026", UserRole.SOCIAL_WORKER),
    ("Finance Officer", "finance@rmh.example.com", "DevFinance!2026", UserRole.FINANCE),
    ("Reporting Viewer", "viewer@rmh.example.com", "DevViewer!2026", UserRole.VIEWER),
]


def seed_lookups(db: Session) -> None:
    for name in WARD_CLINICS:
        if db.scalar(select(WardClinic).where(WardClinic.name == name)) is None:
            db.add(WardClinic(name=name, active=True))
    for name in MALAYSIAN_STATES:
        if db.scalar(select(State).where(State.name == name)) is None:
            db.add(State(name=name, active=True))
    for name in DONATION_CATEGORIES:
        if db.scalar(select(DonationCategory).where(DonationCategory.name == name)) is None:
            db.add(DonationCategory(name=name, active=True))
    db.flush()


def seed_rooms(db: Session) -> None:
    """Seed the initial 18 rooms. Rooms remain configurable after seed."""
    existing = db.scalar(select(Room).limit(1))
    if existing:
        return
    for number in range(1, 19):
        db.add(Room(room_number=f"{number:02d}", status=RoomStatus.VACANT))
    db.flush()


def seed_users(db: Session) -> None:
    settings = get_settings()
    for name, email, password, role in DEV_USERS:
        if db.scalar(select(User).where(User.email == email)) is None:
            chosen = settings.seed_admin_password if role == UserRole.ADMIN else password
            db.add(
                User(
                    name=name,
                    email=email,
                    password_hash=hash_password(chosen),
                    role=role,
                    active=True,
                )
            )
    db.flush()


def seed_demo_records(db: Session) -> None:
    """Fictional operational sample for local dashboards. Never real families."""
    if db.scalar(select(Patient.id).limit(1)):
        return
    ward = db.scalar(select(WardClinic).where(WardClinic.name == "Wad Pediatrik 4A"))
    state = db.scalar(select(State).where(State.name == "Selangor"))
    duty = db.scalar(select(User).where(User.email == "duty@rmh.example.com"))
    social = db.scalar(select(User).where(User.email == "social@rmh.example.com"))
    rooms = list(db.scalars(select(Room).order_by(Room.room_number)).all())
    category = db.scalar(select(DonationCategory).where(DonationCategory.name == "General"))
    if not (ward and state and duty and rooms):
        return

    today = date.today()
    registered = datetime.now(timezone.utc)

    occupied = Patient(
        name="Aisyah binti Demo",
        registration_no="HCTM26-1001",
        nric="060101145678",
        gender=Gender.FEMALE,
        dob=date(2018, 3, 12),
        address="No. 1, Jalan Demo, Shah Alam",
        diagnosis="Fictional diagnosis — development sample",
        referring_doctor="Dr. Demo",
        ward_clinic_id=ward.id,
        state_id=state.id,
        status=PatientStatus.NEW,
        registered_online=True,
        registered_at=registered,
        sibling_count=1,
        sibling_names="Amin Demo",
        guardians=[Guardian(name="Siti Demo", relationship="Mother", contact="012-0000000")],
        assessment=SocialWorkerAssessment(
            payload={},
            notes="Fee fields not yet confirmed in the PRD. Sample notes only.",
            assessed_fee_amount=Decimal("0"),
            assessed_by_id=social.id if social else None,
            assessed_at=registered,
        ),
    )
    vacant_family = Patient(
        name="Farid bin Demo",
        registration_no="HCTM26-1002",
        nric="050505105555",
        gender=Gender.MALE,
        dob=date(2019, 5, 5),
        address="No. 2, Jalan Fiksyen, Cheras",
        diagnosis="Fictional diagnosis — development sample",
        referring_doctor="Dr. Example",
        ward_clinic_id=ward.id,
        state_id=state.id,
        status=PatientStatus.RETURNING,
        registered_online=False,
        registered_at=registered,
        sibling_count=2,
        sibling_names="Aina Demo, Amir Demo",
        guardians=[Guardian(name="Fatimah Demo", relationship="Mother", contact="013-1111111")],
    )
    waiting = Patient(
        name="Nurul binti Demo",
        registration_no="HCTM26-1003",
        nric="070707147777",
        gender=Gender.FEMALE,
        dob=date(2020, 7, 7),
        address="No. 3, Jalan Contoh, Kajang",
        diagnosis="Fictional diagnosis — development sample",
        ward_clinic_id=ward.id,
        state_id=state.id,
        status=PatientStatus.NEW,
        registered_online=False,
        registered_at=registered,
        sibling_count=0,
        guardians=[Guardian(name="Ahmad Demo", relationship="Father", contact="014-2222222")],
    )
    db.add_all([occupied, vacant_family, waiting])
    db.flush()

    room = rooms[0]
    room.status = RoomStatus.OCCUPIED
    db.add(
        RoomStay(
            patient_id=occupied.id,
            room_id=room.id,
            hospital_admission_date=today - timedelta(days=3),
            check_in_date=today - timedelta(days=2),
            officer_on_duty_id=duty.id,
            room_inspected=True,
            remarks="Development sample stay",
        )
    )
    db.add(
        WaitlistEntry(
            patient_id=waiting.id,
            added_date=today - timedelta(days=4),
            remarks="Awaiting a vacant room — fictional sample",
        )
    )
    if category:
        db.add(
            Donation(
                date=today,
                donor_name="Demo Corporation Sdn Bhd",
                type=DonationType.CORPORATE,
                category_id=category.id,
                item_remark="Fictional house-level donation",
                quantity=1,
                amount=Decimal("250.00"),
            )
        )
    db.add(
        PettyCashEntry(
            month=today.replace(day=1),
            budgeted=Decimal("1000.00"),
            actual=Decimal("350.00"),
            groceries_sponsored=Decimal("100.00"),
            category=PettyCashCategory.GROCERIES,
            remarks="Development sample — computed balance is budget minus actual",
        )
    )
    db.add(
        MealSponsorship(
            date=today,
            sponsor_name="Demo Meal Sponsor",
            item_remark="Packed lunch — fictional",
            meal_type=MealType.LUNCH,
            pax=18,
            amount=Decimal("180.00"),
        )
    )
    db.flush()


def run_seed(db: Session) -> None:
    settings = get_settings()
    logger.warning("seed_start", message="Loading DEVELOPMENT ONLY seed data")
    seed_lookups(db)
    seed_rooms(db)
    seed_users(db)
    if settings.seed_demo_records:
        seed_demo_records(db)
    db.commit()
    logger.warning(
        "seed_complete",
        message="Development users created. Change all passwords before any non-dev use.",
    )
