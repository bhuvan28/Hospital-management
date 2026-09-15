from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship
from sqlalchemy.types import JSON

from app.database import Base
from app.models.enums import Gender, PatientStatus


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    registration_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nric: Mapped[str] = mapped_column(String(32), nullable=False)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender", native_enum=False, length=20),
        nullable=False,
    )
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    referring_doctor: Mapped[str | None] = mapped_column(String(200))
    ward_clinic_id: Mapped[int] = mapped_column(ForeignKey("ward_clinics.id"), nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    status: Mapped[PatientStatus] = mapped_column(
        Enum(PatientStatus, name="patient_status", native_enum=False, length=20),
        nullable=False,
        default=PatientStatus.NEW,
    )
    registered_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sibling_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sibling_names: Mapped[str | None] = mapped_column(Text)

    ward_clinic = orm_relationship("WardClinic", back_populates="patients")
    state = orm_relationship("State", back_populates="patients")
    guardians = orm_relationship(
        "Guardian",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    assessment = orm_relationship(
        "SocialWorkerAssessment",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stays = orm_relationship("RoomStay", back_populates="patient")
    waitlist_entries = orm_relationship("WaitlistEntry", back_populates="patient")


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship: Mapped[str] = mapped_column(String(80), nullable=False)
    contact: Mapped[str] = mapped_column(String(80), nullable=False)

    patient = orm_relationship("Patient", back_populates="guardians")


class SocialWorkerAssessment(Base):
    """Extensible assessment block.

    Exact room-fee fields are an open PRD question. `payload` holds future
    confirmed fields as JSON without inventing medical/business rules.
    `assessed_fee_amount` is optional free-text numeric capture only — the
    application never computes a fee formula.
    """

    __tablename__ = "social_worker_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)
    assessed_fee_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    assessed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patient = orm_relationship("Patient", back_populates="assessment")
    assessed_by = orm_relationship("User", back_populates="assessments")
