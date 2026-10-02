from datetime import date, datetime

import pytest

from ge_appointment_finder import cbp, cli
from ge_appointment_finder.store import SeenSlots

# Far enough in the future that SeenSlots never prunes them as past.
YEAR = 2099


def slot(day: int, hour: int = 9, location_id: int = 1) -> cbp.Slot:
    return cbp.Slot(start=datetime(YEAR, 3, day, hour), location_id=location_id)


class FakeNotifier:
    def __init__(self):
        self.sent: list[tuple[str, str | None]] = []

    def send(self, message, *, title=None):
        self.sent.append((message, title))


def test_format_message_sorted_with_names_and_fallback():
    msg = cli.format_message([slot(2, location_id=7), slot(1)], {1: "Detroit"})
    lines = msg.splitlines()
    assert lines[0].startswith("Detroit")
    assert lines[0].endswith(f"{datetime(YEAR, 3, 1):%a} Mar 01 09:00")
    assert lines[1].startswith("7 ")


def test_check_once_filters_by_before_and_notifies_only_new(tmp_path, monkeypatch):
    responses = {1: [slot(1), slot(5)], 2: [slot(2, location_id=2)]}
    monkeypatch.setattr(cbp, "fetch_slots", lambda lid, limit=10: responses[lid])
    seen = SeenSlots(tmp_path / "seen.json")
    notifier = FakeNotifier()
    names = {1: "A", 2: "B"}

    fresh = cli.check_once([1, 2], names, date(YEAR, 3, 3), seen, notifier)
    assert fresh == [slot(1), slot(2, location_id=2)]
    assert len(notifier.sent) == 1
    assert notifier.sent[0][0].splitlines()[0].startswith("A")

    assert cli.check_once([1, 2], names, date(YEAR, 3, 3), seen, notifier) == []
    assert len(notifier.sent) == 1


def test_check_once_without_before_keeps_everything(tmp_path, monkeypatch):
    monkeypatch.setattr(cbp, "fetch_slots", lambda lid, limit=10: [slot(1), slot(30)])
    fresh = cli.check_once([1], {1: "A"}, None, SeenSlots(tmp_path / "s.json"), None)
    assert fresh == [slot(1), slot(30)]


def test_check_once_retries_notification_next_poll_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(cbp, "fetch_slots", lambda lid, limit=10: [slot(1)])
    seen = SeenSlots(tmp_path / "seen.json")
    notifier = FakeNotifier()
    attempts = []

    def flaky_send(message, *, title=None):
        attempts.append(message)
        if len(attempts) == 1:
            raise OSError("ntfy down")

    notifier.send = flaky_send
    assert cli.check_once([1], {1: "A"}, None, seen, notifier) == []
    assert cli.check_once([1], {1: "A"}, None, seen, notifier) == [slot(1)]
    assert cli.check_once([1], {1: "A"}, None, seen, notifier) == []
    assert len(attempts) == 2


def test_watch_requires_ntfy_url_unless_no_notify(monkeypatch, caplog):
    monkeypatch.delenv("NTFY_URL", raising=False)
    assert cli.main(["watch", "-l", "1", "--once"]) == 2
    assert "NTFY_URL" in caplog.text


def test_parser_rejects_bad_date():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["watch", "-l", "1", "--before", "not-a-date"])
