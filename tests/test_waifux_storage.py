"""Transactional persistence tests using an isolated temporary database."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waifux import storage


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "balance_system.db")
    storage.init_db()
    return tmp_path


def test_storage_schema_initializes_without_destroying_existing_balance_table(isolated_db):
    with storage.connect() as con:
        con.execute(
            "INSERT INTO user_balance(user_id,cash,diamonds) VALUES (77,1200,3)"
        )
    assert storage.get_balance(77) == (1200, 3)


def test_collection_supports_multiple_copies_and_removes_one_at_a_time(isolated_db):
    storage.add_waifu("1234", "Test Hero", "Test Anime", "Shiny", 40000, "photo-file-id", 9)
    assert storage.add_to_collection(10, "1234", "test")
    assert storage.add_to_collection(10, "1234", "test")
    assert len(storage.collection(10)) == 2
    assert storage.remove_from_collection(10, "1234")
    assert len(storage.collection(10)) == 1


def test_balance_updates_are_atomic_and_reject_negative_balance(isolated_db):
    storage.change_balance(10, cash_delta=500)
    assert storage.get_balance(10) == (500, 0)
    with pytest.raises(ValueError):
        storage.change_balance(10, cash_delta=-501)
    assert storage.get_balance(10) == (500, 0)


def test_duplicate_waifu_ids_are_rejected(isolated_db):
    storage.add_waifu("1234", "Test Hero", "Test Anime", "Shiny", 40000, "photo-file-id", 9)
    with pytest.raises(Exception):
        storage.add_waifu("1234", "Another Hero", "Another Anime", "Rising", 30000, "photo-2", 9)



def test_bot_user_ids_are_stable_unique_and_eleven_digits(isolated_db):
    first = storage.ensure_bot_user_id(1001)
    assert len(first) == 11 and first.isdigit()
    assert storage.ensure_bot_user_id(1001) == first
    second = storage.ensure_bot_user_id(1002)
    assert len(second) == 11 and second.isdigit()
    assert second != first
