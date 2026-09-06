from datetime import date, timedelta

from app.models.room import WaitlistEntry
from app.services.occupancy import occupancy_rate


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
