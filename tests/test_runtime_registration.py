"""Runtime import and command-registration smoke test; no Telegram network calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram.ext import Application, CommandHandler
from waifux import storage
from waifux.handlers import register_handlers


def test_runtime_modules_import_and_register_core_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "balance_system.db")
    app = Application.builder().token("123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi").build()
    register_handlers(app, 8163432539)
    commands = set()
    for group_handlers in app.handlers.values():
        for handler in group_handlers:
            if isinstance(handler, CommandHandler):
                commands.update(handler.commands)
    expected = {
        "start", "help", "upload", "hunt", "waifu", "collection", "fav",
        "profile", "find", "dfind", "f", "gift", "trade", "sell",
        "marketplace", "auction", "bid", "claim", "gclaim", "filter",
        "delfilter", "delall", "send", "stop", "run", "dmode",
    }
    assert expected <= commands
