import socket

from ge_apt_finder import systemd


def test_notify_noop_without_socket(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert systemd.notify("READY=1") is False


def test_notify_sends_joined_states_to_socket(tmp_path, monkeypatch):
    path = tmp_path / "notify.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(path))
        server.settimeout(2)
        monkeypatch.setenv("NOTIFY_SOCKET", str(path))
        assert systemd.notify("READY=1", "STATUS=ok") is True
        assert server.recv(1024) == b"READY=1\nSTATUS=ok"


def test_under_journal(monkeypatch):
    monkeypatch.delenv("JOURNAL_STREAM", raising=False)
    assert systemd.under_journal() is False
    monkeypatch.setenv("JOURNAL_STREAM", "9:12345")
    assert systemd.under_journal() is True
