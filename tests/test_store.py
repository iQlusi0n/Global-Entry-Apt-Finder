from datetime import datetime

from ge_appointment_finder.cbp import Slot
from ge_appointment_finder.store import SeenSlots


def slot(hour: int, location_id: int = 1) -> Slot:
    return Slot(start=datetime(2026, 1, 1, hour), location_id=location_id)


def test_new_reports_each_slot_once_and_persists(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenSlots(path)
    assert store.new([slot(9), slot(10)]) == [slot(9), slot(10)]
    assert store.new([slot(9), slot(11)]) == [slot(11)]

    reloaded = SeenSlots(path)
    assert reloaded.new([slot(9), slot(10), slot(11), slot(12)]) == [slot(12)]


def test_same_time_different_location_is_distinct(tmp_path):
    store = SeenSlots(tmp_path / "seen.json")
    store.new([slot(9, location_id=1)])
    assert store.new([slot(9, location_id=2)]) == [slot(9, location_id=2)]


def test_no_write_when_nothing_new(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenSlots(path)
    assert store.new([]) == []
    assert not path.exists()
