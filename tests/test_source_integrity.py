"""Lightweight checks that do not require Telegram credentials or network access."""
import ast
from pathlib import Path


def _tree(path):
    return ast.parse(Path(path).read_text(encoding="utf-8"))


def test_entrypoint_and_runtime_modules_are_syntax_valid():
    for path in ("main.py", "waifux/config.py", "waifux/handlers.py"):
        _tree(path)


def test_legacy_source_is_preserved_and_syntax_valid():
    assert Path("legacy/partial_commands.py").exists()
    _tree("legacy/partial_commands.py")
    assert Path("legacy/source_original.py").exists()
    _tree("legacy/source_original.py")
    legacy_tree = _tree("legacy/partial_commands.py")
    names = [
        node.name for node in ast.walk(legacy_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert names.count("add_waifu_to_collection") == 1
    assert "add_waifu_id_to_user_collection" in names


def test_command_registry_has_no_duplicate_names():
    tree = _tree("waifux/handlers.py")
    command_map = next(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "command_map" for target in node.targets)
    )
    names = [key.value for key in command_map.keys if isinstance(key, ast.Constant)]
    assert len(names) == len(set(names))
    assert "redeem" in names
    assert "redeemtoggle" in names
    assert "dredeemtoggle" in names


def test_redeem_toggles_are_not_duplicate_redeem_commands():
    source = Path("waifux/handlers.py").read_text(encoding="utf-8")
    assert '"redeem": redeem_command' in source
    assert '"dredeem": legacy.dredeem_cmd' in source
    assert '"redeemtoggle": legacy.redeem_toggle' in source
    assert '"dredeemtoggle": legacy.dredeem_toggle' in source
