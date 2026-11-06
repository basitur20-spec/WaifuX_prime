"""Single registration point for commands preserved in the supplied source."""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from legacy import partial_commands as legacy
from . import storage
from . import waifu_handlers as waifu
from . import marketplace
from . import social_handlers as social
from . import event_handlers as events

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "🌸 WAIFUX PRIME — COMMAND GUIDE 🌸\n\n"
    "📚 COLLECTION & PROFILE\n"
    "/collection [@username|bot_id] — view collection\n"
    "/fav <waifu_id> — set favourite\n"
    "/dmode — choose collection display mode\n"
    "/setprofile <waifu_id> — set profile waifu; reply to a photo to set profile photo\n"
    "/profile [@username|bot_id] — view profile\n\n"
    "🎭 CHARACTER CATALOGUE\n"
    "/upload — upload a photo with Name, Rarity, Anime\n"
    "/dupload <waifu_id> — delete a character (uploader)\n"
    "/f <waifu_id> — character information\n"
    "/find <waifu_id> — global owners and picked count\n"
    "/dfind <name> — search catalogue by name/anime\n\n"
    "🎮 GAMEPLAY\n"
    "/hunt <name> — claim the group spawn\n"
    "/waifu — claim daily waifu (12h cooldown)\n"
    "/marriage — 35% chance for Shiny/Ultimate reward\n"
    "/propose — spend 30,000 Cash for a proposal\n\n"
    "💰 ECONOMY & TRANSFERS\n"
    "/balance, /explore, /bonus, /pay — cash economy\n"
    "/sell <id> [ids...] — sell up to 5 waifus/day\n"
    "/sell diamonds <amount> — exchange diamonds for Cash\n"
    "/gift <waifu_id> — reply to a user to gift\n"
    "/trade <your_id> <their_id> — reply to a user to trade\n\n"
    "🏪 MARKETPLACE & AUCTIONS\n"
    "/marketplace — daily offers, two purchases/day\n"
    "/auction <waifu_id> <starting_bid> [hours] — list auction (staff)\n"
    "/bid <amount> — submit a bid after opening Auction\n"
    "/auction users — current bidders (staff)\n\n"
    "👥 GROUP CONTROLS\n"
    "/spawn <rarity> on/off — toggle hunt rarity (owner)\n"
    "/changetime <2-120 minutes> — set group spawn interval (sudo)\n"
    "/filter <keyword> | <response>, /filters, /delfilter, /delall\n\n"
    "👑 OWNER / STAFF\n"
    "/give <waifu_id> <username|bot_id> — grant waifu\n"
    "/gclaim <amount|amount d|waifu id> — create one-time reward\n"
    "/claim — claim active reward once\n"
    "/marketspawn <rarity> on/off — marketplace rarity control (owner)\n"
    "/stop <command>, /run <command|all>, /send <message>\n"
    "/addsudo, /rsudo, /sudolist, /adduploader, /ruploader\n\n"
    "🎲 OTHER GAMES\n"
    "/roll, /darts, /goal, /mines, /endmines"
)


async def help_command(update, context) -> None:
    await update.effective_message.reply_text(HELP_TEXT)


async def help_callback(update, context) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="HELP_BACK_TO_START")]])
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


async def dredeem_command(update, context) -> None:
    await legacy.dredeem_cmd(update, context)
    uid = update.effective_user.id
    try:
        legacy_users = legacy.load_users()
        owned_ids = legacy_users.get(str(uid), {}).get("collection", [])
    except Exception:
        owned_ids = []
    for wid in owned_ids:
        if storage.get_waifu(str(wid)) and not storage.owned_waifu(uid, str(wid)):
            storage.add_to_collection(uid, str(wid), "dredeem")


def register_handlers(app: Application, owner_id: int) -> None:
    """Register each command once and route callbacks by specific prefixes."""
    _install_runtime_roles(owner_id)
    waifu.configure(owner_id)
    legacy.ensure_files()
    legacy.init_collection_db()
    storage.migrate_legacy_data()

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
        "gen": legacy.gen_cmd,
        "redeem": redeem_command,
        "dgen": legacy.dgen_cmd,
        "dredeem": dredeem_command,
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
        "upload": waifu.upload_cmd,
        "collection": waifu.collection_cmd,
        "dmode": waifu.dmode_cmd,
        "fav": waifu.fav_cmd,
        "waifu": waifu.waifu_cmd,
        "hunt": waifu.hunt_cmd,
        "spawn": waifu.spawn_cmd,
        "changetime": waifu.changetime_cmd,
        "marriage": waifu.marriage_cmd,
        "propose": waifu.propose_cmd,
        "profile": waifu.profile_cmd,
        "find": waifu.find_cmd,
        "dfind": waifu.dfind_cmd,
        "f": waifu.f_cmd,
        "gift": waifu.gift_cmd,
        "sell": waifu.sell_cmd,
        "setprofile": waifu.setprofile_cmd,
        "dupload": waifu.dupload_cmd,
        "stop": waifu.stop_cmd,
        "run": waifu.run_cmd,
        "marketplace": marketplace.marketplace_cmd,
        "marketspawn": marketplace.marketspawn_cmd,
        "auction": marketplace.auction_cmd,
        "bid": marketplace.bid_cmd,
        "trade": social.trade_cmd,
        "give": social.give_cmd,
        "gclaim": events.gclaim_cmd,
        "claim": events.claim_cmd,
        "filters": events.filters_cmd,
        "filter": events.filter_add_cmd,
        "delfilter": events.filter_delete_cmd,
        "delall": events.filter_delete_all_cmd,
        "send": events.send_all_cmd,
    }
    app.add_handler(MessageHandler(filters.ALL, events.track_user), group=-2)
    app.add_handler(MessageHandler(filters.COMMAND, waifu.command_guard), group=-1)
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
        (r"^(?:HELP_COMMANDS_1|HELP_COMMANDS_2|HELP_GAMES|HELP_BACK_TO_START)$", legacy.callback_router),
    ]
    for pattern, callback in callback_map:
        app.add_handler(CallbackQueryHandler(callback, pattern=pattern))
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^OPEN_HELP$"))

    app.add_handler(CallbackQueryHandler(waifu.collection_callback, pattern=r"^(?:col|colimg|colclose|colimgclose):|^colimgnoop$"))
    app.add_handler(CallbackQueryHandler(waifu.dmode_callback, pattern=r"^(?:dmode:|dmrarity:|dmchoices:|dmback:|dmset:|dmpick:|dmclose:|dmnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.find_callback, pattern=r"^(?:find:|finddel:|findnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.dfind_callback, pattern=r"^(?:dfind:|dfinddel:|dfindnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.waifu_callback, pattern=r"^fav(?:inline|confirm|cancel):"))
    app.add_handler(CallbackQueryHandler(waifu.gift_callback, pattern=r"^gift(?:ok|no):"))
    app.add_handler(CallbackQueryHandler(waifu.sell_callback, pattern=r"^sell(?:ok|no):"))
    app.add_handler(CallbackQueryHandler(waifu.delete_callback, pattern=r"^del(?:ok|no):"))
    app.add_handler(CallbackQueryHandler(marketplace.marketplace_callback, pattern=r"^mkt:"))
    app.add_handler(CallbackQueryHandler(marketplace.auction_callback, pattern=r"^aucbid:"))
    app.add_handler(CallbackQueryHandler(marketplace.bid_callback, pattern=r"^bid(?:ok|no):"))
    app.add_handler(CallbackQueryHandler(social.trade_callback, pattern=r"^trd(?:accept|cancel):"))
    app.add_handler(CallbackQueryHandler(social.give_callback, pattern=r"^giv(?:eok|no):"))
    app.add_handler(InlineQueryHandler(waifu.inline_collection))
    app.add_handler(MessageHandler(filters.ALL, waifu.group_activity), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, events.filter_message), group=2)
    app.job_queue.run_repeating(marketplace.settle_auctions, interval=60, first=30, name="auction-settlement")
    app.job_queue.run_repeating(waifu.spawn_expiry_job, interval=15, first=15, name="spawn-expiry")
    logger.info("Registered %d commands and %d callback routes", len(command_map), len(callback_map))
