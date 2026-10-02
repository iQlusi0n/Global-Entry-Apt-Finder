"""Persistent record of slots that have already been reported."""

from __future__ import annotations

import json
from pathlib import Path

from ge_appointment_finder.cbp import Slot


class SeenSlots:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._keys: set[str] = set()
        if path.exists():
            self._keys = set(json.loads(path.read_text()))

    def new(self, slots: list[Slot]) -> list[Slot]:
        """Return the subset of *slots* not seen before, and remember them."""
        fresh = [slot for slot in slots if slot.key not in self._keys]
        if fresh:
            self._keys.update(slot.key for slot in fresh)
            self._save()
        return fresh

    def _save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(sorted(self._keys)))
        tmp.replace(self.path)
