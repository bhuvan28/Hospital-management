from __future__ import annotations

from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError
from app.models.enums import AuditAction, RoomStatus
from app.models.patient import Patient
from app.models.room import Room, RoomStay, WaitlistEntry
from app.services.audit import write_audit


def occupancy_rate(occupied: int, total: int) -> float:
    """occupied rooms / total rooms * 100. Never accept a user-supplied percentage."""
    if total <= 0:
        return 0.0
    return round((occupied / total) * 100, 2)


def _active_stay_query(room_id: int) -> Select:
    return select(RoomStay).where(RoomStay.room_id == room_id, RoomStay.check_out_date.is_(None))


def get_occupancy_summary(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    total = db.scalar(select(func.count(Room.id))) or 0
    occupied = db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.OCCUPIED)) or 0
    vacant = db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.VACANT)) or 0
    maintenance = db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.MAINTENANCE)) or 0
    todays_check_ins = (
        db.scalar(select(func.count(RoomStay.id)).where(RoomStay.check_in_date == today)) or 0
    )
    todays_check_outs = (
        db.scalar(
            select(func.count(RoomStay.id)).where(RoomStay.check_out_date == today)
        )
        or 0
    )
    waiting = (
        db.scalar(select(func.count(WaitlistEntry.id)).where(WaitlistEntry.resolved_date.is_(None)))
        or 0
    )
    return {
        "total_rooms": total,
        "occupied_rooms": occupied,
        "vacant_rooms": vacant,
        "maintenance_rooms": maintenance,
        "occupancy_rate": occupancy_rate(occupied, total),
        "todays_check_ins": todays_check_ins,
        "todays_check_outs": todays_check_outs,
        "waiting_list_open": waiting,
    }


def room_board(db: Session) -> list[Room]:
    return list(
        db.scalars(
            select(Room).options(
                joinedload(Room.stays).joinedload(RoomStay.patient).joinedload(Patient.ward_clinic),
                joinedload(Room.stays).joinedload(RoomStay.officer),
            ).order_by(Room.room_number)
        ).unique().all()
    )


def current_occupant(room: Room) -> RoomStay | None:
    for stay in room.stays:
        if stay.check_out_date is None:
            return stay
    return None


def check_in(
    db: Session,
    *,
    room_id: int,
    patient_id: int,
    officer_id: int,
    hospital_admission_date: date | None,
    check_in_date: date | None,
    room_inspected: bool,
    remarks: str | None,
) -> RoomStay:
    today = date.today()
    check_in_date = check_in_date or today

    room = db.execute(select(Room).where(Room.id == room_id).with_for_update()).scalar_one_or_none()
    if room is None:
        raise NotFoundError("Room not found")
    if room.status == RoomStatus.MAINTENANCE:
        raise ConflictError("Room is under maintenance and cannot be checked in")
    if room.status != RoomStatus.VACANT:
        raise ConflictError("Check-in is only allowed when the room is vacant")

    existing = db.execute(_active_stay_query(room_id).with_for_update()).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Room already has an active occupant")

    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Patient not found. A stay must reference an existing patient.")

    active_patient_stay = db.scalar(
        select(RoomStay).where(RoomStay.patient_id == patient_id, RoomStay.check_out_date.is_(None))
    )
    if active_patient_stay is not None:
        raise ConflictError("Patient already occupies a room")

    stay = RoomStay(
        patient_id=patient_id,
        room_id=room_id,
        hospital_admission_date=hospital_admission_date,
        check_in_date=check_in_date,
        officer_on_duty_id=officer_id,
        room_inspected=room_inspected,
        remarks=remarks,
    )
    room.status = RoomStatus.OCCUPIED
    db.add(stay)
    db.flush()

    open_wait = db.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.patient_id == patient_id,
            WaitlistEntry.resolved_date.is_(None),
        )
    )
    if open_wait:
        open_wait.resolved_date = check_in_date

    write_audit(
        db,
        user_id=officer_id,
        entity="RoomStay",
        entity_id=stay.id,
        action=AuditAction.CHECK_IN,
        after={
            "patient_id": patient_id,
            "room_id": room_id,
            "check_in_date": check_in_date.isoformat(),
            "room_inspected": room_inspected,
            "remarks": remarks,
        },
    )
    write_audit(
        db,
        user_id=officer_id,
        entity="Room",
        entity_id=room.id,
        action=AuditAction.UPDATE,
        before={"status": RoomStatus.VACANT.value},
        after={"status": RoomStatus.OCCUPIED.value},
    )
    db.commit()
    db.refresh(stay)
    return stay


def check_out(
    db: Session,
    *,
    stay_id: int,
    officer_id: int,
    check_out_date: date | None,
    remarks: str | None,
) -> RoomStay:
    stay = db.execute(select(RoomStay).where(RoomStay.id == stay_id).with_for_update()).scalar_one_or_none()
    if stay is None:
        raise NotFoundError("Stay not found")
    if stay.check_out_date is not None:
        raise ConflictError("Stay is already checked out")

    checkout = check_out_date or date.today()
    if checkout < stay.check_in_date:
        raise ConflictError("Check-out cannot occur before check-in")

    room = db.execute(select(Room).where(Room.id == stay.room_id).with_for_update()).scalar_one()
    before = {
        "check_out_date": None,
        "remarks": stay.remarks,
        "room_status": room.status.value,
    }
    stay.check_out_date = checkout
    if remarks:
        stay.remarks = remarks
    room.status = RoomStatus.VACANT
    write_audit(
        db,
        user_id=officer_id,
        entity="RoomStay",
        entity_id=stay.id,
        action=AuditAction.CHECK_OUT,
        before=before,
        after={
            "check_out_date": checkout.isoformat(),
            "remarks": stay.remarks,
            "room_status": RoomStatus.VACANT.value,
        },
    )
    write_audit(
        db,
        user_id=officer_id,
        entity="Room",
        entity_id=room.id,
        action=AuditAction.UPDATE,
        before={"status": RoomStatus.OCCUPIED.value},
        after={"status": RoomStatus.VACANT.value},
    )
    db.commit()
    db.refresh(stay)
    return stay


def days_waited(entry: WaitlistEntry, as_of: date | None = None) -> int:
    end = entry.resolved_date or as_of or date.today()
    return max((end - entry.added_date).days, 0)


def daily_occupancy_series(
    db: Session,
    start: date,
    end: date,
) -> list[dict]:
    rooms_total = db.scalar(select(func.count(Room.id))) or 0
    stays = list(
        db.scalars(
            select(RoomStay).where(
                RoomStay.check_in_date <= end,
                or_(RoomStay.check_out_date.is_(None), RoomStay.check_out_date >= start),
            )
        ).all()
    )
    series = []
    cursor = start
    while cursor <= end:
        occupied_room_ids = set()
        for stay in stays:
            stay_end = stay.check_out_date or end
            if stay.check_in_date <= cursor <= stay_end:
                # A checkout on `cursor` means the room is free that night.
                if stay.check_out_date == cursor:
                    continue
                occupied_room_ids.add(stay.room_id)
        occupied = len(occupied_room_ids)
        series.append(
            {
                "date": cursor.isoformat(),
                "occupied_rooms": occupied,
                "total_rooms": rooms_total,
                "occupancy_rate": occupancy_rate(occupied, rooms_total),
            }
        )
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return series
