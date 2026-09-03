"""Development seed data. DEVELOPMENT ONLY — never use real patient information."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.models.enums import RoomStatus, UserRole
from app.models.finance import DonationCategory
from app.models.lookup import State, WardClinic
from app.models.room import Room
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


def run_seed(db: Session) -> None:
    logger.warning("seed_start", message="Loading DEVELOPMENT ONLY seed data")
    seed_lookups(db)
    seed_rooms(db)
    seed_users(db)
    db.commit()
    logger.warning(
        "seed_complete",
        message="Development users created. Change all passwords before any non-dev use.",
    )
