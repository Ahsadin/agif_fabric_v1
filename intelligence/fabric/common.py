"""Shared helpers for the AGIF Phase 3 fabric foundation."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_ROOT = REPO_ROOT / "runtime_state" / "fabric"


@dataclass
class FabricError(Exception):
    """Fail-closed CLI error."""

    code: str
    message: str
    exit_code: int = 1

    def __str__(self) -> str:
        return self.message


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def ensure_object(value: Any, field_name: str, *, code: str = "CONFIG_INVALID") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FabricError(code, f"{field_name} must be an object.")
    return value


def ensure_non_empty_string(value: Any, field_name: str, *, code: str = "CONFIG_INVALID") -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise FabricError(code, f"{field_name} must be a non-empty string.")
    return value.strip()


def ensure_positive_int(value: Any, field_name: str, *, code: str = "CONFIG_INVALID") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FabricError(code, f"{field_name} must be a positive integer.")
    return int(value)


def ensure_numeric(value: Any, field_name: str, *, code: str = "CONFIG_INVALID") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FabricError(code, f"{field_name} must be numeric.")
    return float(value)


def ensure_list_of_strings(value: Any, field_name: str, *, code: str = "CONFIG_INVALID") -> list[str]:
    if not isinstance(value, list) or len(value) == 0:
        raise FabricError(code, f"{field_name} must be a non-empty array of strings.")
    output: list[str] = []
    for index, item in enumerate(value):
        output.append(ensure_non_empty_string(item, f"{field_name}[{index}]", code=code))
    return output


def ensure_exact_keys(value: dict[str, Any], required_keys: Iterable[str], field_name: str, *, code: str) -> None:
    actual = set(value.keys())
    required = set(required_keys)
    missing = sorted(required - actual)
    extra = sorted(actual - required)
    if missing or extra:
        pieces: list[str] = []
        if missing:
            pieces.append(f"missing keys: {','.join(missing)}")
        if extra:
            pieces.append(f"extra keys: {','.join(extra)}")
        raise FabricError(code, f"{field_name} keys invalid ({'; '.join(pieces)}).")


def load_json_file(path: Path, *, not_found_code: str, invalid_code: str, label: str) -> Any:
    if not path.exists():
        raise FabricError(not_found_code, f"{label} not found: {path}")
    if not path.is_file():
        raise FabricError(invalid_code, f"{label} must be a file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise FabricError(invalid_code, f"{label} JSON invalid at line {err.lineno} column {err.colno}.") from err
    except OSError as err:
        raise FabricError(invalid_code, f"{label} could not be read: {err}.") from err


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def repo_relative(path: Path) -> str:
    target = path.resolve()
    try:
        return str(target.relative_to(REPO_ROOT))
    except ValueError:
        return str(target)


def resolve_state_root() -> Path:
    override = os.environ.get("AGIF_FABRIC_STATE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_STATE_ROOT
