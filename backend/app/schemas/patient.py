from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Gender, PatientStatus
from app.schemas.common import LookupOut, ORMModel

# Reasonable identity text only. The PRD does not specify a Malaysian 12-digit NRIC format.
_NRIC_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 \-/]*")


class GuardianIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship: str = Field(min_length=1, max_length=80)
    contact: str = Field(min_length=1, max_length=80)


class GuardianOut(ORMModel):
    id: int
    name: str
    relationship: str
    contact: str


class AssessmentIn(BaseModel):
    payload: dict = Field(default_factory=dict)
    notes: str | None = None
    assessed_fee_amount: Decimal | None = Field(default=None, ge=0)


class AssessmentOut(ORMModel):
    id: int
    payload: dict
    notes: str | None
    assessed_fee_amount: Decimal | None
    assessed_by_id: int | None
    assessed_at: datetime | None


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    registration_no: str = Field(min_length=1, max_length=64)
    nric: str = Field(min_length=4, max_length=32)
    gender: Gender
    dob: date
    address: str = Field(min_length=1)
    diagnosis: str = Field(min_length=1)
    referring_doctor: str | None = None
    ward_clinic_id: int
    state_id: int
    status: PatientStatus = PatientStatus.NEW
    registered_online: bool = False
    registered_at: datetime | None = None
    sibling_count: int = Field(default=0, ge=0)
    sibling_names: str | None = None
    guardians: list[GuardianIn] = Field(default_factory=list)
    assessment: AssessmentIn | None = None

    @field_validator("registration_no")
    @classmethod
    def registration_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Registration number is required")
        return cleaned

    @field_validator("nric")
    @classmethod
    def nric_reasonable(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("NRIC / identification number is too short")
        if not _NRIC_RE.fullmatch(cleaned):
            raise ValueError("NRIC / identification number contains invalid characters")
        return cleaned

    @field_validator("dob")
    @classmethod
    def dob_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    registration_no: str | None = Field(default=None, min_length=1, max_length=64)
    nric: str | None = Field(default=None, min_length=4, max_length=32)
    gender: Gender | None = None
    dob: date | None = None
    address: str | None = None
    diagnosis: str | None = None
    referring_doctor: str | None = None
    ward_clinic_id: int | None = None
    state_id: int | None = None
    status: PatientStatus | None = None
    registered_online: bool | None = None
    registered_at: datetime | None = None
    sibling_count: int | None = Field(default=None, ge=0)
    sibling_names: str | None = None
    guardians: list[GuardianIn] | None = None
    assessment: AssessmentIn | None = None

    @field_validator("nric")
    @classmethod
    def nric_reasonable(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise ValueError("NRIC / identification number is too short")
        if not _NRIC_RE.fullmatch(cleaned):
            raise ValueError("NRIC / identification number contains invalid characters")
        return cleaned

    @field_validator("dob")
    @classmethod
    def dob_not_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class PatientListOut(ORMModel):
    id: int
    name: str
    registration_no: str
    gender: Gender
    status: PatientStatus
    ward_clinic: LookupOut
    state: LookupOut
    registered_at: datetime
    registered_online: bool
    nric: str | None = None
    diagnosis: str | None = None
    house_status: str = "none"
    room_number: str | None = None


class PatientDetailOut(PatientListOut):
    dob: date | None = None
    address: str | None = None
    referring_doctor: str | None = None
    sibling_count: int
    sibling_names: str | None = None
    guardians: list[GuardianOut] = Field(default_factory=list)
    assessment: AssessmentOut | None = None
