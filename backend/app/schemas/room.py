from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import RoomStatus
from app.schemas.common import ORMModel


class RoomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    status: RoomStatus = RoomStatus.VACANT
    notes: str | None = None


class RoomUpdate(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=20)
    status: RoomStatus | None = None
    notes: str | None = None


class OccupantSummary(BaseModel):
    patient_id: int
    patient_name: str
    registration_no: str
    ward_name: str | None = None
    check_in_date: date
    officer_name: str | None = None
    room_inspected: bool
    remarks: str | None = None
    stay_id: int


class RoomOut(ORMModel):
    id: int
    room_number: str
    status: RoomStatus
    occupancy_status: RoomStatus
    notes: str | None
    current_occupant: OccupantSummary | None = None


class CheckInRequest(BaseModel):
    patient_id: int
    hospital_admission_date: date | None = None
    check_in_date: date | None = None
    room_inspected: bool = False
    remarks: str | None = None


class CheckOutRequest(BaseModel):
    check_out_date: date | None = None
    remarks: str | None = None


class StayOut(ORMModel):
    id: int
    patient_id: int
    room_id: int
    hospital_admission_date: date | None
    check_in_date: date
    check_out_date: date | None
    officer_on_duty_id: int | None
    room_inspected: bool
    remarks: str | None


class StayListOut(StayOut):
    patient_name: str | None = None
    registration_no: str | None = None
    room_number: str | None = None
    officer_name: str | None = None


class OccupancySummary(BaseModel):
    total_rooms: int
    occupied_rooms: int
    vacant_rooms: int
    maintenance_rooms: int
    occupancy_rate: float
    todays_check_ins: int
    todays_check_outs: int
    waiting_list_open: int


class WaitlistCreate(BaseModel):
    patient_id: int
    added_date: date | None = None
    remarks: str | None = None


class WaitlistResolve(BaseModel):
    remarks: str | None = None
    resolved_date: date | None = None


class WaitlistOut(ORMModel):
    id: int
    patient_id: int
    patient_name: str
    registration_no: str
    added_date: date
    resolved_date: date | None
    days_waited: int
    remarks: str | None
