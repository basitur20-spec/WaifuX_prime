"""Single registration point for commands preserved in the supplied source."""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
)

from legacy import partial_commands as legacy

logger = logging.getLogger(__name__)


async def help_command(update, context) -> None:
    """Show the available command groups from the preserved feature set."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Commands", callback_data="HELP_COMMANDS_1"),
         InlineKeyboardButton("Games", callback_data="HELP_GAMES")]
    ])
    await update.message.reply_text(
        "WaifuX Prime Help\nChoose a category below.", reply_markup=keyboard
    )


def _install_runtime_roles(owner_id: int) -> None:
    """Replace stale hard-coded role IDs with the persistent role lists."""
    legacy.OWNER_ID = owner_id

    def _is_owner(uid: int) -> bool:
        return int(uid) == owner_id

    def _is_sudo(uid: int) -> bool:
        try:
            return int(uid) in {int(value) for value in legacy.load_sudo()}
        except (TypeError, ValueError):
            return False

    def _is_uploader(uid: int) -> bool:
        try:
            return int(uid) in {int(value) for value in legacy.load_uploaders()}
        except (TypeError, ValueError):
            return False

    def _role(uid: int) -> str:
        if _is_owner(uid):
            return "owner"
        if _is_sudo(uid):
            return "sudo"
        if _is_uploader(uid):
            return "uploader"
        return "user"

    legacy.is_owner = _is_owner
    legacy.is_sudo = _is_sudo
    legacy.is_uploader = _is_uploader
    legacy.role = _role
    legacy.is_staff = lambda uid: _role(uid) in {"owner", "sudo", "uploader"}
    legacy.SUDO_USERS = set()
    legacy.UPLOADER_USERS = set()


def _sync_legacy_role_sets() -> None:
    """Refresh compatibility sets used by older command implementations."""
    legacy.SUDO_USERS = {int(value) for value in legacy.load_sudo()}
    legacy.UPLOADER_USERS = {int(value) for value in legacy.load_uploaders()}


async def redeem_command(update, context) -> None:
    _sync_legacy_role_sets()
    await legacy.redeem_cmd(update, context)


def register_handlers(app: Application, owner_id: int) -> None:
    """Register each command once and route callbacks by specific prefixes."""
    _install_runtime_roles(owner_id)
    legacy.ensure_files()
    legacy.init_collection_db()

    command_map = {
        "start": legacy.start,
        "help": help_command,
        "balance": legacy.balance_cmd,
        "explore": legacy.explore_cmd,
        "bonus": legacy.bonus_cmd,
        "bonusrefresh": legacy.bonusrefresh_cmd,
        "pay": legacy.pay_cmd,
        "payrefresh": legacy.payrefresh_cmd,
        "roll": legacy.roll_cmd,
        "darts": legacy.darts_cmd,
        "goal": legacy.goal_cmd,
        "mines": legacy.mines_cmd,
        "endmines": legacy.endmines,
        "dtops": legacy.dtops_cmd,
        "collection": legacy.collection_cmd,
        "gen": legacy.gen_cmd,
        "redeem": redeem_command,
        "dgen": legacy.dgen_cmd,
        "dredeem": legacy.dredeem_cmd,
        "redeemtoggle": legacy.redeem_toggle,
        "dredeemtoggle": legacy.dredeem_toggle,
        "addsudo": legacy.add_sudo,
        "rsudo": legacy.remove_sudo,
        "sudolist": legacy.sudo_list_command,
        "sudocommands": legacy.sudo_commands,
        "adduploader": legacy.add_uploader,
        "ruploader": legacy.remove_uploader,
        "uploaderlist": legacy.uploader_list_command,
        "uploadercommands": legacy.uploader_commands,
    }
    for name, callback in command_map.items():
        app.add_handler(CommandHandler(name, callback))

    # Specific callback patterns prevent the old catch-all handler from
    # swallowing collection image callbacks or unrelated inline buttons.
    callback_map = [
        (r"^bonus_", legacy.bonus_callback),
        (r"^pay_", legacy.pay_callback),
        (r"^(?:mine_\d+|mines_cashout)$", legacy.mines_callback),
        (r"^dt_", legacy.dtops_callback),
        (r"^cw_img_\d+_\d+$", legacy.collection_image_view),
        (r"^(?:cw_(?:next|prev)_\d+_\d+|cw_close)$", legacy.collection_callback),
        (r"^SUDO_GUIDE$", legacy.sudo_guide_callback),
        (r"^UPLOADER_GUIDE$", legacy.uploader_guide_callback),
        (r"^(?:OPEN_HELP|HELP_COMMANDS_1|HELP_COMMANDS_2|HELP_GAMES|HELP_BACK_TO_START)$", legacy.callback_router),
    ]
    for pattern, callback in callback_map:
        app.add_handler(CallbackQueryHandler(callback, pattern=pattern))

    app.add_handler(InlineQueryHandler(legacy.inline_collection))
    logger.info("Registered %d commands and %d callback routes", len(command_map), len(callback_map))
