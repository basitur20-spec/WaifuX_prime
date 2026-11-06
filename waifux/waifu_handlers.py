"""Waifu catalogue, collection and reward commands.

The module deliberately keeps all ownership/economy writes in storage.py.
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from . import storage
from legacy import partial_commands as legacy

RARITIES = {
    "Starter": ("⚪", (20_000, 25_000)),
    "Rising": ("🟢", (25_000, 33_000)),
    "Shiny": ("🟣", (35_000, 45_000)),
    "Ultimate": ("🟡", (50_000, 60_000)),
    "BeachArc": ("🏖️", (600_000, 850_000)),
    "ChibiArc": ("👼", (400_000, 550_000)),
    "WinterArc": ("❄️", (650_000, 850_000)),
    "LoveArc": ("💞", (800_000, 1_100_000)),
    "DarkArc": ("🎃", (600_000, 850_000)),
    "ChristmasArc": ("🎄", (600_000, 750_000)),
    "RoyalArc": ("👑", (475_000, 650_000)),
    "NeonArc": ("💫", (400_000, 600_000)),
    "CelestialArc": ("🪽", (550_000, 810_000)),
    "CrossArc": ("🧬", (800_000, 1_100_000)),
    "MangaArc": ("✨", (300_000, 450_000)),
    "LimitedArc": ("🔮", (750_000, 1_000_000)),
    "SpecialArc": ("🫧", (800_000, 1_300_000)),
    "DivineArc": ("🥵", (800_000, 1_300_000)),
    "CinemaArc": ("🎥", (800_000, 1_300_000)),
}
RARITY_WEIGHTS = {
    "Starter": 50, "Rising": 50, "Shiny": 50, "Ultimate": 50,
    "BeachArc": 13, "ChibiArc": 17, "WinterArc": 19, "LoveArc": 3,
    "DarkArc": 5, "ChristmasArc": 15, "RoyalArc": 35, "NeonArc": 25,
    "CelestialArc": 35, "CrossArc": 4, "MangaArc": 50, "LimitedArc": 8,
    "SpecialArc": 5, "DivineArc": 4, "CinemaArc": 4,
}
OWNER_ID = 0
MESSAGE_COUNTS = defaultdict(int)
RECENT_MESSAGES = defaultdict(deque)
RARITY_ORDER = list(RARITIES)


def configure(owner_id: int) -> None:
    global OWNER_ID
    OWNER_ID = int(owner_id)
    storage.init_db()


def _owner(uid: int) -> bool:
    return int(uid) == OWNER_ID


def _sudo(uid: int) -> bool:
    return _owner(uid) or bool(legacy.is_sudo(int(uid)))


def _uploader(uid: int) -> bool:
    return _owner(uid) or bool(legacy.is_uploader(int(uid)))


def _staff(uid: int) -> bool:
    return _sudo(uid) or _uploader(uid)


def _fmt(n: int) -> str:
    return f"{int(n):,}"


def _rarity_name(raw: str) -> str | None:
    key = re.sub(r"[^a-z]", "", raw.lower())
    if raw.strip().isdigit():
        index = int(raw.strip()) - 1
        return RARITY_ORDER[index] if 0 <= index < len(RARITY_ORDER) else None
    return next((r for r in RARITIES if re.sub(r"[^a-z]", "", r.lower()) == key), None)


def _display(w) -> str:
    emoji = RARITIES.get(w["rarity"], ("✨",))[0]
    return (
        f"🎭 Name: {w['name']}\n"
        f"📺 Anime: {w['anime']}\n"
        f"💫 Rarity: {emoji} {w['rarity']}\n"
        f"🆔 ID: {w['waifu_id']}\n"
        f"💰 Price: {_fmt(w['price'])}"
    )


def _random_waifu(rarities: list[str] | None = None, respect_spawn_settings: bool = False):
    available = []
    for rarity in (rarities or RARITY_ORDER):
        if respect_spawn_settings:
            setting = storage.raw_connect()
            try:
                row = setting.execute(
                    "SELECT spawn_enabled FROM rarity_settings WHERE rarity=?", (rarity,)
                ).fetchone()
                if row and not row["spawn_enabled"]:
                    continue
            finally:
                setting.close()
        pool = storage.list_waifus(rarity, 500)
        with storage.connect() as con:
            active_ids = {row["waifu_id"] for row in con.execute("SELECT waifu_id FROM auctions")}
        if pool:
            available.extend((rarity, w) for w in pool if w["waifu_id"] not in active_ids)
    if not available:
        return None
    names = list(dict.fromkeys(r for r, _ in available))
    weights = [RARITY_WEIGHTS.get(r, 1) for r in names]
    chosen_rarity = random.choices(names, weights=weights, k=1)[0]
    pool = [w for r, w in available if r == chosen_rarity]
    return random.choice(pool)


def _parse_upload_details(raw: str) -> dict:
    data = {}
    for line in raw.splitlines():
        match = re.match(r"\s*(name|rarity|anime|price|id|aliases)\s*[:=]?\s+(.+?)\s*$", line, re.I)
        if match:
            data[match.group(1).lower()] = match.group(2).strip()
    # Also accept the documented three-line plain format.
    if not data:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(lines) >= 3:
            data = {"name": lines[0], "rarity": lines[1], "anime": lines[2]}
            if len(lines) >= 4:
                data["price"] = lines[3]
    return data


async def upload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    uid = update.effective_user.id
    if not _uploader(uid):
        return
    photo = msg.photo[-1] if msg.photo else None
    details_text = msg.caption or ""
    if msg.reply_to_message:
        photo_msg = msg.reply_to_message
        if photo_msg.photo:
            photo = photo_msg.photo[-1]
        details_text = msg.text or msg.caption or ""
    if not photo:
        await msg.reply_text(
            "Image ke sath caption mein details likho ya image ko reply karke /upload use karo.\n\n"
            "Name: Character Name\nRarity: Shiny\nAnime: Anime Name\nPrice: 40000\nID: 1234"
        )
        return
    data = _parse_upload_details(details_text)
    name, anime = data.get("name"), data.get("anime")
    rarity = _rarity_name(data.get("rarity", ""))
    if not name or not anime or not rarity:
        await msg.reply_text("Upload details incomplete/invalid hain. Name, Rarity aur Anime zaroor do.")
        return
    low, high = RARITIES[rarity][1]
    try:
        price = int(re.sub(r"[^0-9]", "", data.get("price", ""))) if data.get("price") else random.randint(low, high)
        if not low <= price <= high:
            raise ValueError(f"{rarity} ki allowed price {_fmt(low)}–{_fmt(high)} hai.")
        wid = data.get("id") or ""
        if not wid:
            used = {str(w["waifu_id"]) for w in storage.list_waifus(limit=10000)}
            free = [str(n).zfill(4) for n in range(1000, 10000) if str(n).zfill(4) not in used]
            if not free:
                raise ValueError("Waifu ID space khatam ho gaya.")
            wid = random.choice(free)
        if len(wid) != 4 or not wid.isdigit():
            raise ValueError("ID exactly 4 digits ka hona chahiye.")
        storage.add_waifu(wid, name, anime, rarity, price, photo.file_id, uid, [a.strip() for a in data.get('aliases', '').split(',') if a.strip()])
        reward = int(price * 0.03)
        if reward:
            storage.change_balance(uid, cash_delta=reward)
        storage.add_audit(uid, "waifu_upload", details={"waifu_id": wid, "rarity": rarity})
    except (ValueError, Exception) as exc:
        await msg.reply_text(f"❌ Upload reject ho gaya: {exc}")
        return
    w = storage.get_waifu(wid)
    await msg.reply_photo(
        photo=photo.file_id,
        caption=f"🌐 CHARACTER INFO\n{_display(w)}\n\n🎉 Upload Successful!\n"
                f"You earned +{_fmt(reward)} coins (3% uploader bonus)."
    )
    try:
        await context.bot.send_photo(
            chat_id="@waifuxprime_updates",
            photo=photo.file_id,
            caption=f"🌸 New Waifu Uploaded\n{_display(w)}"
        )
    except Exception:
        # Channel delivery is best-effort; successful DB save is not rolled back.
        pass


def _collection_for_user(uid: int):
    with storage.connect() as con:
        profile = con.execute("SELECT display_mode,display_value FROM user_profiles WHERE user_id=?", (uid,)).fetchone()
    if not profile or profile["display_mode"] == "default":
        return storage.collection(uid)
    mode, value = profile["display_mode"], profile["display_value"]
    if mode == "rarity":
        return storage.collection(uid, rarity=value)
    if mode == "anime":
        return storage.collection(uid, anime=value)
    if mode == "character":
        return storage.collection(uid, name=value)
    return storage.collection(uid)


async def collection_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    owner_id = uid
    if context.args:
        target = context.args[0].lstrip("@")
        with storage.connect() as con:
            if target.isdigit():
                profile = con.execute("SELECT user_id FROM user_profiles WHERE bot_user_id=? OR user_id=?", (target, int(target))).fetchone()
            else:
                profile = con.execute("SELECT user_id FROM user_profiles WHERE lower(username)=lower(?)", (target,)).fetchone()
        if not profile:
            await update.effective_message.reply_text("User not found. They must have started the bot first.")
            return
        owner_id = int(profile["user_id"])
    rows = _collection_for_user(owner_id)
    if not rows:
        await update.effective_message.reply_text("📚 This collection is empty.")
        return
    if owner_id == uid:
        favourites = [w for w in storage.collection(uid) if w["is_favorite"]]
        if favourites:
            fav = favourites[0]
            await update.effective_message.reply_photo(fav["image_file_id"], caption=f"❤️ Your favourite waifu\n{_display(fav)}")
    await _send_collection(update.effective_message, owner_id, 0, rows, viewer_id=uid)


async def _send_collection(message, owner_id: int, page: int, rows=None, viewer_id=None):
    rows = rows if rows is not None else _collection_for_user(owner_id)
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    chunk = rows[page * page_size:(page + 1) * page_size]
    viewer_id = owner_id if viewer_id is None else viewer_id
    if owner_id == viewer_id:
        title = "YOUR WAIFU COLLECTION"
    else:
        with storage.connect() as con:
            profile = con.execute("SELECT username,first_name,bot_user_id FROM user_profiles WHERE user_id=?", (owner_id,)).fetchone()
        owner_name = f"@{profile['username']}" if profile and profile["username"] else (profile["first_name"] if profile else f"User {storage.ensure_bot_user_id(owner_id)}")
        title = f"{owner_name}'S WAIFU COLLECTION (VIEW ONLY)"
    lines = [f"📚 {title}", f"Page {page + 1}/{pages}", ""]
    last_anime = None
    for w in chunk:
        if w["anime"] != last_anime:
            lines.append(f"🎬 {w['anime']}")
            last_anime = w["anime"]
        icon = RARITIES.get(w["rarity"], ("✨",))[0]
        lines.append(f"{'❤️ ' if w['is_favorite'] else ''}🆔 {w['waifu_id']} | {icon} | {w['name']}")
    buttons = []
    if owner_id == viewer_id:
        buttons.append([
            InlineKeyboardButton("◀ Prev", callback_data=f"col:{owner_id}:{max(0,page-1)}"),
            InlineKeyboardButton("Next ▶", callback_data=f"col:{owner_id}:{min(pages-1,page+1)}")
        ])
    buttons.append([InlineKeyboardButton("✨ Waifus", callback_data=f"colimg:{owner_id}:{viewer_id}:{page}")])
    if owner_id == viewer_id:
        buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"colclose:{owner_id}:{viewer_id}")])
    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


def _collection_image_keyboard(owner_id: int, viewer_id: int, page: int, count: int):
    pages = max(1, (count + 9) // 10)
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"colimg:{owner_id}:{viewer_id}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📑 {page+1}/{pages}", callback_data="colimgnoop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"colimg:{owner_id}:{viewer_id}:{page+1}"))
    buttons.append(nav)
    if owner_id == viewer_id:
        buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"colimgclose:{owner_id}:{viewer_id}")])
    return InlineKeyboardMarkup(buttons)


async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.data == "colimgnoop":
        await q.answer()
        return
    parts = q.data.split(":")
    action = parts[0]
    owner_id = int(parts[1])
    if action == "colclose" or action == "colimgclose":
        viewer_id = int(parts[2])
        if q.from_user.id != viewer_id:
            await q.answer("This control is not yours.", show_alert=True)
            return
        await q.answer()
        await q.message.delete()
        return
    if action == "colimg":
        viewer_id, page = int(parts[2]), int(parts[3])
        if q.from_user.id != viewer_id:
            await q.answer("This image view is not yours.", show_alert=True)
            return
        rows = _collection_for_user(owner_id)
        images = [w for w in rows if w["image_file_id"]]
        pages = max(1, (len(images) + 9) // 10)
        page = max(0, min(page, pages - 1))
        await q.answer()
        await q.edit_message_text(
            f"🖼️ WAIFUS | Page {page+1}/{pages}",
            reply_markup=_collection_image_keyboard(owner_id, viewer_id, page, len(images))
        )
        for w in images[page * 10:(page + 1) * 10]:
            await q.message.reply_photo(w["image_file_id"])
        return
    if q.from_user.id != owner_id:
        await q.answer("Only the collection owner can change pages.", show_alert=True)
        return
    await q.answer()
    rows = _collection_for_user(owner_id)
    page = int(parts[2])
    await q.edit_message_text(
        _collection_text(rows, page, owner_id),
        reply_markup=_collection_keyboard(owner_id, page, len(rows))
    )


def _collection_text(rows, page, owner_id):
    pages = max(1, (len(rows) + 9) // 10)
    lines = [f"📚 WAIFU COLLECTION", f"Page {page+1}/{pages}", ""]
    last = None
    for w in rows[page*10:(page+1)*10]:
        if last != w["anime"]:
            lines.append(f"🎬 {w['anime']}")
            last = w["anime"]
        lines.append(f"{'❤️ ' if w['is_favorite'] else ''}🆔 {w['waifu_id']} | {RARITIES[w['rarity']][0]} | {w['name']}")
    return "\n".join(lines)


def _collection_keyboard(uid, page, count):
    pages = max(1, (count + 9) // 10)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀ Prev", callback_data=f"col:{uid}:{max(0,page-1)}"),
         InlineKeyboardButton("Next ▶", callback_data=f"col:{uid}:{min(pages-1,page+1)}")],
        [InlineKeyboardButton("✨ Waifus", callback_data=f"colimg:{uid}:{uid}:{page}")],
        [InlineKeyboardButton("❌ Close", callback_data=f"colclose:{uid}:{uid}")]
    ])


async def fav_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Usage: /fav <waifu_id>")
        return
    w = storage.owned_waifu(update.effective_user.id, context.args[0])
    if not w:
        await update.effective_message.reply_text("😔 Ye waifu tumhari collection mein nahi hai.")
        return
    token = storage.create_pending(update.effective_user.id, "favorite", {"waifu_id": w["waifu_id"]}, 60)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("INLINE", callback_data=f"favinline:{token}"),
        InlineKeyboardButton("COLLECTION", callback_data=f"favconfirm:{token}"),
        InlineKeyboardButton("CANCEL", callback_data=f"favcancel:{token}")
    ]])
    await update.effective_message.reply_photo(
        w["image_file_id"],
        caption=f"Do you really want to set {w['name']} as your favourite waifu?",
        reply_markup=keyboard
    )


async def waifu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data.split(":")
    action, token = data[0], data[1]
    if action.startswith("fav"):
        pending = storage.get_pending(token, q.from_user.id, "favorite")
        if not pending:
            await q.answer("This request expired or belongs to another user.", show_alert=True)
            return
        import json
        wid = json.loads(pending["payload"])["waifu_id"]
        if action == "favcancel":
            storage.finish_pending(token, "cancelled")
            await q.answer("Favourite cancelled.")
            await q.message.delete()
        else:
            storage.set_favorite(q.from_user.id, wid)
            storage.finish_pending(token)
            w = storage.get_waifu(wid)
            await q.answer("Favourite updated.")
            if action == "favinline":
                await q.edit_message_caption(
                    caption=f"❤️ {w['name']} is now your favourite. Open inline mode:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Open Inline Collection", switch_inline_query_current_chat=f"waifu {w['name']}")
                    ]])
                )
            else:
                await q.edit_message_caption(caption=f"❤️ {w['name']} is now your favourite.")
                rows = storage.collection(q.from_user.id)
                await _send_collection(q.message, q.from_user.id, 0, rows, q.from_user.id)


async def inline_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from telegram import InlineQueryResultCachedPhoto
    query = update.inline_query
    term = query.query.strip()
    rows = _collection_for_user(query.from_user.id)
    if term:
        bits = term.split(maxsplit=1)
        term = bits[1] if len(bits) == 2 and bits[0].lower() == "waifu" else term
        rows = [w for w in rows if term.casefold() in w["name"].casefold() or term.casefold() in w["anime"].casefold()]
    results = [
        InlineQueryResultCachedPhoto(
            id=f"{w['waifu_id']}-{i}", photo_file_id=w["image_file_id"],
            title=w["name"], description=f"{w['rarity']} | {w['anime']}"
        )
        for i, w in enumerate(rows[:50])
    ]
    await query.answer(results, cache_time=1, is_personal=True)


async def waifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    w = _random_waifu(["Starter", "Rising", "Shiny", "Ultimate", "RoyalArc"])
    if not w:
        await update.effective_message.reply_text("Abhi reward pool mein waifus available nahi hain.")
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT expires_at FROM cooldowns WHERE user_id=? AND action='daily_waifu'", (uid,)).fetchone()
        left = max(0, int(row["expires_at"]) - storage.now()) if row else 0
        if left:
            con.rollback()
            await update.effective_message.reply_text(f"⏳ Please wait {left//3600:02d}:{(left%3600)//60:02d}:{left%60:02d} before claiming your next waifu.")
            return
        con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (uid, w["waifu_id"], storage.now(), "daily"))
        con.execute("INSERT INTO cooldowns(user_id,action,expires_at) VALUES (?,?,?) ON CONFLICT(user_id,action) DO UPDATE SET expires_at=excluded.expires_at", (uid, "daily_waifu", storage.now()+12*60*60))
        con.execute("INSERT INTO transactions(tx_id,actor_id,action,waifu_id,created_at) VALUES (?,?,?,?,?)", (__import__("uuid").uuid4().hex, uid, "daily_waifu", w["waifu_id"], storage.now()))
        con.commit()
    await update.effective_message.reply_photo(
        w["image_file_id"],
        caption=f"🎉 Congratulations {update.effective_user.first_name}! You won!\n{_display(w)}"
    )


async def hunt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg.chat.type == ChatType.PRIVATE:
        await msg.reply_text("Hunt sirf groups mein active hota hai.")
        return
    supplied = " ".join(context.args).casefold().strip()
    if not supplied:
        await msg.reply_text("Usage: /hunt <character name>")
        return
    con = storage.raw_connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        spawn = con.execute("SELECT * FROM active_spawns WHERE chat_id=?", (msg.chat_id,)).fetchone()
        if not spawn or spawn["expires_at"] <= storage.now():
            if spawn:
                con.execute("DELETE FROM active_spawns WHERE chat_id=?", (msg.chat_id,))
            con.commit()
            await msg.reply_text("❌ NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEXT SPAWN.")
            return
        w = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (spawn["waifu_id"],)).fetchone()
        if not w:
            con.execute("DELETE FROM active_spawns WHERE chat_id=?", (msg.chat_id,))
            con.commit()
            await msg.reply_text("❌ NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEXT SPAWN.")
            return
        names = [w["name"], *(__import__("json").loads(w["aliases"] or "[]"))]
        words = {part.casefold() for name in names for part in re.findall(r"[\w]+", name)}
        supplied_words = set(re.findall(r"[\w]+", supplied))
        if not (supplied_words & words) and supplied != w["name"].casefold():
            con.rollback()
            await msg.reply_text("❌ NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEXT SPAWN.")
            return
        con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (msg.from_user.id, w["waifu_id"], storage.now(), "hunt"))
        con.execute("DELETE FROM active_spawns WHERE chat_id=?", (msg.chat_id,))
        con.execute("INSERT INTO transactions(tx_id,actor_id,action,waifu_id,created_at) VALUES (?,?,?,?,?)", (__import__("uuid").uuid4().hex, msg.from_user.id, "hunt", w["waifu_id"], storage.now()))
        con.commit()
    finally:
        con.close()
    await msg.reply_photo(
        w["image_file_id"],
        caption=f"🎉 Congratulations {msg.from_user.first_name}! You got a new waifu!\n{_display(w)}\n\nCheck /collection now.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("COLLECTION 🔥", callback_data=f"col:{msg.from_user.id}:0")]])
    )


async def group_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or msg.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP) or not msg.from_user or msg.from_user.is_bot:
        return
    if msg.text and msg.text.startswith("/"):
        return
    uid, chat_id = msg.from_user.id, msg.chat_id
    now = time.monotonic()
    q = RECENT_MESSAGES[(chat_id, uid)]
    q.append(now)
    while q and now - q[0] > 5:
        q.popleft()
    if len(q) >= 5:
        try:
            await context.bot.restrict_chat_member(
                chat_id, uid, permissions=__import__("telegram").ChatPermissions(can_send_messages=False),
                until_date=int(time.time()) + 300
            )
            await msg.reply_text(f"{msg.from_user.first_name}, your messages won't be counted for 5 minutes.\nYou cannot spam to get characters.")
        except Exception:
            pass
        q.clear()
        return
    con = storage.raw_connect()
    try:
        active = con.execute("SELECT 1 FROM active_spawns WHERE chat_id=? AND expires_at>?", (chat_id, storage.now())).fetchone()
        if active:
            return
        con.execute("INSERT OR IGNORE INTO group_settings(chat_id) VALUES (?)", (chat_id,))
        settings = con.execute("SELECT * FROM group_settings WHERE chat_id=?", (chat_id,)).fetchone()
        if not settings or not settings["enabled"]:
            return
        count = MESSAGE_COUNTS[chat_id] + 1
        MESSAGE_COUNTS[chat_id] = count
        if count < 50 or storage.now() < settings["next_spawn_at"]:
            return
        w = _random_waifu(respect_spawn_settings=True)
        if not w:
            return
        timestamp = storage.now()
        con.execute(
            "INSERT OR REPLACE INTO active_spawns(chat_id,waifu_id,spawned_at,expires_at) VALUES (?,?,?,?)",
            (chat_id, w["waifu_id"], timestamp, timestamp + 300)
        )
        con.execute("UPDATE group_settings SET next_spawn_at=? WHERE chat_id=?", (timestamp + settings["spawn_interval"] * 60, chat_id))
        MESSAGE_COUNTS[chat_id] = 0
    finally:
        con.close()
    await context.bot.send_photo(
        chat_id=chat_id, photo=w["image_file_id"], has_spoiler=True,
        caption="✨ A new character has appeared!\nUse /hunt (name) to add it to your collection."
    )


async def spawn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /spawn <rarity> on/off")
        return
    rarity, status = _rarity_name(context.args[0]), context.args[1].lower()
    if not rarity or status not in {"on", "off"}:
        await update.effective_message.reply_text("Rarity ya on/off value sahi nahi.")
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO rarity_settings(rarity,spawn_enabled) VALUES (?,?)
            ON CONFLICT(rarity) DO UPDATE SET spawn_enabled=excluded.spawn_enabled""",
            (rarity, int(status == "on"))
        )
    await update.effective_message.reply_text(f"{RARITIES[rarity][0]} {rarity} spawning {status.upper()}.")


async def changetime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _sudo(update.effective_user.id):
        return
    if update.effective_message.chat.type == ChatType.PRIVATE:
        await update.effective_message.reply_text("Ye command group mein use karo: /changetime <2-120 minutes>")
        return
    try:
        minutes = int(context.args[0])
        if not 2 <= minutes <= 120:
            raise ValueError
    except (ValueError, IndexError):
        await update.effective_message.reply_text("Usage: /changetime <2-120 minutes>")
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO group_settings(chat_id,spawn_interval,next_spawn_at,enabled)
            VALUES (?,?,?,1) ON CONFLICT(chat_id) DO UPDATE SET
            spawn_interval=excluded.spawn_interval,next_spawn_at=excluded.next_spawn_at,enabled=1""",
            (update.effective_chat.id, minutes, storage.now() + minutes * 60)
        )
    await update.effective_message.reply_text(f"✅ Spawn interval set to every {minutes} minutes.")


async def marriage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    left = storage.cooldown_left(uid, "marriage")
    if left:
        await update.effective_message.reply_text(f"⏳ Try again in {left//60}m {left%60}s.")
        return
    storage.set_cooldown(uid, "marriage", 3600)
    if random.random() >= 0.35:
        await update.effective_message.reply_text(f"{update.effective_user.first_name}, your marriage proposal was rejected and she ran away! 🤡")
        return
    w = _random_waifu(["Shiny", "Ultimate"])
    if not w:
        await update.effective_message.reply_text("Marriage reward pool mein abhi waifu nahi.")
        return
    storage.add_to_collection(uid, w["waifu_id"], "marriage")
    await update.effective_message.reply_photo(w["image_file_id"], caption=f"💍 Congratulations! You are now married!\n{_display(w)}")


async def propose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    left = storage.cooldown_left(uid, "propose")
    if left:
        await update.effective_message.reply_text(f"⏳ Cooldown: {left//60}m {left%60}s.")
        return
    cash, _ = storage.get_balance(uid)
    if cash < 30_000:
        await update.effective_message.reply_text("YOU NEED 30,000 CASH💸 TO PROPOSE.")
        return
    storage.change_balance(uid, cash_delta=-30_000)
    storage.set_cooldown(uid, "propose", 300)
    intro = await update.effective_message.reply_photo(
        "https://t.me/movieandweb_s_group/17959",
        caption=f"{update.effective_user.first_name} 💫 The moment you've been waiting for 💫"
    )
    processing = await intro.reply_text("ᴘʀᴏᴘᴏꜱɪɴɢ ʜᴇʀ.... 💍")
    await asyncio.sleep(random.randint(3, 5))
    if random.uniform(0, 100) <= random.randint(35, 45):
        w = _random_waifu(["ChristmasArc", "RoyalArc", "NeonArc", "CelestialArc"])
        if w:
            storage.add_to_collection(uid, w["waifu_id"], "propose")
            await processing.reply_photo(w["image_file_id"], caption=f"💖 {w['name']} has accepted your proposal!\n{_display(w)}")
            return
    rejection = random.choice([
        ("https://t.me/movieandweb_s_group/18022", "You've been friend-zoned so hard, you're now the mayor of friend zone city! 🏙️"),
        ("https://t.me/movieandweb_s_group/17925", "Breaking news: local simp gets rejected so hard! 🥲🛏️")
    ])
    await processing.reply_photo(rejection[0], caption=rejection[1])


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requester = update.effective_user
    target_id = requester.id
    if context.args:
        search = context.args[0].lstrip("@")
        with storage.connect() as con:
            if search.isdigit():
                found = con.execute("SELECT * FROM user_profiles WHERE bot_user_id=? OR user_id=?", (search, int(search))).fetchone()
            else:
                found = con.execute("SELECT * FROM user_profiles WHERE lower(username)=lower(?)", (search,)).fetchone()
        if not found:
            await update.effective_message.reply_text("⚠️ User not found. User ko pehle bot start karna hoga.")
            return
        target_id = int(found["user_id"])
    bot_user_id = storage.ensure_bot_user_id(target_id)
    with storage.connect() as con:
        profile = con.execute("SELECT * FROM user_profiles WHERE user_id=?", (target_id,)).fetchone()
    rows = storage.collection(target_id)
    cash, diamonds = storage.get_balance(target_id)
    name = (profile["first_name"] if profile else None) or str(target_id)
    username = (profile["username"] if profile else None)
    text = (
        f"👤 USER PROFILE\n\n🆔 User ID: {bot_user_id}\n👤 Name: {name}\n"
        f"🔗 Username: @{username or 'N/A'}\n\n💰 Balance: {_fmt(cash)}\n"
        f"💎 Diamonds: {_fmt(diamonds)}\n💖 Waifus Collected: {len(rows)} / {len(storage.list_waifus(limit=10000))}"
    )
    if profile and profile["profile_waifu_id"]:
        w = storage.get_waifu(profile["profile_waifu_id"])
        if w:
            text += f"\n\n🌸 Profile Waifu: {w['name']} | {w['rarity']} | {w['anime']}"
    if profile and profile["profile_photo"]:
        await update.effective_message.reply_photo(profile["profile_photo"], caption=text)
    elif profile and profile["profile_waifu_id"]:
        w = storage.get_waifu(profile["profile_waifu_id"])
        if w:
            await update.effective_message.reply_photo(w["image_file_id"], caption=text)
            return
        await update.effective_message.reply_text(text)
    else:
        await update.effective_message.reply_text(text)


def _dmode_main_keyboard(uid: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("DEFAULT", callback_data=f"dmode:{uid}:default"),
         InlineKeyboardButton("CHARACTERS", callback_data=f"dmode:{uid}:character")],
        [InlineKeyboardButton("RARITY", callback_data=f"dmode:{uid}:rarity"),
         InlineKeyboardButton("ANIME", callback_data=f"dmode:{uid}:anime")],
        [InlineKeyboardButton("❌ Close", callback_data=f"dmclose:{uid}")]
    ])


def _dmode_rarity_keyboard(uid: int, page: int):
    page_size = 12
    pages = (len(RARITY_ORDER) + page_size - 1) // page_size
    values = RARITY_ORDER[page * page_size:(page + 1) * page_size]
    rows = []
    for index in range(0, len(values), 4):
        rows.append([
            InlineKeyboardButton(
                f"{RARITIES[name][0]} {name}",
                callback_data=f"dmset:{uid}:rarity:{name}"
            ) for name in values[index:index+4]
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Back Page", callback_data=f"dmrarity:{uid}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📑 {page+1}/{pages}", callback_data="dmnoop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next Page ➡", callback_data=f"dmrarity:{uid}:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("Back", callback_data=f"dmback:{uid}")])
    return InlineKeyboardMarkup(rows)


def _dmode_choices_keyboard(uid: int, token: str, page: int, values: list[str]):
    count = len(values)
    pages = max(1, (count + 11) // 12)
    rows = []
    start = page * 12
    for index in range(start, min(start + 12, count), 2):
        row = [InlineKeyboardButton(
            values[index][:40],
            callback_data=f"dmpick:{uid}:{token}:{index}"
        )]
        if index + 1 < min(start + 12, count):
            row.append(InlineKeyboardButton(
                values[index+1][:40],
                callback_data=f"dmpick:{uid}:{token}:{index+1}"
            ))
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Back Page", callback_data=f"dmchoices:{uid}:{token}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📑 {page+1}/{pages}", callback_data="dmnoop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next Page ➡", callback_data=f"dmchoices:{uid}:{token}:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("Back", callback_data=f"dmback:{uid}")])
    return InlineKeyboardMarkup(rows)


async def dmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    with storage.connect() as con:
        profile = con.execute("SELECT display_mode,display_value FROM user_profiles WHERE user_id=?", (uid,)).fetchone()
    current = f"{profile['display_mode']}: {profile['display_value']}" if profile else "default"
    await update.effective_message.reply_text(
        f"🎨 SET YOUR WAIFU'S MODE\nCurrent mode: {current}\nChoose a sorting/filter mode:",
        reply_markup=_dmode_main_keyboard(uid)
    )


async def dmode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    parts = q.data.split(":")
    action = parts[0]
    if q.data == "dmnoop":
        await q.answer()
        return
    uid = int(parts[1])
    if q.from_user.id != uid:
        await q.answer("These settings belong to another user.", show_alert=True)
        return
    if action == "dmclose":
        await q.answer()
        await q.message.delete()
        return
    if action == "dmback":
        await q.answer()
        await q.edit_message_text("🎨 SET YOUR WAIFU'S MODE", reply_markup=_dmode_main_keyboard(uid))
        return
    if action == "dmode":
        mode = parts[2]
        await q.answer()
        if mode == "default":
            with storage.connect() as con:
                con.execute(
                    "INSERT INTO user_profiles(user_id,display_mode,display_value,updated_at) VALUES (?,?,NULL,?) ON CONFLICT(user_id) DO UPDATE SET display_mode='default',display_value=NULL,updated_at=excluded.updated_at",
                    (uid, "default", storage.now())
                )
            await q.edit_message_text("✅ Default collection mode restored. Use /collection.")
            return
        if mode == "rarity":
            await q.edit_message_text("💫 CHOOSE A RARITY TO FILTER YOUR COLLECTION:", reply_markup=_dmode_rarity_keyboard(uid, 0))
            return
        rows = storage.collection(uid)
        field = "name" if mode == "character" else "anime"
        values = list(dict.fromkeys(str(row[field]) for row in rows))
        if not values:
            await q.edit_message_text("Your collection is empty.", reply_markup=_dmode_main_keyboard(uid))
            return
        token = storage.create_pending(uid, "dmode_choices", {"mode": mode, "values": values}, 600)
        label = "CHARACTER" if mode == "character" else "ANIME"
        await q.edit_message_text(
            f"🎭 CHOOSE {label} TO FILTER BY:",
            reply_markup=_dmode_choices_keyboard(uid, token, 0, values)
        )
        return
    if action == "dmrarity":
        page = int(parts[2])
        await q.answer()
        await q.edit_message_text("💫 CHOOSE A RARITY TO FILTER YOUR COLLECTION:", reply_markup=_dmode_rarity_keyboard(uid, page))
        return
    if action == "dmchoices":
        token, page = parts[2], int(parts[3])
        pending = storage.get_pending(token, uid, "dmode_choices")
        if not pending:
            await q.answer("Selection expired. Open /dmode again.", show_alert=True)
            return
        data = __import__("json").loads(pending["payload"])
        values = data["values"]
        await q.answer()
        await q.edit_message_text(
            f"CHOOSE {data['mode'].upper()} TO FILTER BY:",
            reply_markup=_dmode_choices_keyboard(uid, token, page, values)
        )
        return
    if action == "dmset":
        mode, value = parts[2], ":".join(parts[3:])
        if not storage.collection(uid, rarity=value if mode == "rarity" else None,
                                  anime=value if mode == "anime" else None,
                                  name=value if mode == "character" else None):
            await q.answer("You don't own any waifu matching this selection.", show_alert=True)
            return
        with storage.connect() as con:
            con.execute(
                """INSERT INTO user_profiles(user_id,display_mode,display_value,updated_at) VALUES (?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET display_mode=excluded.display_mode,
                display_value=excluded.display_value,updated_at=excluded.updated_at""",
                (uid, mode, value, storage.now())
            )
        await q.answer("Collection mode updated.")
        await q.edit_message_text(f"✅ Collection mode set to {mode}: {value}. Use /collection to view.")
        return
    if action == "dmpick":
        token, index = parts[2], int(parts[3])
        pending = storage.get_pending(token, uid, "dmode_choices")
        if not pending:
            await q.answer("Selection expired. Open /dmode again.", show_alert=True)
            return
        data = __import__("json").loads(pending["payload"])
        values = data["values"]
        if not 0 <= index < len(values):
            await q.answer("Invalid selection.", show_alert=True)
            return
        value, mode = values[index], data["mode"]
        with storage.connect() as con:
            con.execute(
                """INSERT INTO user_profiles(user_id,display_mode,display_value,updated_at) VALUES (?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET display_mode=excluded.display_mode,
                display_value=excluded.display_value,updated_at=excluded.updated_at""",
                (uid, mode, value, storage.now())
            )
        storage.finish_pending(token)
        await q.answer("Collection mode updated.")
        await q.edit_message_text(f"✅ Collection mode set to {mode}: {value}. Use /collection to view.")


async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /find <waifu_id>")
        return
    wid = context.args[0]
    w = storage.get_waifu(wid)
    if not w:
        await update.effective_message.reply_text("THE WAIFU ID IS NOT FOUND IN BOT DATABASE.")
        return
    total, rows, total_users = _find_users_page(wid, 0)
    if not rows:
        await update.effective_message.reply_text("❌ NO CHARACTER FOUND WITH THIS 🆔.")
        return
    caption, pages = _find_caption(w, 0)
    await update.effective_message.reply_photo(
        w["image_file_id"], caption=caption,
        reply_markup=_find_keyboard(update.effective_user.id, wid, 0, pages)
    )


async def find_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.data == "findnoop":
        await q.answer()
        return
    parts = q.data.split(":")
    if parts[0] == "finddel":
        if q.from_user.id != int(parts[1]):
            await q.answer("Only the search owner can discard this result.", show_alert=True)
            return
        await q.answer()
        await q.message.delete()
        return
    _, owner_raw, wid, page_raw = parts
    if q.from_user.id != int(owner_raw):
        await q.answer("Only the search owner can use these buttons.", show_alert=True)
        return
    w = storage.get_waifu(wid)
    if not w:
        await q.answer("Waifu no longer exists.", show_alert=True)
        return
    page = int(page_raw)
    caption, pages = _find_caption(w, page)
    await q.answer()
    await q.edit_message_caption(caption=caption, reply_markup=_find_keyboard(q.from_user.id, wid, page, pages))


def _dfind_page_text(rows, page: int):
    selected = rows[page * 15:(page + 1) * 15]
    lines = ["🔎 WAIFU SEARCH RESULTS", f"Page {page+1}/{max(1,(len(rows)+14)//15)}"]
    for rarity in RARITY_ORDER:
        group = [w for w in selected if w["rarity"] == rarity]
        if group:
            lines.append(f"\n{RARITIES[rarity][0]} {rarity}")
            lines.extend(f"🆔 {w['waifu_id']} | {w['name']} — {w['anime']}" for w in group)
    return "\n".join(lines)


def _dfind_keyboard(uid: int, token: str, page: int, count: int):
    pages = max(1, (count + 14) // 15)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Back Page", callback_data=f"dfind:{uid}:{token}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📑 {page+1}/{pages}", callback_data="dfindnoop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"dfind:{uid}:{token}:{page+1}"))
    return InlineKeyboardMarkup([nav, [InlineKeyboardButton("🗑 Discard", callback_data=f"dfinddel:{uid}:{token}")]])


async def dfind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /dfind <character name>")
        return
    term = " ".join(context.args).casefold()
    matches = [w for w in storage.list_waifus(limit=10000) if term in w["name"].casefold() or term in w["anime"].casefold()]
    if not matches:
        await update.effective_message.reply_text("No uploaded waifus match that name.")
        return
    token = storage.create_pending(update.effective_user.id, "dfind", {"ids": [w["waifu_id"] for w in matches]}, 600)
    await update.effective_message.reply_text(
        _dfind_page_text(matches, 0),
        reply_markup=_dfind_keyboard(update.effective_user.id, token, 0, len(matches))
    )


async def dfind_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.data == "dfindnoop":
        await q.answer()
        return
    parts = q.data.split(":")
    if parts[0] == "dfinddel":
        _, owner, token = parts
        if q.from_user.id != int(owner):
            await q.answer("Only the search owner can discard this result.", show_alert=True)
            return
        storage.finish_pending(token, "done")
        await q.answer()
        await q.message.delete()
        return
    _, owner, token, page_raw = parts
    if q.from_user.id != int(owner):
        await q.answer("Only the search owner can use these buttons.", show_alert=True)
        return
    pending = storage.get_pending(token, q.from_user.id, "dfind")
    if not pending:
        await q.answer("Search session expired.", show_alert=True)
        return
    ids = __import__("json").loads(pending["payload"])["ids"]
    rows = [w for wid in ids if (w := storage.get_waifu(wid))]
    page = int(page_raw)
    await q.answer()
    await q.edit_message_text(_dfind_page_text(rows, page), reply_markup=_dfind_keyboard(q.from_user.id, token, page, len(rows)))


async def f_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Usage: /f <waifu_id>")
        return
    w = storage.get_waifu(context.args[0])
    if not w:
        await update.effective_message.reply_text("THIS ID IS NOT FOUND IN BOT DATABASE.")
        return
    with storage.connect() as con:
        picked = con.execute("SELECT COUNT(*) AS n FROM user_waifus WHERE waifu_id=?", (w["waifu_id"],)).fetchone()["n"]
    await update.effective_message.reply_photo(
        w["image_file_id"],
        caption=f"🌐 CHARACTER INFO\n{_display(w)}\n🌍 GLOBALLY PICKED: {picked} times..."
    )


async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("Jis user ko gift karna hai uske message par reply karke /gift <waifu_id> likho.")
        return
    if not context.args:
        await msg.reply_text("Usage: /gift <waifu_id>")
        return
    giver, receiver = update.effective_user.id, msg.reply_to_message.from_user
    if receiver.is_bot or receiver.id == giver:
        await msg.reply_text("Bot ya khud ko gift nahi kar sakte.")
        return
    w = storage.owned_waifu(giver, context.args[0])
    if not w:
        await msg.reply_text("Ye waifu tumhari collection mein nahi hai.")
        return
    if storage.owned_waifu(receiver.id, context.args[0]):
        await msg.reply_text("⚠️ Receiver already owns this waifu. Duplicate gifting is not allowed.")
        return
    token = storage.create_pending(giver, "gift", {"receiver_id": receiver.id, "waifu_id": w["waifu_id"], "receiver_name": receiver.full_name}, 60)
    await msg.reply_photo(w["image_file_id"], caption=f"🎁 GIFT CONFIRMATION\n\n{_display(w)}\n\nReceiver: {receiver.full_name}\nRequest 1 minute mein expire ho jayegi.\nGift confirm karna hai?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm", callback_data=f"giftok:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"giftno:{token}")
        ]]))


async def gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "gift")
    if not pending:
        await q.answer("Gift request expire ho gayi ya tumhari nahi hai.", show_alert=True)
        return
    import json
    data = json.loads(pending["payload"])
    if action == "giftno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Gift cancelled.")
        await q.edit_message_caption("The gift has been successfully cancelled.")
        return
    if not storage.owned_waifu(q.from_user.id, data["waifu_id"]):
        await q.answer("Waifu ab tumhari collection mein nahi hai.", show_alert=True)
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM user_waifus WHERE id=(SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=? ORDER BY obtained_at LIMIT 1)",
            (q.from_user.id, data["waifu_id"])
        )
        if cur.rowcount != 1:
            con.rollback()
            await q.answer("Gift process nahi ho saka.", show_alert=True)
            return
        con.execute(
            "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
            (data["receiver_id"], data["waifu_id"], storage.now(), "gift")
        )
        con.execute(
            "INSERT INTO transactions(tx_id,actor_id,target_id,action,waifu_id,created_at) VALUES (?,?,?,?,?,?)",
            (__import__("uuid").uuid4().hex, q.from_user.id, data["receiver_id"], "gift", data["waifu_id"], storage.now())
        )
        con.commit()
    storage.finish_pending(token, "done")
    await q.answer("Gift successful!")
    await q.edit_message_caption(f"🎉 GIFT SUCCESSFUL!\n\nCharacter ID: {data['waifu_id']}\n{data['receiver_name']} ko successfully gift kar di gayi hai.")
    gifted = storage.get_waifu(data["waifu_id"])
    if gifted:
        try:
            await context.bot.send_photo(data["receiver_id"], gifted["image_file_id"],
                caption=f"🎁 YOU RECEIVED A WAIFU!\n{_display(gifted)}\nAdded to your /collection.")
        except Exception:
            pass


async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    args = context.args
    if len(args) == 2 and _owner(uid) and args[0].lower() in {r.lower() for r in RARITIES}:
        rarity = _rarity_name(args[0])
        try:
            percent = float(args[1].replace("%", ""))
            if not 1 <= percent <= 100:
                raise ValueError
        except ValueError:
            await update.effective_message.reply_text("Sell percentage 1–100 ke darmiyan hona chahiye.")
            return
        with storage.connect() as con:
            con.execute("INSERT INTO rarity_settings(rarity,sell_percent) VALUES (?,?) ON CONFLICT(rarity) DO UPDATE SET sell_percent=excluded.sell_percent", (rarity, percent))
        await update.effective_message.reply_text(f"👑 Sell rate updated: {rarity} = {percent:g}%")
        return
    if storage.cooldown_left(uid, "sell"):
        await update.effective_message.reply_text(f"⏳ Sell cooldown: {storage.cooldown_left(uid,'sell')} seconds.")
        return
    if len(args) == 2 and args[0].lower() in {"diamond", "diamonds", "dimonds"}:
        try:
            amount = int(args[1])
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.effective_message.reply_text("Usage: /sell diamonds <amount>")
            return
        cash, diamonds = storage.get_balance(uid)
        if diamonds < amount:
            await update.effective_message.reply_text("❌ Not enough diamonds.")
            return
        token = storage.create_pending(uid, "sell_diamonds", {"amount": amount}, 60)
        await update.effective_message.reply_text(
            f"💎 Sell {amount:,} diamonds for {_fmt(amount*10000)} Cash?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirm", callback_data=f"sellok:{token}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"sellno:{token}")
            ]])
        )
        return
    if not args or len(args) > 5 or not all(x.isdigit() for x in args):
        await update.effective_message.reply_text("Usage: /sell <waifu_id> [id2 id3 id4 id5] ya /sell diamonds <amount>")
        return
    if len(args) > 5:
        return
    if any(not storage.owned_waifu(uid, wid) for wid in args):
        await update.effective_message.reply_text("❌ In IDs mein se koi waifu tumhari collection mein nahi.")
        return
    day_start = int(datetime.now(ZoneInfo("Asia/Karachi")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    with storage.connect() as con:
        sold_today = con.execute(
            "SELECT COUNT(*) AS n FROM transactions WHERE actor_id=? AND action='sell_waifu' AND created_at>=?",
            (uid, day_start)
        ).fetchone()["n"]
    if sold_today + len(args) > 5:
        await update.effective_message.reply_text("Daily limit: maximum 5 waifus sell kar sakte ho.")
        return
    token = storage.create_pending(uid, "sell_waifus", {"ids": args}, 60)
    total = 0
    for wid in args:
        w = storage.owned_waifu(uid, wid)
        with storage.connect() as con:
            rate = con.execute("SELECT sell_percent FROM rarity_settings WHERE rarity=?", (w["rarity"],)).fetchone()
        percent = float(rate["sell_percent"]) if rate else 50.0
        total += int(w["price"] * percent / 100)
    await update.effective_message.reply_text(
        f"⚠️ Sell confirmation\nWaifus: {', '.join(args)}\nEstimated cash: {_fmt(total)}\nConfirm?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm", callback_data=f"sellok:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"sellno:{token}")
        ]])
    )


async def sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "sell_waifus") or storage.get_pending(token, q.from_user.id, "sell_diamonds")
    if not pending:
        await q.answer("Sell request expire ho gayi ya tumhari nahi hai.", show_alert=True)
        return
    import json
    data = json.loads(pending["payload"])
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        if action == "sellno":
            con.execute("UPDATE pending_actions SET status='cancelled' WHERE token=?", (token,))
            con.commit()
            await q.answer("Cancelled.")
            await q.edit_message_text("❌ Sale cancelled.")
            storage.set_cooldown(q.from_user.id, "sell", 60)
            return
        if pending["action"] == "sell_diamonds":
            amount = int(data["amount"])
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (q.from_user.id,))
            bal = con.execute("SELECT cash,diamonds FROM user_balance WHERE user_id=?", (q.from_user.id,)).fetchone()
            if bal["diamonds"] < amount:
                con.rollback()
                await q.answer("Not enough diamonds.", show_alert=True)
                return
            con.execute("UPDATE user_balance SET diamonds=diamonds-?,cash=cash+? WHERE user_id=?", (amount, amount*10000, q.from_user.id))
            cash_added = amount * 10000
        else:
            ids = data["ids"]
            cash_added = 0
            sale_logs = []
            for wid in ids:
                w = con.execute("SELECT price,rarity FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (wid,)).fetchone()
                owned = con.execute("SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=? ORDER BY obtained_at LIMIT 1", (q.from_user.id, wid)).fetchone()
                if not w or not owned:
                    con.rollback()
                    await q.answer("Collection changed; sale cancelled.", show_alert=True)
                    return
                rate = con.execute("SELECT sell_percent FROM rarity_settings WHERE rarity=?", (w["rarity"],)).fetchone()
                percent = float(rate["sell_percent"]) if rate else 50.0
                payout = int(w["price"] * percent / 100)
                con.execute("DELETE FROM user_waifus WHERE id=?", (owned["id"],))
                cash_added += payout
                sale_logs.append((wid, payout))
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (q.from_user.id,))
            con.execute("UPDATE user_balance SET cash=cash+? WHERE user_id=?", (cash_added, q.from_user.id))
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        if pending["action"] == "sell_waifus":
            for wid, payout in sale_logs:
                con.execute("INSERT INTO transactions(tx_id,actor_id,action,amount,waifu_id,details,created_at) VALUES (?,?,?,?,?,?,?)",
                            (__import__("uuid").uuid4().hex, q.from_user.id, "sell_waifu", payout, wid, json.dumps(data), storage.now()))
        else:
            con.execute("INSERT INTO transactions(tx_id,actor_id,action,amount,details,created_at) VALUES (?,?,?,?,?,?)",
                        (__import__("uuid").uuid4().hex, q.from_user.id, "sell_diamonds", cash_added, json.dumps(data), storage.now()))
        con.commit()
    storage.set_cooldown(q.from_user.id, "sell", 60)
    await q.answer("Sale completed.")
    await q.edit_message_text(f"✅ SOLD SUCCESSFULLY\n💰 Cash added: {_fmt(cash_added)}")


async def setprofile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.effective_message
    if context.args:
        wid = context.args[0]
        w = storage.owned_waifu(uid, wid)
        if not w:
            await msg.reply_text("You don't own this waifu.")
            return
        with storage.connect() as con:
            con.execute("INSERT INTO user_profiles(user_id,profile_waifu_id,updated_at) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET profile_waifu_id=excluded.profile_waifu_id,updated_at=excluded.updated_at", (uid, wid, storage.now()))
        await msg.reply_text(f"💖 {w['name']} set as your profile waifu.")
        return
    reply = msg.reply_to_message
    if reply and reply.photo:
        file_id = reply.photo[-1].file_id
        with storage.connect() as con:
            con.execute("INSERT INTO user_profiles(user_id,profile_photo,updated_at) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET profile_photo=excluded.profile_photo,updated_at=excluded.updated_at", (uid, file_id, storage.now()))
        await msg.reply_text("💖 Profile photo updated.")
        return
    await msg.reply_text("Usage: /setprofile <owned_waifu_id> ya kisi photo ko reply karke /setprofile.")


async def dupload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _uploader(update.effective_user.id):
        return
    msg = update.effective_message
    wid = context.args[0] if context.args else None
    if not wid and msg.reply_to_message:
        # The image caption may contain an ID line.
        match = re.search(r"ID:\s*(\d{4})", msg.reply_to_message.caption or "", re.I)
        wid = match.group(1) if match else None
    if not wid:
        await msg.reply_text("Usage: /dupload <4-digit-waifu_id>")
        return
    w = storage.get_waifu(wid)
    if not w:
        await msg.reply_text("Waifu not found.")
        return
    token = storage.create_pending(update.effective_user.id, "delete_waifu", {"waifu_id": wid}, 60)
    await msg.reply_photo(w["image_file_id"], caption=f"Delete {w['name']} ({wid}) from the catalogue and all collections?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Confirm Delete", callback_data=f"delok:{token}"), InlineKeyboardButton("Cancel", callback_data=f"delno:{token}")]]))


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "delete_waifu")
    if not pending:
        await q.answer("Request expired.", show_alert=True)
        return
    import json
    wid = json.loads(pending["payload"])["waifu_id"]
    if action == "delno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Cancelled.")
        await q.edit_message_caption("Deletion cancelled.")
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM user_waifus WHERE waifu_id=?", (wid,))
        con.execute("UPDATE waifus SET deleted_at=? WHERE waifu_id=?", (storage.now(), wid))
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        con.execute("INSERT INTO audit_log(actor_id,action,details,created_at) VALUES (?,?,?,?)", (q.from_user.id, "waifu_deleted", json.dumps({"waifu_id":wid}), storage.now()))
        con.commit()
    await q.answer("Deleted.")
    await q.edit_message_caption("✅ Waifu permanently deleted from the catalogue and all collections.")


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /stop <command> | /stop list")
        return
    with storage.connect() as con:
        if context.args[0].lower() == "list":
            rows = con.execute("SELECT command_name FROM bot_commands WHERE is_stopped=1 ORDER BY command_name").fetchall()
            await update.effective_message.reply_text("Stopped commands:\n" + ("\n".join(r["command_name"] for r in rows) or "None"))
            return
        name = context.args[0].lstrip("/").lower()
        con.execute("INSERT INTO bot_commands(command_name,is_stopped,stopped_by,stopped_at) VALUES (?,1,?,?) ON CONFLICT(command_name) DO UPDATE SET is_stopped=1,stopped_by=excluded.stopped_by,stopped_at=excluded.stopped_at", (name, update.effective_user.id, storage.now()))
    await update.effective_message.reply_text(f"✅ /{name} stopped for users. Owner can still test it.")


async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    name = context.args[0].lstrip("/").lower() if context.args else ""
    with storage.connect() as con:
        if name == "all":
            con.execute("UPDATE bot_commands SET is_stopped=0")
        elif name:
            con.execute("UPDATE bot_commands SET is_stopped=0 WHERE command_name=?", (name,))
        else:
            await update.effective_message.reply_text("Usage: /run <command|all>")
            return
    await update.effective_message.reply_text("▶️ Command(s) enabled.")


async def command_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text or not msg.text.startswith("/"):
        return
    name = msg.text.split()[0].split("@")[0].lstrip("/").lower()
    if _owner(update.effective_user.id):
        return
    with storage.connect() as con:
        row = con.execute("SELECT is_stopped FROM bot_commands WHERE command_name=?", (name,)).fetchone()
    if row and row["is_stopped"]:
        await msg.reply_text("⚙️ This command is temporarily unavailable. Please try again shortly.")
        raise __import__("telegram").error.ApplicationHandlerStop


async def changetime_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Alias retained for command inventory compatibility.
    await changetime_cmd(update, context)


async def add_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.add_sudo(update, context)


async def remove_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.remove_sudo(update, context)


async def sudo_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.sudo_list_command(update, context)


async def add_uploader_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.add_uploader(update, context)


async def remove_uploader_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.remove_uploader(update, context)


async def uploader_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await legacy.uploader_list_command(update, context)


async def spawn_expiry_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expire unattended group spawns and announce the escaped character."""
    expired = []
    with storage.connect() as con:
        rows = con.execute("SELECT chat_id,waifu_id FROM active_spawns WHERE expires_at<=?", (storage.now(),)).fetchall()
        for row in rows:
            expired.append((row["chat_id"], row["waifu_id"]))
            con.execute("DELETE FROM active_spawns WHERE chat_id=?", (row["chat_id"],))
    for chat_id, wid in expired:
        w = storage.get_waifu(wid)
        if not w:
            continue
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ TOO SLOW! The character escaped!\n\n{_display(w)}"
            )
        except Exception:
            pass

