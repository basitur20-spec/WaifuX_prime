"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = (os.getenv("BOT_TOKEN") or os.getenv("Bot_Token") or "").strip()
        owner_raw = (os.getenv("OWNER_ID") or "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is missing. Add it to Replit Secrets.")
        if not owner_raw:
            raise RuntimeError("OWNER_ID is missing. Add it to Replit Secrets.")
        try:
            owner_id = int(owner_raw)
        except ValueError as exc:
            raise RuntimeError("OWNER_ID must be a numeric Telegram user ID.") from exc
        if owner_id <= 0:
            raise RuntimeError("OWNER_ID must be a positive Telegram user ID.")
        return cls(bot_token=token, owner_id=owner_id)
