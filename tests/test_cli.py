from datetime import date, datetime

import pytest

from ge_apt_finder import cbp, cli
from ge_apt_finder.store import SeenSlots

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


def test_watch_config_from_env(monkeypatch, tmp_path):
    for var in ("GE_LOCATIONS", "GE_BEFORE", "GE_INTERVAL", "GE_STATE_FILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GE_LOCATIONS", "5023, 7680 16242")
    monkeypatch.setenv("GE_BEFORE", "2099-01-02")
    monkeypatch.setenv("GE_INTERVAL", "42")
    monkeypatch.setenv("GE_STATE_FILE", str(tmp_path / "s.json"))
    captured = {}
    monkeypatch.setattr(cli, "cmd_watch", lambda args: captured.update(vars(args)) or 0)

    assert cli.main(["watch"]) == 0
    assert captured["location"] == [5023, 7680, 16242]
    assert captured["before"] == date(2099, 1, 2)
    assert captured["interval"] == 42
    assert captured["state_file"] == tmp_path / "s.json"

    # Flags replace, not extend, the environment.
    assert cli.main(["watch", "-l", "1", "--interval", "7"]) == 0
    assert captured["location"] == [1]
    assert captured["interval"] == 7


def test_watch_requires_locations_from_flag_or_env(monkeypatch):
    monkeypatch.delenv("GE_LOCATIONS", raising=False)
    with pytest.raises(SystemExit):
        cli.main(["watch", "--once", "--no-notify"])


def test_watch_stops_cleanly_on_sigterm(monkeypatch, tmp_path):
    import os
    import signal

    monkeypatch.delenv("GE_LOCATIONS", raising=False)
    monkeypatch.setattr(cbp, "fetch_locations", lambda: [])
    monkeypatch.setattr(cbp, "fetch_slots", lambda lid, limit=10: [])
    monkeypatch.setattr(cli.time, "sleep", lambda s: os.kill(os.getpid(), signal.SIGTERM))
    previous = signal.getsignal(signal.SIGTERM)
    try:
        rc = cli.main(["watch", "-l", "1", "--no-notify", "--state-file", str(tmp_path / "s.json")])
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert rc == 0
