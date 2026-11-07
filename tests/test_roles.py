"""Persistent role resolution and isolation tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waifux import roles


def test_owner_is_always_owner_and_never_needs_staff_json(tmp_path):
    roles.configure(8163432539, tmp_path)
    assert roles.role(8163432539) == "owner"
    assert roles.is_owner(8163432539)
    assert not roles.is_sudo(8163432539)
    assert not roles.is_uploader(8163432539)


def test_sudo_and_uploader_lists_persist_and_remain_separate(tmp_path):
    roles.configure(8163432539, tmp_path)
    roles.save_sudo([12345, "12345", 8163432539, -1])
    roles.save_uploaders([67890, "67890", 8163432539])
    assert roles.load_sudo() == [12345]
    assert roles.load_uploaders() == [67890]
    assert roles.role(12345) == "sudo"
    assert roles.role(67890) == "uploader"
    assert roles.role(99999) == "user"

    # A fresh configuration pointed at the same data directory must retain roles.
    roles.configure(8163432539, tmp_path)
    assert roles.role(12345) == "sudo"
    assert roles.role(67890) == "uploader"


def test_owner_id_cannot_be_accidentally_promoted_to_staff(tmp_path):
    roles.configure(8163432539, tmp_path)
    roles.save_sudo([8163432539, 12345])
    roles.save_uploaders([8163432539, 67890])
    assert roles.load_sudo() == [12345]
    assert roles.load_uploaders() == [67890]
    assert roles.role(8163432539) == "owner"
