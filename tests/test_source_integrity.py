"""Lightweight checks that do not require Telegram credentials or network access."""
import ast
from pathlib import Path


def test_entrypoint_is_syntax_valid():
    ast.parse(Path("main.py").read_text(encoding="utf-8"))


def test_handlers_are_syntax_valid():
    ast.parse(Path("waifux/handlers.py").read_text(encoding="utf-8"))


def test_config_is_syntax_valid():
    ast.parse(Path("waifux/config.py").read_text(encoding="utf-8"))


def test_legacy_source_is_preserved_and_syntax_valid():
    source = Path("legacy/partial_commands.py")
    assert source.exists()
    ast.parse(source.read_text(encoding="utf-8"))
