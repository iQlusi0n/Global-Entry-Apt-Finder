"""Persistent record of slots that have already been reported."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ge_appointment_finder.cbp import Slot


class SeenSlots:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._keys: set[str] = set()
        if path.exists():
            self._keys = set(json.loads(path.read_text()))

    def unseen(self, slots: list[Slot]) -> list[Slot]:
        """Return the subset of *slots* not yet remembered, without remembering them."""
        return [slot for slot in slots if slot.key not in self._keys]

    def remember(self, slots: list[Slot], *, now: datetime | None = None) -> None:
        """Persist *slots* as reported, dropping any remembered slot already in the past."""
        self._keys.update(slot.key for slot in slots)
        cutoff = (now or datetime.now()).isoformat(timespec="minutes")
        self._keys = {key for key in self._keys if key.partition("|")[2] >= cutoff}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(sorted(self._keys)))
        tmp.replace(self.path)
