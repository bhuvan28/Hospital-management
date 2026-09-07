from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["CORS_ORIGINS"] = "http://test"

from collections.abc import Generator  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import (
    Session,  # noqa: E402
    sessionmaker,  # noqa: E402
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import Gender, PatientStatus, UserRole  # noqa: E402
from app.models.lookup import State, WardClinic  # noqa: E402
from app.models.patient import Guardian, Patient  # noqa: E402
from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security.hashing import hash_password  # noqa: E402

get_settings.cache_clear()

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client


def add_user(db: Session, email: str, role: UserRole, password: str = "DevPass!2026", active: bool = True) -> User:
    user = User(
        name=email.split("@")[0].title(),
        email=email,
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_lookups_and_rooms(db: Session) -> tuple[WardClinic, State, list[Room]]:
    ward = WardClinic(name="Wad Pediatrik 4A", active=True)
    state = State(name="Selangor", active=True)
    db.add_all([ward, state])
    rooms = [Room(room_number=f"{n:02d}") for n in range(1, 5)]
    db.add_all(rooms)
    db.commit()
    db.refresh(ward)
    db.refresh(state)
    return ward, state, rooms


def make_patient(db: Session, ward: WardClinic, state: State, reg: str = "HCTM26-1001") -> Patient:
    patient = Patient(
        name="Aisyah binti Demo",
        registration_no=reg,
        nric="060101145678",
        gender=Gender.FEMALE,
        dob=date(2018, 3, 12),
        address="No. 1, Jalan Demo, Shah Alam",
        diagnosis="Demo diagnosis — fictional",
        referring_doctor="Dr. Demo",
        ward_clinic_id=ward.id,
        state_id=state.id,
        status=PatientStatus.NEW,
        registered_online=False,
        registered_at=datetime.now(timezone.utc),
        sibling_count=1,
        sibling_names="Amin Demo",
        guardians=[Guardian(name="Siti Demo", relationship="Mother", contact="012-0000000")],
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def login(client: TestClient, email: str, password: str = "DevPass!2026"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def auth_header(client: TestClient, email: str, password: str = "DevPass!2026") -> dict[str, str]:
    response = login(client, email, password)
    token = response.cookies.get("rmh_session")
    return {"Authorization": f"Bearer {token}"}
