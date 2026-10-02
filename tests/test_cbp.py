from datetime import datetime

from ge_appointment_finder import cbp


def test_slot_from_api_parses_and_orders_by_start():
    later = cbp.Slot.from_api({"locationId": 5023, "startTimestamp": "2026-10-02T18:40"})
    earlier = cbp.Slot.from_api({"locationId": 7680, "startTimestamp": "2026-10-02T18:00"})
    assert earlier < later
    assert earlier.start == datetime(2026, 10, 2, 18, 0)
    assert earlier.key == "7680|2026-10-02T18:00"


def test_fetch_slots_drops_inactive(monkeypatch):
    payload = [
        {"locationId": 1, "startTimestamp": "2026-01-01T09:00", "active": True},
        {"locationId": 1, "startTimestamp": "2026-01-01T10:00", "active": False},
    ]
    monkeypatch.setattr(cbp, "_get_json", lambda url, **kw: payload)
    assert [s.start.hour for s in cbp.fetch_slots(1)] == [9]


def test_fetch_slots_empty_on_failure(monkeypatch):
    monkeypatch.setattr(cbp, "_get_json", lambda url, **kw: None)
    assert cbp.fetch_slots(1) == []


def test_fetch_locations_sorted_by_id(monkeypatch):
    payload = [
        {"id": 20, "name": "B", "shortName": "B", "city": "x", "state": "OH"},
        {"id": 10, "name": "A", "shortName": "", "city": None, "state": "MI"},
    ]
    monkeypatch.setattr(cbp, "_get_json", lambda url, **kw: payload)
    locs = cbp.fetch_locations()
    assert [loc.id for loc in locs] == [10, 20]
    assert locs[0] == cbp.Location(id=10, name="A", city="", state="MI")
