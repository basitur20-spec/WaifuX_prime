"""Regression tests for the user's original waifu gameplay rules."""
import asyncio
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waifux import waifu_handlers as waifu


def test_daily_and_marriage_rarity_weights_match_spec():
    assert waifu.DAILY_WAIFU_WEIGHTS == {
        "Starter": 50,
        "Rising": 50,
        "Shiny": 50,
        "Ultimate": 50,
        "RoyalArc": 5,
    }
    assert waifu.MARRIAGE_REWARD_WEIGHTS == {"Shiny": 50, "Ultimate": 50}
    assert waifu.RARITY_WEIGHTS["LoveArc"] == 3
    assert waifu.RARITY_WEIGHTS["RoyalArc"] == 35
    assert waifu.RARITY_WEIGHTS["LimitedArc"] == 0
    assert waifu.RARITY_WEIGHTS["SpecialArc"] == 0
    assert waifu.RARITY_WEIGHTS["DivineArc"] == 0
    assert waifu.RARITY_WEIGHTS["CinemaArc"] == 0


def test_inline_favourite_search_filters_global_catalogue_by_name_and_rarity(monkeypatch):
    from telegram import InlineQueryResultCachedPhoto

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE waifus (waifu_id TEXT, name TEXT, anime TEXT, rarity TEXT, "
        "image_file_id TEXT, aliases TEXT)"
    )
    con.executemany(
        "INSERT INTO waifus VALUES (?,?,?,?,?,?)",
        [
            ("0001", "Son Goku", "Dragon Ball Z", "Shiny", "file-shiny", '["Goku"]'),
            ("0002", "Son Goku", "Dragon Ball Z", "Ultimate", "file-ultimate", '["Goku"]'),
            ("0003", "Vegeta", "Dragon Ball Z", "Shiny", "file-vegeta", "[]"),
        ],
    )
    rows = con.execute("SELECT * FROM waifus").fetchall()
    monkeypatch.setattr(waifu.storage, "list_waifus", lambda limit=10000: rows)

    class FakeQuery:
        query = "waifu Son Goku rarity:Shiny"
        from_user = SimpleNamespace(id=111)

        async def answer(self, results, **kwargs):
            self.results = results
            self.kwargs = kwargs

    query = FakeQuery()
    update = SimpleNamespace(inline_query=query)
    asyncio.run(waifu.inline_collection(update, None))

    assert len(query.results) == 1
    assert isinstance(query.results[0], InlineQueryResultCachedPhoto)
    assert query.results[0].title == "Son Goku"
    assert query.results[0].description == "Shiny | Dragon Ball Z"
    con.close()
