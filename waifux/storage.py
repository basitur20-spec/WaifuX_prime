"""Shared SQLite persistence for WaifuX Prime.

Uses the existing balance_system.db so cash, diamonds, waifus and ownership
can be changed inside one SQLite transaction. Existing tables are preserved.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DATA_DIR = Path(os.getenv("WAIFUX_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "balance_system.db"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=20000")
    try:
        yield con
    finally:
        con.close()


def raw_connect() -> sqlite3.Connection:
    """Return a manually managed connection for legacy-style try/finally blocks."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=20000")
    return con


def init_db() -> None:
    with connect() as con:
        con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id INTEGER PRIMARY KEY,
            cash INTEGER NOT NULL DEFAULT 0 CHECK(cash >= 0),
            diamonds INTEGER NOT NULL DEFAULT 0 CHECK(diamonds >= 0)
        );
        CREATE TABLE IF NOT EXISTS waifus (
            waifu_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            anime TEXT NOT NULL,
            rarity TEXT NOT NULL,
            price INTEGER NOT NULL CHECK(price > 0),
            image_file_id TEXT NOT NULL,
            uploader_id INTEGER NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]',
            created_at INTEGER NOT NULL,
            deleted_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_waifus_name ON waifus(name COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_waifus_rarity ON waifus(rarity);
        CREATE INDEX IF NOT EXISTS idx_waifus_anime ON waifus(anime COLLATE NOCASE);
        CREATE TABLE IF NOT EXISTS user_waifus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            waifu_id TEXT NOT NULL REFERENCES waifus(waifu_id),
            obtained_at INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'unknown',
            is_favorite INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_user_waifus_user ON user_waifus(user_id);
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            profile_photo TEXT,
            profile_waifu_id TEXT,
            display_mode TEXT NOT NULL DEFAULT 'default',
            display_value TEXT,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY(user_id, action)
        );
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            spawn_interval INTEGER NOT NULL DEFAULT 30,
            next_spawn_at INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS active_spawns (
            chat_id INTEGER PRIMARY KEY,
            waifu_id TEXT NOT NULL REFERENCES waifus(waifu_id),
            spawned_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rarity_settings (
            rarity TEXT PRIMARY KEY,
            spawn_enabled INTEGER NOT NULL DEFAULT 1,
            sell_percent REAL NOT NULL DEFAULT 50
        );
        CREATE TABLE IF NOT EXISTS market_refreshes (
            user_id INTEGER NOT NULL,
            day_key TEXT NOT NULL,
            refreshes INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, day_key)
        );
        CREATE TABLE IF NOT EXISTS market_daily_purchases (
            user_id INTEGER NOT NULL,
            day_key TEXT NOT NULL,
            purchases INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, day_key)
        );
        CREATE TABLE IF NOT EXISTS marketplace_slots (
            user_id INTEGER NOT NULL,
            slot INTEGER NOT NULL,
            waifu_id TEXT NOT NULL REFERENCES waifus(waifu_id),
            discount_percent INTEGER NOT NULL,
            day_key TEXT NOT NULL,
            purchased INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, slot, day_key)
        );
        CREATE TABLE IF NOT EXISTS auctions (
            auction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            waifu_id TEXT NOT NULL UNIQUE REFERENCES waifus(waifu_id),
            seller_id INTEGER NOT NULL,
            starting_bid INTEGER NOT NULL CHECK(starting_bid > 0),
            current_bid INTEGER NOT NULL CHECK(current_bid > 0),
            highest_bidder INTEGER,
            ends_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auction_bids (
            bid_id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_id INTEGER NOT NULL REFERENCES auctions(auction_id),
            bidder_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pending_actions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id TEXT PRIMARY KEY,
            actor_id INTEGER NOT NULL,
            target_id INTEGER,
            action TEXT NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            waifu_id TEXT,
            details TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bot_commands (
            command_name TEXT PRIMARY KEY,
            is_stopped INTEGER NOT NULL DEFAULT 0,
            stopped_by INTEGER,
            stopped_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS claim_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            reward_type TEXT NOT NULL,
            reward_value TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_claims (
            event_id INTEGER NOT NULL REFERENCES claim_events(event_id),
            user_id INTEGER NOT NULL,
            claimed_at INTEGER NOT NULL,
            PRIMARY KEY(event_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS chat_filters (
            chat_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            response TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            PRIMARY KEY(chat_id, keyword)
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_id INTEGER,
            details TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL
        );
        """)
        # Existing deployments may have an older, weaker balance table.
        columns = {row["name"] for row in con.execute("PRAGMA table_info(user_balance)")}
        if "cash" not in columns:
            con.execute("ALTER TABLE user_balance ADD COLUMN cash INTEGER NOT NULL DEFAULT 0")
        if "diamonds" not in columns:
            con.execute("ALTER TABLE user_balance ADD COLUMN diamonds INTEGER NOT NULL DEFAULT 0")
        profile_columns = {row["name"] for row in con.execute("PRAGMA table_info(user_profiles)")}
        if "display_mode" not in profile_columns:
            con.execute("ALTER TABLE user_profiles ADD COLUMN display_mode TEXT NOT NULL DEFAULT 'default'")
        if "display_value" not in profile_columns:
            con.execute("ALTER TABLE user_profiles ADD COLUMN display_value TEXT")


def now() -> int:
    return int(time.time())


def get_balance(user_id: int) -> tuple[int, int]:
    init_db()
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (int(user_id),))
        row = con.execute(
            "SELECT cash, diamonds FROM user_balance WHERE user_id=?", (int(user_id),)
        ).fetchone()
        return int(row["cash"]), int(row["diamonds"])


def change_balance(user_id: int, cash_delta: int = 0, diamond_delta: int = 0) -> tuple[int, int]:
    """Atomic balance change; negative results are rejected."""
    init_db()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (int(user_id),))
        row = con.execute(
            "SELECT cash, diamonds FROM user_balance WHERE user_id=?", (int(user_id),)
        ).fetchone()
        cash, diamonds = int(row["cash"]) + int(cash_delta), int(row["diamonds"]) + int(diamond_delta)
        if cash < 0 or diamonds < 0:
            con.rollback()
            raise ValueError("Insufficient balance.")
        con.execute(
            "UPDATE user_balance SET cash=?, diamonds=? WHERE user_id=?",
            (cash, diamonds, int(user_id)),
        )
        con.commit()
        return cash, diamonds


def get_waifu(waifu_id: str):
    init_db()
    with connect() as con:
        return con.execute(
            "SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL",
            (str(waifu_id),),
        ).fetchone()


def list_waifus(rarity: str | None = None, limit: int = 500):
    init_db()
    with connect() as con:
        if rarity:
            return con.execute(
                "SELECT * FROM waifus WHERE deleted_at IS NULL AND rarity=? ORDER BY waifu_id LIMIT ?",
                (rarity, int(limit)),
            ).fetchall()
        return con.execute(
            "SELECT * FROM waifus WHERE deleted_at IS NULL ORDER BY waifu_id LIMIT ?",
            (int(limit),),
        ).fetchall()


def add_waifu(waifu_id: str, name: str, anime: str, rarity: str, price: int,
              image_file_id: str, uploader_id: int, aliases: list[str] | None = None):
    init_db()
    wid = str(waifu_id)
    if len(wid) != 4 or not wid.isdigit():
        raise ValueError("Waifu ID must contain exactly four digits.")
    if not name.strip() or not anime.strip() or not image_file_id:
        raise ValueError("Name, anime and image are required.")
    if int(price) <= 0:
        raise ValueError("Price must be positive.")
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            """INSERT INTO waifus
            (waifu_id,name,anime,rarity,price,image_file_id,uploader_id,aliases,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (wid, name.strip(), anime.strip(), rarity, int(price), image_file_id,
             int(uploader_id), json.dumps(aliases or [], ensure_ascii=False), now()),
        )
        con.commit()


def add_to_collection(user_id: int, waifu_id: str, source: str = "unknown") -> bool:
    init_db()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        exists = con.execute(
            "SELECT 1 FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (str(waifu_id),)
        ).fetchone()
        if not exists:
            con.rollback()
            raise ValueError("Waifu not found.")
        con.execute(
            "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
            (int(user_id), str(waifu_id), now(), source),
        )
        con.commit()
        return True


def owned_waifu(user_id: int, waifu_id: str):
    init_db()
    with connect() as con:
        return con.execute(
            """SELECT w.*, uw.is_favorite, uw.obtained_at
            FROM user_waifus uw JOIN waifus w ON w.waifu_id=uw.waifu_id
            WHERE uw.user_id=? AND uw.waifu_id=? AND w.deleted_at IS NULL""",
            (int(user_id), str(waifu_id)),
        ).fetchone()


def collection(user_id: int, rarity: str | None = None, anime: str | None = None,
               name: str | None = None):
    init_db()
    sql = """SELECT w.*, uw.is_favorite, uw.obtained_at
             FROM user_waifus uw JOIN waifus w ON w.waifu_id=uw.waifu_id
             WHERE uw.user_id=? AND w.deleted_at IS NULL"""
    args: list[object] = [int(user_id)]
    for field, value in (("w.rarity", rarity), ("w.anime", anime), ("w.name", name)):
        if value:
            if field == "w.name":
                sql += " AND w.name LIKE ?"
                args.append(f"%{value}%")
            else:
                sql += f" AND {field}=?"
                args.append(value)
    sql += " ORDER BY uw.is_favorite DESC, w.anime COLLATE NOCASE, w.name COLLATE NOCASE"
    with connect() as con:
        return con.execute(sql, args).fetchall()


def remove_from_collection(user_id: int, waifu_id: str) -> bool:
    init_db()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            """DELETE FROM user_waifus WHERE id=(
                SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=?
                ORDER BY obtained_at LIMIT 1
            )""",
            (int(user_id), str(waifu_id)),
        )
        con.commit()
        return cur.rowcount == 1


def set_favorite(user_id: int, waifu_id: str | None) -> None:
    init_db()
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE user_waifus SET is_favorite=0 WHERE user_id=?", (int(user_id),))
        if waifu_id is not None:
            cur = con.execute(
                "UPDATE user_waifus SET is_favorite=1 WHERE user_id=? AND waifu_id=?",
                (int(user_id), str(waifu_id)),
            )
            if cur.rowcount != 1:
                con.rollback()
                raise ValueError("You do not own that waifu.")
        con.commit()


def add_audit(actor_id: int, action: str, target_id: int | None = None, details=None):
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO audit_log(actor_id,action,target_id,details,created_at) VALUES (?,?,?,?,?)",
            (int(actor_id), action, target_id,
             json.dumps(details or {}, ensure_ascii=False), now()),
        )


def create_pending(user_id: int, action: str, payload: dict, ttl: int = 60) -> str:
    init_db()
    token = uuid.uuid4().hex[:16]
    with connect() as con:
        con.execute(
            "INSERT INTO pending_actions(token,user_id,action,payload,expires_at) VALUES (?,?,?,?,?)",
            (token, int(user_id), action, json.dumps(payload), now() + int(ttl)),
        )
    return token


def get_pending(token: str, user_id: int, action: str):
    init_db()
    with connect() as con:
        return con.execute(
            """SELECT * FROM pending_actions WHERE token=? AND user_id=?
            AND action=? AND status='pending' AND expires_at>=?""",
            (token, int(user_id), action, now()),
        ).fetchone()


def finish_pending(token: str, status: str = "done") -> None:
    with connect() as con:
        con.execute(
            "UPDATE pending_actions SET status=? WHERE token=? AND status='pending'",
            (status, token),
        )


def cooldown_left(user_id: int, action: str) -> int:
    init_db()
    with connect() as con:
        row = con.execute(
            "SELECT expires_at FROM cooldowns WHERE user_id=? AND action=?",
            (int(user_id), action),
        ).fetchone()
        return max(0, int(row["expires_at"]) - now()) if row else 0


def set_cooldown(user_id: int, action: str, seconds: int) -> None:
    init_db()
    with connect() as con:
        con.execute(
            """INSERT INTO cooldowns(user_id,action,expires_at) VALUES (?,?,?)
            ON CONFLICT(user_id,action) DO UPDATE SET expires_at=excluded.expires_at""",
            (int(user_id), action, now() + int(seconds)),
        )


def record_transaction(actor_id: int, action: str, amount: int = 0,
                       target_id: int | None = None, waifu_id: str | None = None, details=None):
    init_db()
    txid = uuid.uuid4().hex
    with connect() as con:
        con.execute(
            """INSERT INTO transactions(tx_id,actor_id,target_id,action,amount,waifu_id,details,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (txid, int(actor_id), target_id, action, int(amount), waifu_id,
             json.dumps(details or {}, ensure_ascii=False), now()),
        )
    return txid
