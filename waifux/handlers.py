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
from . import roles

logger = logging.getLogger(__name__)


HELP_CATEGORIES = {
    "collection": (
        "📚 COLLECTION & PROFILE\n\n"
        "/collection — View your collection\n"
        "/fav or /fave — Manage favourite waifus\n"
        "/dmode — Change collection display mode\n"
        "/profile [user] — View a profile\n"
        "/setprofile <waifu_id> — Set profile waifu/photo"
    ),
    "waifu": (
        "🎭 WAIFU GAMEPLAY\n\n"
        "/hunt <name> — Claim the active group spawn\n"
        "/waifu — Claim your daily waifu\n"
        "/marriage — Try the marriage feature\n"
        "/propose — Make a proposal"
    ),
    "catalogue": (
        "🗂️ CHARACTER CATALOGUE\n\n"
        "/f <waifu_id> — View character information\n"
        "/find <waifu_id> — Find character owners\n"
        "/dfind <name> — Search uploaded characters\n"
        "/upload — Upload a character (Uploader/Owner)\n"
        "/dupload <waifu_id> — Request character deletion (Sudo/Owner)"
    ),
    "economy": (
        "💰 ECONOMY & TRANSFERS\n\n"
        "/balance — Check your balance\n"
        "/explore — Explore for rewards\n"
        "/bonus — Open daily/weekly bonus menu\n"
        "/pay — Transfer cash/diamonds\n"
        "/gift <waifu_id> — Gift a waifu (reply to receiver)\n"
        "/trade <your_id> <their_id> — Trade waifus (reply to user)\n"
        "/sell <waifu_id> — Sell a waifu"
    ),
    "market": (
        "🏪 MARKETPLACE\n\n"
        "/marketplace — Open your personal daily marketplace.\n"
        "Each offer has its own details, price, discount and Buy button.\n"
        "Use the Refresh button to rotate eligible offers."
    ),
    "auction": (
        "🔨 AUCTION GUIDE\n\n"
        "Open /marketplace and tap the Auction button to view an active auction.\n"
        "Choose the bid amount, then confirm or cancel your bid.\n"
        "The highest valid bid wins when the auction timer ends.\n"
        "Sudo/Owner staff can list auctions; see Staff Guide."
    ),
    "games": (
        "🎮 GAMES\n\n"
        "/roll — Roll dice\n"
        "/darts — Play darts\n"
        "/goal — Play goal\n"
        "/mines — Play mines\n"
        "/endmines — End your active mines game"
    ),
    "groups": (
        "👥 GROUP TOOLS\n\n"
        "/filter <keyword> | <reply> — Add a chat filter\n"
        "/filters — View chat filters\n"
        "/delfilter <keyword> — Delete a filter\n"
        "/delall — Delete all chat filters\n"
        "/changetime <minutes> — Set spawn interval (Sudo/Owner)\n"
        "/spawn <rarity> on/off — Toggle spawn rarity (Owner)"
    ),
}

ROLE_COMMANDS = {
    "addsudo": {"owner"}, "rsudo": {"owner"},
    "adduploader": {"owner"}, "ruploader": {"owner"},
    "sudolist": {"sudo"}, "sudocommands": {"sudo"},
    "uploaderlist": {"uploader"}, "uploadercommands": {"uploader"},
    "upload": {"uploader"}, "dupload": {"sudo", "uploader"},
    "auction": {"sudo", "uploader"}, "changetime": {"sudo"},
    "gen": {"sudo"}, "dgen": {"sudo", "uploader"}, "give": {"sudo", "uploader"}, "dtops": {"sudo", "uploader"},
    "bonusrefresh": {"owner"}, "payrefresh": {"owner"},
    "redeemtoggle": {"owner"}, "dredeemtoggle": {"owner"},
    "marketspawn": {"owner"}, "spawn": {"owner"},
    "gclaim": {"owner"}, "send": {"owner"}, "stop": {"owner"}, "run": {"owner"},
}


def _role(uid: int) -> str:
    return roles.role(int(uid))


def _help_keyboard(uid: int, section: str = "main") -> InlineKeyboardMarkup:
    role = _role(uid)
    if section == "main":
        rows = [
            [InlineKeyboardButton("📚 Collection", callback_data="HELP:collection"),
             InlineKeyboardButton("🎭 Waifu", callback_data="HELP:waifu")],
            [InlineKeyboardButton("🗂️ Catalogue", callback_data="HELP:catalogue"),
             InlineKeyboardButton("💰 Economy", callback_data="HELP:economy")],
            [InlineKeyboardButton("🏪 Marketplace", callback_data="HELP:market"),
             InlineKeyboardButton("🎮 Games", callback_data="HELP:games")],
            [InlineKeyboardButton("🔨 Auctions", callback_data="HELP:auction"),
             InlineKeyboardButton("👥 Group Tools", callback_data="HELP:groups")],
        ]
        if role != "user":
            rows.append([InlineKeyboardButton("🛡️ Staff Guide", callback_data="HELP:staff")])
        rows.append([InlineKeyboardButton("✖ Close", callback_data="HELP:close")])
        return InlineKeyboardMarkup(rows)

    if section == "staff":
        rows = []
        if role == "owner":
            rows.extend([
                [InlineKeyboardButton("👑 Owner Commands", callback_data="HELP:owner")],
                [InlineKeyboardButton("🛡️ Sudo Commands", callback_data="HELP:sudo")],
                [InlineKeyboardButton("📤 Uploader Commands", callback_data="HELP:uploader")],
            ])
        elif role == "sudo":
            rows.append([InlineKeyboardButton("🛡️ Sudo Commands", callback_data="HELP:sudo")])
        elif role == "uploader":
            rows.append([InlineKeyboardButton("📤 Uploader Commands", callback_data="HELP:uploader")])
        rows.append([InlineKeyboardButton("⬅ Back", callback_data="HELP:main")])
        return InlineKeyboardMarkup(rows)

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back to Help", callback_data="HELP:main")]
    ])


def _help_content(uid: int, section: str) -> str:
    role = _role(uid)
    if section in HELP_CATEGORIES:
        return HELP_CATEGORIES[section]
    if section == "staff":
        return "🛡️ STAFF GUIDE\n\nChoose your verified role below to view its command guide."
    if section == "owner" and role == "owner":
        return (
            "👑 OWNER COMMAND GUIDE\n\n"
            "Owner has unrestricted access to every bot command.\n\n"
            "ROLE MANAGEMENT\n"
            "/addsudo — Reply to a user to promote them to Sudo\n"
            "/rsudo — Reply to a Sudo to remove the role\n"
            "/adduploader — Reply to a user to promote them to Uploader\n"
            "/ruploader — Reply to an Uploader to remove the role\n"
            "/sudolist /uploaderlist — View staff lists\n\n"
            "OWNER CONTROLS\n"
            "/bonusrefresh — Reply to a user to reset bonus cooldown\n"
            "/payrefresh — Reply to a user to reset payment cooldown\n"
            "/marketspawn <rarity> on/off — Toggle marketplace rarity\n"
            "/spawn <rarity> on/off — Toggle spawn rarity\n"
            "/redeemtoggle on/off, /dredeemtoggle on/off\n"
            "/gclaim — Create a one-time reward\n"
            "/send — Broadcast a message\n"
            "/stop /run — Manage command maintenance\n\n"
            "Owner can also use all Sudo and Uploader commands."
        )
    if section == "sudo" and role in {"owner", "sudo"}:
        return (
            "🛡️ SUDO COMMAND GUIDE\n\n"
            "/auction <waifu_id> <starting_bid> [hours]\n"
            "Example: /auction 2342 1000000 24\n"
            "/auction users — View active auction bidders\n\n"
            "/gen <amount> <quantity> [cash/dimond] — Generate cash/diamond codes\n"
            "/dgen <waifu_id> <quantity> — Generate waifu codes\n"
            "/changetime <2-120 minutes> — Change group spawn interval\n"
            "/dupload <waifu_id> — Request character deletion\n"
            "/give <waifu_id> <username|bot_user_id> — Grant a waifu\n"
            "/dtops — View upload statistics\n"
            "/sudolist — View Sudo members\n"
            "/sudocommands — Open this command guide"
        )
    if section == "uploader" and role in {"owner", "uploader"}:
        return (
            "📤 UPLOADER COMMAND GUIDE\n\n"
            "/upload — Upload a waifu using an image and its details.\n"
            "Send the image with caption fields:\n"
            "Name: Character Name\nRarity: Shiny\nAnime: Anime Name\n"
            "Price, ID and Aliases are optional.\n\n"
            "/auction <waifu_id> <starting_bid> [hours] — List an auction\n"
            "/auction users — View active auction bidders\n"
            "/dgen <waifu_id> <quantity> — Generate waifu codes\n"
            "/dupload <waifu_id> — Request character deletion\n"
            "/give <waifu_id> <username|bot_user_id> — Grant a waifu\n"
            "/dtops — View upload statistics\n"
            "/uploaderlist — View Uploader members\n"
            "/uploadercommands — Open this command guide"
        )
    return "This guide is not available for your role."


async def help_command(update, context) -> None:
    uid = update.effective_user.id
    await update.effective_message.reply_text(
        "🌸 WAIFUX PRIME — HELP CENTER 🌸\n\nChoose a category to view its commands and instructions.",
        reply_markup=_help_keyboard(uid),
    )


async def help_callback(update, context) -> None:
    q = update.callback_query
    uid = q.from_user.id
    data = q.data or ""
    if data == "OPEN_HELP" or data == "HELP:main":
        await q.answer()
        await q.edit_message_text(
            "🌸 WAIFUX PRIME — HELP CENTER 🌸\n\nChoose a category to view its commands and instructions.",
            reply_markup=_help_keyboard(uid),
        )
        return
    if data == "HELP:close":
        await q.answer()
        await q.delete_message()
        return
    section = data.partition(":")[2]
    role = _role(uid)
    if section in {"staff", "owner", "sudo", "uploader"}:
        permitted = (
            role != "user" if section == "staff" else
            role == "owner" if section == "owner" else
            role in {"owner", "sudo"} if section == "sudo" else
            role in {"owner", "uploader"}
        )
        if not permitted:
            await q.answer("This guide is not available for your role.", show_alert=True)
            return
    await q.answer()
    await q.edit_message_text(
        _help_content(uid, section),
        reply_markup=_help_keyboard(uid, section),
    )


async def staff_guide_callback(update, context, role_name: str) -> None:
    q = update.callback_query
    uid = q.from_user.id
    current = _role(uid)
    if current != "owner" and current != role_name:
        await q.answer("This guide is not available for your role.", show_alert=True)
        return
    await q.answer()
    await context.bot.send_message(chat_id=uid, text=_help_content(uid, role_name))



def _install_runtime_roles(owner_id: int) -> None:
    """Use one persistent role source and the Replit OWNER_ID everywhere."""
    roles.configure(owner_id)
    legacy.OWNER_ID = int(owner_id)
    legacy.SUDO_FILE = str(roles.SUDO_FILE)
    legacy.UPLOADER_FILE = str(roles.UPLOADER_FILE)
    legacy.load_sudo = roles.load_sudo
    legacy.save_sudo = roles.save_sudo
    legacy.load_uploaders = roles.load_uploaders
    legacy.save_uploaders = roles.save_uploaders
    legacy.is_sudo_owner = roles.is_owner
    legacy.is_uploader_owner = roles.is_owner
    legacy.is_owner = roles.is_owner
    legacy.is_sudo = roles.is_sudo
    legacy.is_uploader = roles.is_uploader
    legacy.role = roles.role
    legacy.is_staff = roles.is_staff
    _sync_legacy_role_sets()


def _sync_legacy_role_sets() -> None:
    """Refresh compatibility sets for older code that still uses set membership."""
    legacy.SUDO_USERS = set(roles.load_sudo())
    legacy.UPLOADER_USERS = set(roles.load_uploaders())


def _wrap_legacy(callback):
    async def wrapped(update, context):
        _sync_legacy_role_sets()
        return await callback(update, context)
    wrapped.__name__ = getattr(callback, "__name__", "legacy_handler")
    return wrapped


def _guard_role(command_name: str, callback):
    allowed = ROLE_COMMANDS.get(command_name)
    if not allowed:
        return callback

    async def guarded(update, context):
        _sync_legacy_role_sets()
        current = _role(update.effective_user.id)
        # Owner is intentionally unrestricted across the entire command map.
        if current != "owner" and current not in allowed:
            return
        return await callback(update, context)

    guarded.__name__ = getattr(callback, "__name__", f"guarded_{command_name}")
    return guarded


async def redeem_command(update, context) -> None:
    _sync_legacy_role_sets()
    await legacy.redeem_cmd(update, context)


async def dredeem_command(update, context) -> None:
    _sync_legacy_role_sets()
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
        "fave": waifu.fav_cmd,
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
        if callback.__module__ == legacy.__name__:
            callback = _wrap_legacy(callback)
        callback = _guard_role(name, callback)
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
        (r"^SUDO_GUIDE$", lambda update, context: staff_guide_callback(update, context, "sudo")),
        (r"^UPLOADER_GUIDE$", lambda update, context: staff_guide_callback(update, context, "uploader")),
        (r"^setprofile(?:ok|no):", waifu.setprofile_callback),
    ]
    for pattern, callback in callback_map:
        app.add_handler(CallbackQueryHandler(callback, pattern=pattern))
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^(?:OPEN_HELP|HELP:.*)$"))

    app.add_handler(CallbackQueryHandler(waifu.collection_callback, pattern=r"^(?:col|colimg|colclose|colimgclose):|^colimgnoop$"))
    app.add_handler(CallbackQueryHandler(waifu.dmode_callback, pattern=r"^(?:dmode:|dmrarity:|dmchoices:|dmback:|dmset:|dmpick:|dmclose:|dmnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.find_callback, pattern=r"^(?:find:|finddel:|findnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.dfind_callback, pattern=r"^(?:dfind:|dfinddel:|dfindnoop$)"))
    app.add_handler(CallbackQueryHandler(waifu.waifu_callback, pattern=r"^(?:fav(?:inline|confirm|cancel|list|pick|listclose):|favnoop$)"))
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
