"""Fail-closed bounded suggestions store adapted from the old JSON suggestions store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, write_json_atomic


MAX_ACTIVE_SUGGESTIONS = 50


class SuggestionsStore:
    """Stores bounded local suggestions for later phases."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            write_json_atomic(self.path, [])

    def load_all(self) -> list[dict[str, Any]]:
        raw = load_json_file(
            self.path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label="Suggestions store",
        )
        if not isinstance(raw, list):
            write_json_atomic(self.path, [])
            return []
        return [item for item in raw if isinstance(item, dict)]

    def count_active(self) -> int:
        return len([item for item in self.load_all() if bool(item.get("dismissed", False)) is False])

    def upsert_suggestions(self, suggestions: list[dict[str, Any]]) -> dict[str, Any]:
        current = {str(item.get("id")): item for item in self.load_all()}
        inserted = 0
        updated = 0
        for item in suggestions:
            item_id = str(item.get("id", ""))
            if item_id == "":
                continue
            if item_id in current:
                updated += 1
            else:
                inserted += 1
            current[item_id] = dict(item)

        rows = list(current.values())
        rows.sort(key=lambda entry: str(entry.get("id", "")))
        active_rows = [row for row in rows if bool(row.get("dismissed", False)) is False]
        if len(active_rows) > MAX_ACTIVE_SUGGESTIONS:
            overflow = len(active_rows) - MAX_ACTIVE_SUGGESTIONS
            for row in active_rows[:overflow]:
                row["dismissed"] = True

        write_json_atomic(self.path, rows)
        return {
            "inserted": inserted,
            "updated": updated,
            "active_count": self.count_active(),
        }

