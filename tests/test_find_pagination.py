"""Tests for global waifu ownership lookup and pagination."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waifux import waifu_handlers as waifu


def test_find_helpers_page_distinct_owners_and_show_global_picks(monkeypatch):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE user_waifus (user_id INTEGER, waifu_id TEXT, obtained_at INTEGER)")
    con.execute(
        "CREATE TABLE user_profiles (user_id INTEGER, first_name TEXT, username TEXT, bot_user_id TEXT)"
    )
    con.executemany(
        "INSERT INTO user_waifus VALUES (?,?,?)",
        [(i, "0001", i) for i in range(1, 12)] + [(1, "0001", 99)],
    )
    con.executemany(
        "INSERT INTO user_profiles VALUES (?,?,?,?)",
        [(i, f"User {i}", f"user{i}", f"1000000000{i}") for i in range(1, 12)],
    )
    monkeypatch.setattr(waifu.storage, "connect", lambda: con)

    total, page_one, total_users = waifu._find_users_page("0001", 0)
    assert total == total_users == 11
    assert len(page_one) == 10

    item = {
        "waifu_id": "0001",
        "name": "Kyoko Hori",
        "rarity": "ChristmasArc",
        "anime": "Horimiya",
        "price": 678000,
    }
    caption, pages = waifu._find_caption(item, 0)
    assert pages == 2
    assert "GLOBALLY 𝗣𝗜𝗖𝗞𝗘𝗗: 12 Times" in caption
    assert "Page 1/2" in caption
    assert "User 1" in caption

    _, page_two, _ = waifu._find_users_page("0001", 1)
    assert len(page_two) == 1
    con.close()
