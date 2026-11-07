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



def test_runtime_role_install_uses_replit_owner_id_for_legacy_checks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from legacy import partial_commands as legacy
    from waifux.handlers import _install_runtime_roles

    _install_runtime_roles(987654321)
    assert legacy.OWNER_ID == 987654321
    assert legacy.is_sudo_owner(987654321)
    assert legacy.is_uploader_owner(987654321)
    assert legacy.is_owner(987654321)
    assert legacy.role(987654321) == "owner"
    assert legacy.is_staff(987654321)



def test_command_matrix_and_role_specific_help(tmp_path):
    from waifux import handlers

    roles.configure(8163432539, tmp_path)
    roles.save_sudo([12345])
    roles.save_uploaders([67890])

    assert handlers.ROLE_COMMANDS["addsudo"] == {"owner"}
    assert handlers.ROLE_COMMANDS["gen"] == {"sudo"}
    assert handlers.ROLE_COMMANDS["upload"] == {"uploader"}
    assert handlers.ROLE_COMMANDS["auction"] == {"sudo", "uploader"}
    assert handlers.ROLE_COMMANDS["dupload"] == {"sudo", "uploader"}

    assert "SUDO COMMAND GUIDE" in handlers._help_content(12345, "sudo")
    assert "UPLOADER COMMAND GUIDE" in handlers._help_content(67890, "uploader")
    assert handlers._help_content(67890, "sudo") == "This guide is not available for your role."
    assert "unrestricted access" in handlers._help_content(8163432539, "owner")


def test_owner_bypasses_staff_command_guard(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from waifux import handlers

    roles.configure(8163432539, tmp_path)
    called = []

    async def callback(update, context):
        called.append(update.effective_user.id)

    guarded = handlers._guard_role("gen", callback)
    owner_update = SimpleNamespace(effective_user=SimpleNamespace(id=8163432539))
    uploader_update = SimpleNamespace(effective_user=SimpleNamespace(id=67890))

    asyncio.run(guarded(owner_update, None))
    asyncio.run(guarded(uploader_update, None))
    assert called == [8163432539]
