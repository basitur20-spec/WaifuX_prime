"""Accepted /upload input syntax tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waifux.waifu_handlers import _parse_upload_details


def test_upload_key_value_format():
    assert _parse_upload_details(
        "Name Kyoko Hori\nRarity 10\nAnime Horimiya\nPrice 678000\nID 0001"
    ) == {
        "name": "Kyoko Hori",
        "rarity": "10",
        "anime": "Horimiya",
        "price": "678000",
        "id": "0001",
    }


def test_upload_label_on_own_line_format():
    assert _parse_upload_details(
        "Name\nKyoko Hori\nRarity\n10\nAnime\nHorimiya"
    ) == {"name": "Kyoko Hori", "rarity": "10", "anime": "Horimiya"}


def test_upload_legacy_comma_format():
    assert _parse_upload_details("/upload 0001,Kyoko Hori,Horimiya,10,678000") == {
        "id": "0001",
        "name": "Kyoko Hori",
        "anime": "Horimiya",
        "rarity": "10",
        "price": "678000",
    }
