from datetime import date, timedelta

from app.models.enums import RoomStatus
from app.models.room import Room, RoomStay, WaitlistEntry
from app.services.occupancy import occupancy_rate, occupancy_status


def test_waitlist_days_property():
    entry = WaitlistEntry(patient_id=1, added_date=date.today() - timedelta(days=3))
    assert entry.days_waited == 3
    entry.resolved_date = entry.added_date + timedelta(days=1)
    assert entry.days_waited == 1


def test_occupancy_formula_matches_prd():
    assert occupancy_rate(0, 18) == 0
    assert occupancy_rate(9, 18) == 50.0
    assert occupancy_rate(18, 18) == 100.0
    assert occupancy_rate(1, 0) == 0.0


def test_occupancy_status_follows_open_stay_not_stale_flag():
    room = Room(room_number="01", status=RoomStatus.VACANT)
    room.stays = []
    assert occupancy_status(room) == RoomStatus.VACANT
    stay = RoomStay(patient_id=1, room_id=1, check_in_date=date.today())
    room.stays = [stay]
    room.status = RoomStatus.VACANT
    assert occupancy_status(room) == RoomStatus.OCCUPIED
    room.stays = []
    room.status = RoomStatus.OCCUPIED
    assert occupancy_status(room) == RoomStatus.VACANT
    room.status = RoomStatus.MAINTENANCE
    assert occupancy_status(room) == RoomStatus.MAINTENANCE
