"""Bounded local episodic event store adapted from the old SQLite store pattern."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso, write_json_atomic


MAX_EVENTS = 256


class EpisodicStore:
    """Keeps a small bounded list of recent fabric events."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            write_json_atomic(self.path, [])

    def append_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.load_all()
        normalized = dict(payload)
        normalized.setdefault("created_utc", utc_now_iso())
        rows.append(normalized)
        rows = rows[-MAX_EVENTS:]
        write_json_atomic(self.path, rows)
        return normalized

    def load_all(self) -> list[dict[str, Any]]:
        raw = load_json_file(
            self.path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label="Episodic store",
        )
        if not isinstance(raw, list):
            write_json_atomic(self.path, [])
            return []
        return [item for item in raw if isinstance(item, dict)]

