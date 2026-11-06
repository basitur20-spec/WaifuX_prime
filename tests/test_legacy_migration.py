import json
import sqlite3

from waifux import storage


def test_legacy_collection_and_json_are_imported_once(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "balance_system.db")
    old = sqlite3.connect(tmp_path / "collection.db")
    old.execute(
        """CREATE TABLE collections(
            user_id INTEGER, username TEXT, waifu_id TEXT, name TEXT,
            anime TEXT, rarity TEXT, image TEXT, favorite INTEGER DEFAULT 0
        )"""
    )
    old.execute(
        "INSERT INTO collections VALUES (77,'tester','1234','Legacy Hero','Legacy Anime','Shiny','telegram-file-id',1)"
    )
    old.commit()
    old.close()
    (tmp_path / "users.json").write_text(
        json.dumps({"77": {"collection": ["1234"]}, "88": {"collection": ["1234"]}}),
        encoding="utf-8",
    )

    storage.migrate_legacy_data()
    assert len(storage.collection(77)) == 1
    assert len(storage.collection(88)) == 1
    assert storage.get_waifu("1234")["name"] == "Legacy Hero"

    storage.migrate_legacy_data()
    assert len(storage.collection(77)) == 1
    assert len(storage.collection(88)) == 1
