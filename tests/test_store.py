from datetime import datetime

from ge_apt_finder.cbp import Slot
from ge_apt_finder.store import SeenSlots

NOW = datetime(2026, 1, 1, 0, 0)


def slot(hour: int, location_id: int = 1, day: int = 1) -> Slot:
    return Slot(start=datetime(2026, 1, day, hour), location_id=location_id)


def test_remember_persists_and_unseen_excludes_them(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenSlots(path)
    assert store.unseen([slot(9), slot(10)]) == [slot(9), slot(10)]
    store.remember([slot(9), slot(10)], now=NOW)
    assert store.unseen([slot(9), slot(11)]) == [slot(11)]

    reloaded = SeenSlots(path)
    assert reloaded.unseen([slot(9), slot(10), slot(11)]) == [slot(11)]


def test_unseen_does_not_remember(tmp_path):
    store = SeenSlots(tmp_path / "seen.json")
    store.unseen([slot(9)])
    assert store.unseen([slot(9)]) == [slot(9)]


def test_same_time_different_location_is_distinct(tmp_path):
    store = SeenSlots(tmp_path / "seen.json")
    store.remember([slot(9, location_id=1)], now=NOW)
    assert store.unseen([slot(9, location_id=2)]) == [slot(9, location_id=2)]


def test_remember_prunes_slots_in_the_past(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenSlots(path)
    store.remember([slot(9, day=1), slot(9, day=3)], now=NOW)
    store.remember([], now=datetime(2026, 1, 2))
    assert SeenSlots(path).unseen([slot(9, day=1), slot(9, day=3)]) == [slot(9, day=1)]
