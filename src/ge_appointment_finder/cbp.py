"""Client for the CBP Trusted Traveler Programs scheduler API."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

BASE_URL = "https://ttp.cbp.dhs.gov/schedulerapi"
GLOBAL_ENTRY_SERVICE = "Global Entry"


@dataclass(frozen=True, slots=True)
class Location:
    id: int
    name: str
    city: str
    state: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Location:
        return cls(
            id=int(data["id"]),
            name=str(data["shortName"] or data["name"]),
            city=str(data.get("city") or ""),
            state=str(data.get("state") or ""),
        )


@dataclass(frozen=True, slots=True, order=True)
class Slot:
    start: datetime
    location_id: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Slot:
        return cls(
            start=datetime.fromisoformat(data["startTimestamp"]),
            location_id=int(data["locationId"]),
        )

    @property
    def key(self) -> str:
        """Stable identity used to remember slots across runs."""
        return f"{self.location_id}|{self.start.isoformat(timespec='minutes')}"


def _get_json(
    url: str,
    *,
    timeout: float = 15,
    retries: int = 3,
    backoff_factor: float = 2,
) -> Any | None:
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            log.warning("%s returned HTTP %s", url, e.code)
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("attempt %d/%d failed for %s: %s", attempt, retries, url, e)
            if attempt < retries:
                time.sleep(delay)
                delay *= backoff_factor
    log.error("giving up on %s after %d attempts", url, retries)
    return None


def fetch_locations(service: str = GLOBAL_ENTRY_SERVICE) -> list[Location]:
    """Return all operational, publicly bookable enrollment centers for *service*."""
    query = urllib.parse.urlencode(
        {
            "temporary": "false",
            "inviteOnly": "false",
            "operational": "true",
            "serviceName": service,
        }
    )
    data = _get_json(f"{BASE_URL}/locations/?{query}")
    if not data:
        return []
    return sorted((Location.from_api(item) for item in data), key=lambda loc: loc.id)


def fetch_slots(location_id: int, limit: int = 10) -> list[Slot]:
    """Return the soonest open slots at one enrollment center."""
    query = urllib.parse.urlencode(
        {"orderBy": "soonest", "limit": limit, "locationId": location_id, "minimum": 1}
    )
    data = _get_json(f"{BASE_URL}/slots?{query}")
    if not data:
        return []
    return [Slot.from_api(item) for item in data if item.get("active", True)]
