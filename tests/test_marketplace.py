"""Offline marketplace offer and refresh regression tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from waifux import marketplace, storage


def test_marketplace_generates_two_offers_and_limits_paid_refreshes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "balance_system.db")
    storage.init_db()
    fixtures = [
        ("1001", "ChibiArc"), ("1002", "WinterArc"),
        ("1003", "RoyalArc"), ("1004", "NeonArc"),
        ("1005", "CelestialArc"), ("1006", "MangaArc"),
    ]
    for wid, rarity in fixtures:
        storage.add_waifu(wid, f"Hero {wid}", "Test Anime", rarity, 500000, f"photo-{wid}", 1)
    storage.change_balance(2001, cash_delta=200000)

    first = marketplace._ensure_offers(2001)
    assert len(first) == 2
    assert len({row["waifu_id"] for row in first}) == 2
    assert len(marketplace._ensure_offers(2001)) == 2

    marketplace._ensure_offers(2001, refresh=True)
    marketplace._ensure_offers(2001, refresh=True)
    assert storage.get_balance(2001)[0] == 100000
    with pytest.raises(ValueError, match="Daily refresh limit"):
        marketplace._ensure_offers(2001, refresh=True)
