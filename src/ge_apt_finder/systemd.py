"""Minimal systemd integration: sd_notify(3) and journal detection, stdlib only."""

from __future__ import annotations

import os
import socket


def under_journal() -> bool:
    """True when stderr is connected to journald (systemd sets ``JOURNAL_STREAM``)."""
    return "JOURNAL_STREAM" in os.environ


def notify(*states: str) -> bool:
    """Send ``READY=1``/``WATCHDOG=1``/``STATUS=...`` to systemd. No-op outside systemd."""
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return False
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.connect(address)
        sock.sendall("\n".join(states).encode())
    return True
