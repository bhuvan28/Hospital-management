from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.database import get_db
from app.models.enums import AuditAction, RoomStatus
from app.models.room import Room, RoomStay
from app.models.user import User
from app.schemas.room import (
    CheckInRequest,
    CheckOutRequest,
    OccupancySummary,
    OccupantSummary,
    RoomCreate,
    RoomOut,
    RoomUpdate,
    StayListOut,
    StayOut,
)
from app.security.rbac import has_permission
from app.services import occupancy as occupancy_service
from app.services.audit import write_audit
from app.services.exports import to_excel_table

router = APIRouter(tags=["rooms"])


def _serialize_room(room: Room) -> RoomOut:
    stay = occupancy_service.current_occupant(room)
    occupant = None
    if stay and stay.patient:
        occupant = OccupantSummary(
            patient_id=stay.patient_id,
            patient_name=stay.patient.name,
            registration_no=stay.patient.registration_no,
            ward_name=stay.patient.ward_clinic.name if stay.patient.ward_clinic else None,
            check_in_date=stay.check_in_date,
            officer_name=stay.officer.name if stay.officer else None,
            room_inspected=stay.room_inspected,
            remarks=stay.remarks,
            stay_id=stay.id,
        )
    return RoomOut(
        id=room.id,
        room_number=room.room_number,
        status=room.status,
        occupancy_status=occupancy_service.occupancy_status(room),
        notes=room.notes,
        current_occupant=occupant,
    )


def _serialize_stay(stay: RoomStay) -> StayListOut:
    return StayListOut(
        id=stay.id,
        patient_id=stay.patient_id,
        room_id=stay.room_id,
        hospital_admission_date=stay.hospital_admission_date,
        check_in_date=stay.check_in_date,
        check_out_date=stay.check_out_date,
        officer_on_duty_id=stay.officer_on_duty_id,
        room_inspected=stay.room_inspected,
        remarks=stay.remarks,
        patient_name=stay.patient.name if stay.patient else None,
        registration_no=stay.patient.registration_no if stay.patient else None,
        room_number=stay.room.room_number if stay.room else None,
        officer_name=stay.officer.name if stay.officer else None,
    )


@router.get("/api/rooms", response_model=list[RoomOut])
def list_rooms(
    occupancy_status: RoomStatus | None = None,
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    rooms = [_serialize_room(room) for room in occupancy_service.room_board(db)]
    if occupancy_status is not None:
        rooms = [room for room in rooms if room.occupancy_status == occupancy_status]
    return rooms


@router.get("/api/rooms/export")
def export_room_board(
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    summary = occupancy_service.get_occupancy_summary(db)
    rooms = occupancy_service.room_board(db)
    headers = [
        "Room",
        "Status",
        "Patient",
        "Registration",
        "Check-in",
        "Ward / Clinic",
        "Officer",
        "Inspected",
        "Remarks",
    ]
    rows = []
    for room in rooms:
        stay = occupancy_service.current_occupant(room)
        status = occupancy_service.occupancy_status(room).value
        rows.append(
            [
                room.room_number,
                status,
                stay.patient.name if stay and stay.patient else "",
                stay.patient.registration_no if stay and stay.patient else "",
                stay.check_in_date.isoformat() if stay else "",
                stay.patient.ward_clinic.name if stay and stay.patient and stay.patient.ward_clinic else "",
                stay.officer.name if stay and stay.officer else "",
                "Yes" if stay and stay.room_inspected else ("No" if stay else ""),
                (stay.remarks if stay and stay.remarks else room.notes) or "",
            ]
        )
    content = to_excel_table(
        "Daily Room Occupancy Board",
        f"Occupancy Rate {summary['occupancy_rate']}% · {date.today().isoformat()}",
        headers,
        rows,
        summary=[
            ("total_rooms", summary["total_rooms"]),
            ("occupied_rooms", summary["occupied_rooms"]),
            ("vacant_rooms", summary["vacant_rooms"]),
            ("maintenance_rooms", summary["maintenance_rooms"]),
            ("occupancy_rate", f"{summary['occupancy_rate']}%"),
            ("todays_check_ins", summary["todays_check_ins"]),
            ("todays_check_outs", summary["todays_check_outs"]),
            ("waiting_list_open", summary["waiting_list_open"]),
        ],
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="RMH-HCTM-UKM-room-board.xlsx"'},
    )


@router.get("/api/rooms/{room_id}", response_model=RoomOut)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    rooms = {room.id: room for room in occupancy_service.room_board(db)}
    room = rooms.get(room_id)
    if room is None:
        raise NotFoundError("Room not found")
    return _serialize_room(room)


@router.get("/api/stays", response_model=list[StayListOut])
def list_stays(
    room_id: int | None = None,
    patient_id: int | None = None,
    open_only: bool = False,
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    return [
        _serialize_stay(stay)
        for stay in occupancy_service.list_stays(
            db, room_id=room_id, patient_id=patient_id, open_only=open_only
        )
    ]


@router.get("/api/stays/{stay_id}", response_model=StayListOut)
def get_stay(
    stay_id: int,
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    return _serialize_stay(occupancy_service.get_stay(db, stay_id))


@router.post("/api/rooms", response_model=RoomOut, status_code=201)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    if db.scalar(select(Room).where(Room.room_number == payload.room_number.strip())):
        raise ConflictError("Room number must be unique")
    room = Room(room_number=payload.room_number.strip(), status=payload.status, notes=payload.notes)
    db.add(room)
    db.flush()
    write_audit(
        db,
        user_id=actor.id,
        entity="Room",
        entity_id=room.id,
        action=AuditAction.CREATE,
        after={"room_number": room.room_number, "status": room.status.value},
    )
    db.commit()
    db.refresh(room)
    return _serialize_room(room)


@router.patch("/api/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Session = Depends(get_db),
    actor: User = require_permission("rooms:write"),
):
    room = db.get(Room, room_id)
    if room is None:
        raise NotFoundError("Room not found")
    occupant = occupancy_service.current_occupant(room)
    before = {"room_number": room.room_number, "status": room.status.value, "notes": room.notes}
    data = payload.model_dump(exclude_unset=True)
    if "room_number" in data:
        if not has_permission(actor.role, "settings:manage"):
            raise ForbiddenError("Only administrators can rename rooms")
        clash = db.scalar(
            select(Room).where(Room.room_number == data["room_number"].strip(), Room.id != room.id)
        )
        if clash:
            raise ConflictError("Room number must be unique")
        data["room_number"] = data["room_number"].strip()
    if data.get("status") == RoomStatus.MAINTENANCE and occupant:
        raise ConflictError("Cannot place an occupied room into maintenance. Check the occupant out first.")
    if data.get("status") == RoomStatus.VACANT and occupant:
        raise ConflictError("Cannot mark an occupied room vacant. Check the occupant out first.")
    if data.get("status") == RoomStatus.OCCUPIED and not occupant:
        raise ConflictError("Use check-in to occupy a room. Occupancy cannot be set manually.")
    for key, value in data.items():
        setattr(room, key, value)
    write_audit(
        db,
        user_id=actor.id,
        entity="Room",
        entity_id=room.id,
        action=AuditAction.UPDATE,
        before=before,
        after={"room_number": room.room_number, "status": room.status.value, "notes": room.notes},
    )
    db.commit()
    db.refresh(room)
    return _serialize_room(room)


@router.delete("/api/rooms/{room_id}", status_code=204)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    actor: User = require_permission("settings:manage"),
):
    room = db.get(Room, room_id)
    if room is None:
        raise NotFoundError("Room not found")
    if occupancy_service.current_occupant(room):
        raise ConflictError("Cannot delete an occupied room")
    if db.scalar(select(RoomStay.id).where(RoomStay.room_id == room_id).limit(1)):
        raise ConflictError("Cannot delete a room that has stay history")
    write_audit(
        db,
        user_id=actor.id,
        entity="Room",
        entity_id=room.id,
        action=AuditAction.DELETE,
        before={"room_number": room.room_number, "status": room.status.value},
    )
    db.delete(room)
    db.commit()


@router.post("/api/rooms/{room_id}/check-in", response_model=StayOut)
def check_in(
    room_id: int,
    payload: CheckInRequest,
    db: Session = Depends(get_db),
    actor: User = require_permission("stays:check_in"),
):
    stay = occupancy_service.check_in(
        db,
        room_id=room_id,
        patient_id=payload.patient_id,
        officer_id=actor.id,
        hospital_admission_date=payload.hospital_admission_date,
        check_in_date=payload.check_in_date,
        room_inspected=payload.room_inspected,
        remarks=payload.remarks,
    )
    return StayOut.model_validate(stay)


@router.post("/api/stays/{stay_id}/check-out", response_model=StayOut)
def check_out(
    stay_id: int,
    payload: CheckOutRequest,
    db: Session = Depends(get_db),
    actor: User = require_permission("stays:check_out"),
):
    stay = occupancy_service.check_out(
        db,
        stay_id=stay_id,
        officer_id=actor.id,
        check_out_date=payload.check_out_date,
        remarks=payload.remarks,
    )
    return StayOut.model_validate(stay)


@router.get("/api/occupancy/summary", response_model=OccupancySummary)
def occupancy_summary(
    db: Session = Depends(get_db),
    _: User = require_permission("rooms:read"),
):
    return occupancy_service.get_occupancy_summary(db, date.today())
