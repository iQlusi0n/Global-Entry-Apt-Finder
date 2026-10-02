"""Push notifications via an ntfy topic."""

from __future__ import annotations

import base64
import logging
import os
import urllib.request
from dataclasses import dataclass

log = logging.getLogger(__name__)


class NotifierConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Notifier:
    url: str
    user: str | None = None
    password: str | None = None
    token: str | None = None

    @classmethod
    def from_env(cls) -> Notifier:
        """Build from ``NTFY_URL`` plus optional ``NTFY_TOKEN`` or ``NTFY_USER``/``NTFY_PASS``."""
        url = os.environ.get("NTFY_URL")
        if not url:
            raise NotifierConfigError("NTFY_URL is not set")
        return cls(
            url=url,
            user=os.environ.get("NTFY_USER"),
            password=os.environ.get("NTFY_PASS"),
            token=os.environ.get("NTFY_TOKEN"),
        )

    def _auth_header(self) -> str | None:
        if self.token:
            return f"Bearer {self.token}"
        if self.user and self.password is not None:
            creds = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            return f"Basic {creds}"
        return None

    def send(self, message: str, *, title: str | None = None, timeout: float = 15) -> None:
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if title:
            headers["Title"] = title
        if auth := self._auth_header():
            headers["Authorization"] = auth
        req = urllib.request.Request(
            self.url, data=message.encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout):
            pass
        log.info("push notification sent to %s", self.url)
