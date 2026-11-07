"""Centralized, persistent Owner/Sudo/Uploader role management."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

OWNER_ID = 0
DATA_DIR = Path("data")
SUDO_FILE = DATA_DIR / "sudo_users.json"
UPLOADER_FILE = DATA_DIR / "uploader_users.json"


def configure(owner_id: int, data_dir: str | Path = "data") -> None:
    global OWNER_ID, DATA_DIR, SUDO_FILE, UPLOADER_FILE
    OWNER_ID = int(owner_id)
    DATA_DIR = Path(data_dir)
    SUDO_FILE = DATA_DIR / "sudo_users.json"
    UPLOADER_FILE = DATA_DIR / "uploader_users.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path) -> list[int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    values = set()
    for value in raw:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0 and number != OWNER_ID:
            values.add(number)
    return sorted(values)


def _save(path: Path, values: Iterable[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = set()
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0 and number != OWNER_ID:
            normalized.add(number)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(sorted(normalized), indent=2), encoding="utf-8")
    temp.replace(path)


def load_sudo() -> list[int]:
    return _load(SUDO_FILE)


def save_sudo(values: Iterable[int]) -> None:
    _save(SUDO_FILE, values)


def load_uploaders() -> list[int]:
    return _load(UPLOADER_FILE)


def save_uploaders(values: Iterable[int]) -> None:
    _save(UPLOADER_FILE, values)


def is_owner(user_id: int) -> bool:
    try:
        return int(user_id) == OWNER_ID
    except (TypeError, ValueError):
        return False


def is_sudo(user_id: int) -> bool:
    try:
        return int(user_id) in set(load_sudo())
    except (TypeError, ValueError):
        return False


def is_uploader(user_id: int) -> bool:
    try:
        return int(user_id) in set(load_uploaders())
    except (TypeError, ValueError):
        return False


def role(user_id: int) -> str:
    if is_owner(user_id):
        return "owner"
    if is_sudo(user_id):
        return "sudo"
    if is_uploader(user_id):
        return "uploader"
    return "user"


def is_staff(user_id: int) -> bool:
    return role(user_id) in {"owner", "sudo", "uploader"}
