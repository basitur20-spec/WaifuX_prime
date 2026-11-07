"""Waifu catalogue, collection and reward commands.

The module deliberately keeps all ownership/economy writes in storage.py.
"""
from __future__ import annotations

import asyncio
import difflib
import json
import os
import random
import re
import time
import urllib.request
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
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
    "CelestialArc": 35, "CrossArc": 4, "MangaArc": 50, "LimitedArc": 0,
    "SpecialArc": 0, "DivineArc": 0, "CinemaArc": 0,
}
OWNER_ID = 0
MESSAGE_COUNTS = defaultdict(int)
RECENT_MESSAGES = defaultdict(deque)
RARITY_ORDER = list(RARITIES)
DAILY_WAIFU_WEIGHTS = {
    "Starter": 50,
    "Rising": 50,
    "Shiny": 50,
    "Ultimate": 50,
    "RoyalArc": 5,
}
MARRIAGE_REWARD_WEIGHTS = {"Shiny": 50, "Ultimate": 50}


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


async def _edit_photo_or_text(q, text: str, reply_markup=None):
    if getattr(q.message, "photo", None):
        await q.edit_message_caption(caption=text, reply_markup=reply_markup)
    else:
        await q.edit_message_text(text, reply_markup=reply_markup)


def _display(w) -> str:
    emoji = RARITIES.get(w["rarity"], ("✨",))[0]
    return (
        f"🎭 Name: {w['name']}\n"
        f"📺 Anime: {w['anime']}\n"
        f"💫 Rarity: {emoji} {w['rarity']}\n"
        f"🆔 ID: {w['waifu_id']}\n"
        f"💰 Price: {_fmt(w['price'])}"
    )


def _random_waifu(
    rarities: list[str] | None = None,
    respect_spawn_settings: bool = False,
    weights: dict[str, int] | None = None,
):
    available = []
    weight_map = weights if weights is not None else RARITY_WEIGHTS
    for rarity in (rarities or RARITY_ORDER):
        if weight_map.get(rarity, 0) <= 0:
            continue
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
            available.extend((rarity, w) for w in pool if w["waifu_id"] not in active_ids and w["image_file_id"])
    if not available:
        return None
    names = list(dict.fromkeys(r for r, _ in available))
    chosen_rarity = random.choices(names, weights=[weight_map[r] for r in names], k=1)[0]
    pool = [w for r, w in available if r == chosen_rarity]
    return random.choice(pool)


def _parse_upload_details(raw: str) -> dict:
    """Accept the documented label/value formats and the legacy comma format."""
    raw = re.sub(r"^\s*/upload(?:@\w+)?\s*", "", raw or "", flags=re.I).strip()
    if not raw:
        return {}

    labels = {"name", "rarity", "anime", "price", "id", "aliases"}
    data = {}
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(
            r"^(name|rarity|anime|price|id|aliases)\s*(?:\([^)]*\))?\s*(?::|=)?\s*(.*?)\s*$",
            line,
            re.I,
        )
        if match:
            key, value = match.group(1).lower(), match.group(2).strip()
            if key == "anime" and value.casefold() == "name":
                value = ""
            if not value and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not re.match(
                    r"^(?:name|rarity|anime|price|id|aliases)\s*(?:\([^)]*\))?\s*(?::|=)?(?:\s|$)",
                    next_line,
                    re.I,
                ):
                    value = next_line
                    i += 1
            if value:
                data[key] = value
        i += 1

    if data:
        return data

    # Older syntax: /upload 38429,Name,Anime,Rarity[,Price]
    comma_parts = [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]
    if len(comma_parts) >= 4 and comma_parts[0].isdigit():
        data = {
            "id": comma_parts[0],
            "name": comma_parts[1],
            "anime": comma_parts[2],
            "rarity": comma_parts[3],
        }
        if len(comma_parts) >= 5:
            data["price"] = comma_parts[4]
        return data
    if len(comma_parts) >= 3:
        data = {
            "name": comma_parts[0],
            "anime": comma_parts[1],
            "rarity": comma_parts[2],
        }
        if len(comma_parts) >= 4:
            data["price"] = comma_parts[3]
        return data

    # Short plain format: Name, Rarity, Anime, optional Price.
    if len(lines) >= 3:
        data = {"name": lines[0], "rarity": lines[1], "anime": lines[2]}
        if len(lines) >= 4:
            data["price"] = lines[3]
    return data


def _quality_based_price(photo, rarity: str) -> int:
    low, high = RARITIES[rarity][1]
    pixels = max(0, int(getattr(photo, "width", 0) or 0) * int(getattr(photo, "height", 0) or 0))
    size = max(0, int(getattr(photo, "file_size", 0) or 0))
    resolution_score = min(1.0, max(0.0, (pixels - 512 * 512) / (2560 * 1440 - 512 * 512)))
    size_score = min(1.0, size / 2_000_000)
    quality_score = 0.8 * resolution_score + 0.2 * size_score
    return low + int((high - low) * quality_score)


def _correct_catalogue_labels(name: str, anime: str):
    catalogue = storage.list_waifus(limit=10000)
    known_names = list(dict.fromkeys(w["name"] for w in catalogue))
    known_anime = list(dict.fromkeys(w["anime"] for w in catalogue))
    corrected = []
    name_match = difflib.get_close_matches(name, known_names, n=1, cutoff=0.90)
    anime_match = difflib.get_close_matches(anime, known_anime, n=1, cutoff=0.90)
    if name_match and name_match[0].casefold() != name.casefold():
        corrected.append(f"Name: {name} -> {name_match[0]}")
        name = name_match[0]
    if anime_match and anime_match[0].casefold() != anime.casefold():
        corrected.append(f"Anime: {anime} -> {anime_match[0]}")
        anime = anime_match[0]
    return name, anime, corrected


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
        command_details = (msg.text or "").partition(" ")[2].strip()
        details_text = command_details or photo_msg.caption or msg.caption or ""
    if not photo:
        await msg.reply_text(
            "Add the details in the photo caption, or reply to the photo with /upload.\n\n"
            "Name: Character Name\nRarity: Shiny (or 1-19)\nAnime: Anime Name\nPrice: optional\nID: optional\nAliases: optional comma-separated names"
        )
        return
    data = _parse_upload_details(details_text)
    name, anime = data.get("name"), data.get("anime")
    rarity = _rarity_name(data.get("rarity", ""))
    if not name or not anime or not rarity:
        await msg.reply_text("Upload details are incomplete or invalid. Name, Rarity, and Anime are required.")
        return
    low, high = RARITIES[rarity][1]
    name, anime, corrections = _correct_catalogue_labels(name.strip(), anime.strip())
    try:
        price = int(re.sub(r"[^0-9]", "", data.get("price", ""))) if data.get("price") else _quality_based_price(photo, rarity)
        if not low <= price <= high:
            raise ValueError(f"{rarity} has an allowed price range of {_fmt(low)}–{_fmt(high)}.")
        wid = data.get("id") or ""
        if not wid:
            used = {str(w["waifu_id"]) for w in storage.list_waifus(limit=10000)}
            free = [str(n).zfill(4) for n in range(1000, 10000) if str(n).zfill(4) not in used]
            if not free:
                raise ValueError("No free Waifu IDs are available.")
            wid = random.choice(free)
        if len(wid) != 4 or not wid.isdigit():
            raise ValueError("The ID must contain exactly 4 digits.")
        storage.add_waifu(wid, name, anime, rarity, price, photo.file_id, uid, [a.strip() for a in data.get('aliases', '').split(',') if a.strip()])
        reward = int(price * 0.03)
        if reward:
            storage.change_balance(uid, cash_delta=reward)
        storage.add_audit(uid, "waifu_upload", details={"waifu_id": wid, "rarity": rarity})
    except Exception as exc:
        await msg.reply_text(f"❌ Upload rejected: {exc}")
        return
    w = storage.get_waifu(wid)
    rarity_emoji = RARITIES[rarity][0]
    success_caption = (
        "🌐 CHARACTER INFO:\n"
        "┏━━━━━━━━━━━━━⧫\n"
        f"✧ NAME: {w['name']} [{rarity_emoji}]\n"
        f"✧ RARITY: {w['rarity']} {rarity_emoji}\n"
        f"✧ ANIME: {w['anime']}\n"
        f"✧ PRICE: {_fmt(w['price'])}\n"
        f"✧ ID: {w['waifu_id']}\n"
        "┗━━━━━━━━━━━━━⧫\n\n"
        "🎉 Upload Successful!\n"
        "This waifu has been added to the global database.\n"
        f"You earned +{_fmt(reward)} coins (3%)."
    )
    if not data.get("price"):
        success_caption += "\n\nℹ️ Price Auto-Set by System\nPrice was automatically calculated based on image quality."
    if data.get("id"):
        success_caption += "\nManual ID has been registered successfully."
    await msg.reply_photo(photo=photo.file_id, caption=success_caption)
    channel_id = os.getenv("WAIFU_CHANNEL_ID")
    if channel_id:
        try:
            await context.bot.send_photo(
                chat_id=channel_id,
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
            if fav["image_file_id"]:
                await update.effective_message.reply_photo(fav["image_file_id"], caption=f"❤️ Your favourite waifu\n{_display(fav)}")
            else:
                await update.effective_message.reply_text(f"❤️ Your favourite waifu\n{_display(fav)}")
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


async def _send_fav_confirmation(message, uid: int, wid: str):
    w = storage.owned_waifu(uid, wid)
    if not w:
        await message.reply_text("😔 This waifu is not in your collection.")
        return
    token = storage.create_pending(uid, "favorite", {"waifu_id": w["waifu_id"]}, 60)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("INLINE", callback_data=f"favinline:{token}"),
        InlineKeyboardButton("COLLECTION", callback_data=f"favconfirm:{token}"),
        InlineKeyboardButton("CANCEL", callback_data=f"favcancel:{token}")
    ]])
    caption = f"ᴅᴏ ʏᴏᴜ ʀᴇᴀʟʟʏ ᴡᴀɴᴛ ᴛᴏ ꜱᴇᴛ ({w['name']}) ᴀꜱ ʏᴏᴜʀ ꜰᴀᴠᴏʀɪᴛᴇ ᴡᴀɪꜰᴜ?"
    if w["image_file_id"]:
        await message.reply_photo(w["image_file_id"], caption=caption, reply_markup=keyboard)
    else:
        await message.reply_text(caption, reply_markup=keyboard)


def _fav_list_keyboard(uid: int, rows, page: int):
    unique = list({w["waifu_id"]: w for w in rows}.values())
    pages = max(1, (len(unique) + 9) // 10)
    page = max(0, min(page, pages - 1))
    buttons = []
    for w in unique[page*10:(page+1)*10]:
        icon = RARITIES.get(w["rarity"], ("✨",))[0]
        buttons.append([InlineKeyboardButton(
            f"{icon} {w['name']} | {w['waifu_id']}"[:60],
            callback_data=f"favpick:{uid}:{w['waifu_id']}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"favlist:{uid}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="favnoop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"favlist:{uid}:{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"favlistclose:{uid}")])
    return InlineKeyboardMarkup(buttons)


async def fav_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if context.args:
        wid = context.args[0]
        if not wid.isdigit():
            await update.effective_message.reply_text("Usage: /fav <waifu_id>")
            return
        await _send_fav_confirmation(update.effective_message, uid, wid)
        return
    rows = storage.collection(uid)
    if not rows:
        await update.effective_message.reply_text("Your collection is empty.")
        return
    await update.effective_message.reply_text(
        "❤️ CHOOSE A WAIFU TO SET AS YOUR FAVOURITE:",
        reply_markup=_fav_list_keyboard(uid, rows, 0)
    )


async def waifu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.data == "favnoop":
        await q.answer()
        return
    data = q.data.split(":")
    action = data[0]
    if action == "favlistclose":
        if q.from_user.id != int(data[1]):
            await q.answer("This menu is not yours.", show_alert=True)
            return
        await q.answer()
        await q.message.delete()
        return
    if action == "favlist":
        if q.from_user.id != int(data[1]):
            await q.answer("This menu is not yours.", show_alert=True)
            return
        rows = storage.collection(q.from_user.id)
        await q.answer()
        await q.edit_message_reply_markup(reply_markup=_fav_list_keyboard(q.from_user.id, rows, int(data[2])))
        return
    if action == "favpick":
        if q.from_user.id != int(data[1]):
            await q.answer("This selection is not yours.", show_alert=True)
            return
        wid = data[2]
        if not storage.owned_waifu(q.from_user.id, wid):
            await q.answer("You no longer own this waifu.", show_alert=True)
            return
        await q.answer()
        await q.edit_message_text("Selected waifu. Confirm your favourite below.")
        await _send_fav_confirmation(q.message, q.from_user.id, wid)
        return
    token = data[1]
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
                await _edit_photo_or_text(
                    q, f"❤️ {w['name']} is now your favourite. Open inline mode:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("OPEN CHARACTER INLINE", switch_inline_query_current_chat=f"waifu {w['name']} rarity:{w['rarity']}")
                    ]])
                )
            else:
                await _edit_photo_or_text(q, f"❤️ {w['name']} is now your favourite.")
                if w["image_file_id"]:
                    await q.message.reply_photo(
                        w["image_file_id"],
                        caption=f"❤️ YOUR FAVOURITE WAIFU\n{_display(w)}",
                    )
                rows = storage.collection(q.from_user.id)
                await _send_collection(q.message, q.from_user.id, 0, rows, q.from_user.id)


async def inline_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from telegram import InlineQueryResultCachedPhoto
    query = update.inline_query
    term = query.query.strip()
    global_catalogue = term.casefold().startswith("waifu ")
    rarity_filter = None

    if global_catalogue:
        term = term[6:].strip()
        rarity_match = re.search(r"\s+rarity:([a-z0-9]+)\s*$", term, re.I)
        if rarity_match:
            rarity_filter = rarity_match.group(1).casefold()
            term = term[:rarity_match.start()].strip()
        rows = storage.list_waifus(limit=10000)
        if rarity_filter:
            rows = [w for w in rows if w["rarity"].casefold() == rarity_filter]
        if term:
            def character_matches(w):
                aliases = __import__("json").loads(w["aliases"] or "[]")
                return any(
                    term.casefold() in str(name).casefold()
                    for name in [w["name"], *aliases]
                )
            rows = [w for w in rows if character_matches(w)]
    else:
        rows = [w for w in _collection_for_user(query.from_user.id) if w["image_file_id"]]
        if term:
            rows = [
                w for w in rows
                if term.casefold() in w["name"].casefold()
                or term.casefold() in w["anime"].casefold()
            ]

    results = [
        InlineQueryResultCachedPhoto(
            id=f"{w['waifu_id']}-{i}",
            photo_file_id=w["image_file_id"],
            title=w["name"],
            description=f"{w['rarity']} | {w['anime']}",
        )
        for i, w in enumerate(rows[:50])
        if w["image_file_id"]
    ]
    await query.answer(results, cache_time=1, is_personal=True)


async def waifu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    daily_weights = DAILY_WAIFU_WEIGHTS
    w = _random_waifu(list(daily_weights), weights=daily_weights)
    if not w:
        await update.effective_message.reply_text("No waifus are currently available in the daily reward pool.")
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT expires_at FROM cooldowns WHERE user_id=? AND action='daily_waifu'", (uid,)).fetchone()
        left = max(0, int(row["expires_at"]) - storage.now()) if row else 0
        if left:
            con.rollback()
            hours, remainder = divmod(left, 3600)
            minutes, seconds = divmod(remainder, 60)
            await update.effective_message.reply_text(
                f"ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ʙᴇꜰᴏʀᴇ ᴄʟᴀɪᴍɪɴɢ ʏᴏᴜʀ ɴᴇxᴛ ᴡᴀɪꜰᴜ.\n"
                f"⏳ ᴛɪᴍᴇ ʟᴇꜰᴛ: {hours:02d}:{minutes:02d}:{seconds:02d}"
            )
            return
        con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (uid, w["waifu_id"], storage.now(), "daily"))
        con.execute("INSERT INTO cooldowns(user_id,action,expires_at) VALUES (?,?,?) ON CONFLICT(user_id,action) DO UPDATE SET expires_at=excluded.expires_at", (uid, "daily_waifu", storage.now()+12*60*60))
        con.execute("INSERT INTO transactions(tx_id,actor_id,action,waifu_id,created_at) VALUES (?,?,?,?,?)", (__import__("uuid").uuid4().hex, uid, "daily_waifu", w["waifu_id"], storage.now()))
        con.commit()
    emoji = RARITIES.get(w["rarity"], ("✨",))[0]
    caption = (
        f"𝗖𝗢𝗡𝗚𝗥𝗔𝗧𝗨𝗟𝗔𝗧𝗜𝗢𝗡𝗦 {update.effective_user.first_name}! 𝗬𝗢𝗨 𝗪𝗢𝗡 🔥\n"
        f"◈ 𝗡𝗔𝗠𝗘: {w['name']}\n"
        f"◈ 𝗥𝗔𝗥𝗜𝗧𝗬: {emoji} {w['rarity']}\n"
        f"◈ 𝗔𝗡𝗜𝗠𝗘: {w['anime']}"
    )
    await update.effective_message.reply_photo(w["image_file_id"], caption=caption)


async def hunt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg.chat.type == ChatType.PRIVATE:
        await msg.reply_text("Hunt is available in groups only.")
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
            con.rollback()
            await msg.reply_text("❌NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEST SPAWN.")
            return
        w = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (spawn["waifu_id"],)).fetchone()
        if not w:
            con.execute("DELETE FROM active_spawns WHERE chat_id=?", (msg.chat_id,))
            con.commit()
            await msg.reply_text("❌NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEST SPAWN.")
            return
        names = [w["name"], *(__import__("json").loads(w["aliases"] or "[]"))]
        normalized_names = [name.casefold().strip() for name in names]
        supplied_words = set(re.findall(r"[\w]+", supplied))
        partial_match = any(
            supplied_words and supplied_words.issubset(set(re.findall(r"[\w]+", name)))
            for name in normalized_names
        )
        fuzzy_match = bool(difflib.get_close_matches(supplied, normalized_names, n=1, cutoff=0.72))
        if not partial_match and not fuzzy_match:
            con.rollback()
            await msg.reply_text("❌NO CHARACTER HAS SPAWNED YET. PLEASE WAIT FOR THE NEST SPAWN.")
            return
        con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (msg.from_user.id, w["waifu_id"], storage.now(), "hunt"))
        con.execute("DELETE FROM active_spawns WHERE chat_id=?", (msg.chat_id,))
        con.execute("INSERT INTO transactions(tx_id,actor_id,action,waifu_id,created_at) VALUES (?,?,?,?,?)", (__import__("uuid").uuid4().hex, msg.from_user.id, "hunt", w["waifu_id"], storage.now()))
        con.commit()
    finally:
        con.close()
    emoji = RARITIES.get(w["rarity"], ("✨",))[0]
    caption = (
        "Congratulation 🎉\n"
        f"{msg.from_user.first_name} 𝙔𝙤𝙪 𝙂𝙤𝙩 𝙉𝙚𝙬 𝙬𝙖𝙞𝙛𝙪🫧\n"
        f"🌸𝗡𝗔𝗠𝗘: {w['name']}\n"
        f"🧩𝗔𝗡𝗜𝗠𝗘: {w['anime']}\n"
        f"𝗥𝗔𝗥𝗜𝗧𝗬: {emoji} {w['rarity']}\n"
        f"🆔𝗜𝗗: {w['waifu_id']}\n\n"
        "⛩ 𝘾𝙝𝙚𝙘𝙠 𝙮𝙤𝙪𝙧 /collection 𝙉𝙤𝙬"
    )
    await msg.reply_photo(
        w["image_file_id"],
        caption=caption,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("COLLECTION🔥", callback_data=f"col:{msg.from_user.id}:0")]])
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
            await msg.reply_text(f"{msg.from_user.first_name}, your messages won't be counted for 5 minutes.\nYou cannot spam to get characters to this Bot.")
        except Exception:
            await msg.reply_text("⚠️ Anti-spam detected, but I could not mute this user. Please make the bot an administrator with permission to restrict members.")
        q.clear()
        return
    con = storage.raw_connect()
    try:
        active = con.execute("SELECT 1 FROM active_spawns WHERE chat_id=?", (chat_id,)).fetchone()
        if active:
            # The expiry job owns cleanup and the escape announcement.
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
        caption="✨ ᴀ ɴᴇᴡ ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀꜱ ᴀᴘᴘᴇᴀʀᴇᴅ! ✨\nᴜꜱᴇ /hunt (ɴᴀᴍᴇ) ᴛᴏ ᴀᴅᴅ ɪᴛ ɪɴ ʏᴏᴜʀ COLLECTION."
    )


async def spawn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /spawn <rarity> on/off")
        return
    rarity, status = _rarity_name(context.args[0]), context.args[1].lower()
    if not rarity or RARITY_WEIGHTS.get(rarity, 0) <= 0 or status not in {"on", "off"}:
        await update.effective_message.reply_text("Invalid or non-spawnable rarity. Use one of the 15 configured spawn rarities and choose on/off.")
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO rarity_settings(rarity,spawn_enabled) VALUES (?,?)
            ON CONFLICT(rarity) DO UPDATE SET spawn_enabled=excluded.spawn_enabled""",
            (rarity, int(status == "on"))
        )
    await update.effective_message.reply_text(f"{RARITIES[rarity][0]} {rarity} spawning {status.upper()}.")


async def changetime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _staff(update.effective_user.id):
        return
    msg = update.effective_message
    if msg.chat.type == ChatType.PRIVATE:
        await msg.reply_text("Use this command in the group whose spawn timer you want to change.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await msg.reply_text(
            "⚠️ INVALID CHANGETIME FORMAT\n\n"
            "Examples:\n/changetime 5\n/changetime 10"
        )
        return
    minutes = int(context.args[0])
    if not 2 <= minutes <= 120:
        await msg.reply_text(
            "❌ INVALID TIME RANGE\n\nMinimum: 2 minutes\nMaximum: 120 minutes."
        )
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO group_settings(chat_id,spawn_interval,next_spawn_at,enabled)
            VALUES (?,?,?,1) ON CONFLICT(chat_id) DO UPDATE SET
            spawn_interval=excluded.spawn_interval,next_spawn_at=excluded.next_spawn_at,enabled=1""",
            (update.effective_chat.id, minutes, storage.now() + minutes * 60)
        )
    group_name = update.effective_chat.title or str(update.effective_chat.id)
    await msg.reply_text(
        "⏱ SPAWN INTERVAL UPDATED SUCCESSFULLY!\n\n"
        f"Group: {group_name}\n"
        f"Spawn Interval: Every {minutes} minutes\n"
        "Status: ACTIVE ✅\n"
        "The new timer starts now for this group."
    )


async def marriage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT expires_at FROM cooldowns WHERE user_id=? AND action='marriage'", (uid,)).fetchone()
        left = max(0, int(row["expires_at"]) - storage.now()) if row else 0
        if left:
            con.rollback()
            minutes, seconds = divmod(left, 60)
            await update.effective_message.reply_text(f"⏳ ʏᴏᴜ ᴄᴀɴ ᴜꜱᴇ /marriage ᴀɢᴀɪɴ ɪɴ {minutes:02d}ᴍ {seconds:02d}ꜱ.")
            return
        con.execute("INSERT INTO cooldowns(user_id,action,expires_at) VALUES (?,?,?) ON CONFLICT(user_id,action) DO UPDATE SET expires_at=excluded.expires_at", (uid, "marriage", storage.now()+3600))
        con.commit()
    if random.random() >= 0.35:
        await update.effective_message.reply_text(
            f"{update.effective_user.first_name}, ʏᴏᴜʀ ᴍᴀʀʀɪᴀɢᴇ ᴘʀᴏᴘᴏꜱᴀʟ ᴡᴀꜱ ʀᴇᴊᴇᴄᴛᴇᴅ ᴀɴᴅ ꜱʜᴇ ʀᴀɴ ᴀᴡᴀʏ! 🤡"
        )
        return
    w = _random_waifu(["Shiny", "Ultimate"], weights=MARRIAGE_REWARD_WEIGHTS)
    if not w:
        await update.effective_message.reply_text("No waifus are currently available for marriage rewards.")
        return
    storage.add_to_collection(uid, w["waifu_id"], "marriage")
    emoji = RARITIES.get(w["rarity"], ("✨",))[0]
    caption = (
        f"ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴꜱ! {update.effective_user.first_name}, "
        "ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴍᴀʀʀɪᴇᴅ! ʜᴇʀᴇ ɪꜱ ʏᴏᴜʀ ᴄʜᴀʀᴀᴄᴛᴇʀ:\n\n"
        f"Name: {w['name']}\nRarity: {emoji} {w['rarity']}\nAnime: {w['anime']}"
    )
    await update.effective_message.reply_photo(w["image_file_id"], caption=caption)


def _request_waifu_api_images(limit: int = 3) -> list[str]:
    """Fetch SFW anime image URLs from Waifu API."""
    request = urllib.request.Request(
        f"https://api.waifu.best/images?PageSize={limit}&IsNsfw=False",
        headers={"Accept-Version": "v7", "User-Agent": "WaifuX-Prime/1.0"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    urls = []
    for item in payload.get("items", []):
        url = item.get("url")
        if isinstance(url, str) and url.startswith("https://"):
            urls.append(url)
    return urls


_PROPOSAL_INTRO_LOCK = asyncio.Lock()


async def _proposal_intro_image() -> str | None:
    """Use one persistent intro image for every user and every bot restart."""
    cache_path = storage.DATA_DIR / "propose_intro_image_url.txt"
    async with _PROPOSAL_INTRO_LOCK:
        try:
            if cache_path.exists():
                cached = cache_path.read_text(encoding="utf-8").strip()
                if cached.startswith("https://"):
                    return cached
            urls = await asyncio.to_thread(_request_waifu_api_images, 1)
            if not urls:
                return None
            storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(urls[0], encoding="utf-8")
            return urls[0]
        except Exception:
            return None


async def _proposal_gallery_images(intro_url: str | None) -> list[str]:
    """Fetch three fresh SFW anime pictures for the proposal gallery."""
    try:
        urls = await asyncio.to_thread(_request_waifu_api_images, 6)
        unique = []
        for url in urls:
            if url != intro_url and url not in unique:
                unique.append(url)
            if len(unique) == 3:
                break
        return unique
    except Exception:
        return []


async def _random_proposal_reward():
    rarity_weights = {
        "ChristmasArc": 35,
        "RoyalArc": 60,
        "NeonArc": 35,
        "CelestialArc": 55,
    }
    all_waifus = storage.list_waifus(limit=10000)
    pools = {
        rarity: [w for w in all_waifus if w["rarity"] == rarity and w["image_file_id"]]
        for rarity in rarity_weights
    }
    available = [rarity for rarity, waifus in pools.items() if waifus]
    if not available:
        return None
    selected = random.choices(
        available,
        weights=[rarity_weights[rarity] for rarity in available],
        k=1,
    )[0]
    return random.choice(pools[selected])


async def propose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT expires_at FROM cooldowns WHERE user_id=? AND action='propose'", (uid,)).fetchone()
        left = max(0, int(row["expires_at"]) - storage.now()) if row else 0
        if left:
            con.rollback()
            minutes, seconds = divmod(left, 60)
            await update.effective_message.reply_text(
                f"ᴄᴏᴏʟᴅᴏᴡɴ! ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ {minutes:02d}ᴍ {seconds:02d}ꜱ ʙᴇꜰᴏʀᴇ ᴘʀᴏᴘᴏꜱɪɴɢ ᴀɢᴀɪɴ."
            )
            return
        con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (uid,))
        cash = con.execute("SELECT cash FROM user_balance WHERE user_id=?", (uid,)).fetchone()["cash"]
        if cash < 30_000:
            con.rollback()
            await update.effective_message.reply_text("YOU NEED 30,000 CASH💸 TO PROPOSE.")
            return
        con.execute("UPDATE user_balance SET cash=cash-30000 WHERE user_id=?", (uid,))
        con.execute(
            "INSERT INTO cooldowns(user_id,action,expires_at) VALUES (?,?,?) ON CONFLICT(user_id,action) DO UPDATE SET expires_at=excluded.expires_at",
            (uid, "propose", storage.now()+300)
        )
        con.execute(
            "INSERT INTO transactions(tx_id,actor_id,action,amount,created_at) VALUES (?,?,?,?,?)",
            (__import__("uuid").uuid4().hex, uid, "propose_fee", 30000, storage.now())
        )
        con.commit()

    intro_url = await _proposal_intro_image()
    intro_caption = f"{update.effective_user.first_name} 💫 ᴛʜᴇ ᴍᴏᴍᴇɴᴛ ʏᴏᴜ'ᴠᴇ ʙᴇᴇɴ ᴡᴀɪᴛɪɴɢ ꜰᴏʀ 💫"
    intro_message = None
    if intro_url:
        try:
            intro_message = await update.effective_message.reply_photo(intro_url, caption=intro_caption)
        except Exception:
            intro_message = await update.effective_message.reply_text(intro_caption)
    else:
        intro_message = await update.effective_message.reply_text(intro_caption)

    gallery_urls = await _proposal_gallery_images(intro_url)
    if gallery_urls:
        try:
            gallery = [
                InputMediaPhoto(
                    media=url,
                    caption="ᴘʀᴏᴘᴏꜱɪɴɢ ʜᴇʀ.... 💍" if index == 0 else None,
                )
                for index, url in enumerate(gallery_urls)
            ]
            processing_messages = await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=gallery,
                reply_to_message_id=intro_message.message_id,
            )
            processing = processing_messages[0]
        except Exception:
            processing = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="ᴘʀᴏᴘᴏꜱɪɴɢ ʜᴇʀ.... 💍",
                reply_to_message_id=intro_message.message_id,
            )
    else:
        processing = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="ᴘʀᴏᴘᴏꜱɪɴɢ ʜᴇʀ.... 💍",
            reply_to_message_id=intro_message.message_id,
        )

    await asyncio.sleep(random.randint(3, 5))
    accepted = random.uniform(0, 100) <= random.randint(35, 45)
    if accepted:
        w = await _random_proposal_reward()
        if w:
            storage.add_to_collection(uid, w["waifu_id"], "propose")
            caption = (
                f"{w['name']} [🍾] ʜᴀꜱ ᴀᴄᴄᴇᴘᴛᴇᴅ ʏᴏᴜʀ ᴘʀᴏᴘᴏꜱᴀʟ! 😇\n\n"
                f"☘️ Name: {w['name']} [🍾]\n"
                f"🵿 Rarity: {w['rarity']}\n"
                f"💠 Anime: {w['anime']}\n\n"
                "✨ Added to your /collection."
            )
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=w["image_file_id"],
                caption=caption,
                reply_to_message_id=processing.message_id,
            )
            return

    rejection_options = [
        "ʏᴏᴜ'ᴠᴇ ʙᴇᴇɴ ꜰʀɪᴇɴᴅ-ᴢᴏɴᴇᴅ ꜱᴏ ʜᴀʀᴅ,\nʏᴏᴜ'ʀᴇ ɴᴏᴡ ᴛʜᴇ ᴍᴀʏᴏʀ ᴏꜰ ꜰʀɪᴇɴᴅ ᴢᴏɴᴇ ᴄɪᴛʏ! 🏙️",
        "ʙʀᴇᴀᴋɪɴɢ ɴᴇᴡꜱ:\nʟᴏᴄᴀʟ ꜱɪᴍᴘ ɢᴇᴛꜱ ʀᴇᴊᴇᴄᴛᴇᴅ ꜱᴏ ʜᴀʀᴅ,\nᴇᴠᴇɴ ʜɪꜱ ᴀɴɪᴍᴇ ʙᴏᴅʏ ᴘɪʟʟᴏᴡ ʟᴇꜰᴛ ʜɪᴍ! 🥲🛏️",
    ]
    rejection = random.choice(rejection_options)
    try:
        rejection_urls = await asyncio.to_thread(_request_waifu_api_images, 1)
        if rejection_urls:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=rejection_urls[0],
                caption=rejection,
                reply_to_message_id=processing.message_id,
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=rejection,
                reply_to_message_id=processing.message_id,
            )
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=rejection,
            reply_to_message_id=processing.message_id,
        )


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    requester = update.effective_user
    target_id = requester.id
    if context.args:
        search = context.args[0].lstrip("@")
        with storage.connect() as con:
            if search.isdigit():
                found = con.execute(
                    "SELECT * FROM user_profiles WHERE bot_user_id=? OR user_id=?",
                    (search, int(search)),
                ).fetchone()
            else:
                found = con.execute(
                    "SELECT * FROM user_profiles WHERE lower(username)=lower(?)",
                    (search,),
                ).fetchone()
        if not found:
            await update.effective_message.reply_text(
                "⚠️ User not found.\nPlease check the username and try again."
            )
            return
        target_id = int(found["user_id"])

    bot_user_id = storage.ensure_bot_user_id(target_id)
    with storage.connect() as con:
        profile = con.execute("SELECT * FROM user_profiles WHERE user_id=?", (target_id,)).fetchone()
    rows = storage.collection(target_id)
    cash, diamonds = storage.get_balance(target_id)
    name = (profile["first_name"] if profile else None) or str(target_id)
    username = profile["username"] if profile else None
    text = (
        "👤 USER PROFILE\n\n"
        f"🆔 User ID: {bot_user_id}\n"
        f"👤 Name: {name}\n"
        f"🔗 Username: @{username or 'N/A'}\n\n"
        f"💰 Balance: {_fmt(cash)}\n"
        f"💎 Diamonds: {_fmt(diamonds)}\n"
        f"💖 Waifus Collected: {len(rows)} / {len(storage.list_waifus(limit=10000))}"
    )

    image_file_id = None
    if profile and profile["profile_photo"]:
        image_file_id = profile["profile_photo"]
    elif profile and profile["profile_waifu_id"]:
        w = storage.get_waifu(profile["profile_waifu_id"])
        if w:
            image_file_id = w["image_file_id"]

    if profile and profile["profile_waifu_id"]:
        w = storage.get_waifu(profile["profile_waifu_id"])
        if w:
            text += (
                "\n\n🌸 Profile Waifu:\n"
                f"Name: {w['name']}\n"
                f"Rarity: {RARITIES.get(w['rarity'], ('✨',))[0]} {w['rarity']}\n"
                f"Anime: {w['anime']}"
            )

    if image_file_id:
        await update.effective_message.reply_photo(image_file_id)
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
    if w["image_file_id"]:
        await update.effective_message.reply_photo(
            w["image_file_id"], caption=caption,
            reply_markup=_find_keyboard(update.effective_user.id, wid, 0, pages)
        )
    else:
        await update.effective_message.reply_text(
            caption, reply_markup=_find_keyboard(update.effective_user.id, wid, 0, pages)
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
    await _edit_photo_or_text(q, caption, reply_markup=_find_keyboard(q.from_user.id, wid, page, pages))


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
    caption = f"🌐 CHARACTER INFO\n{_display(w)}\n🌍 GLOBALLY PICKED: {picked} times..."
    if w["image_file_id"]:
        await update.effective_message.reply_photo(w["image_file_id"], caption=caption)
    else:
        await update.effective_message.reply_text(caption)


async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("Reply to the recipient's message and use /gift <waifu_id>.")
        return
    if not context.args:
        await msg.reply_text("Usage: /gift <waifu_id>")
        return
    giver, receiver = update.effective_user.id, msg.reply_to_message.from_user
    if receiver.is_bot or receiver.id == giver:
        await msg.reply_text("You cannot gift a character to the bot or to yourself.")
        return
    w = storage.owned_waifu(giver, context.args[0])
    if not w:
        await msg.reply_text("This character is not in your collection.")
        return
    if storage.owned_waifu(receiver.id, context.args[0]):
        await msg.reply_text("⚠️ Receiver already owns this waifu. Duplicate gifting is not allowed.")
        return
    token = storage.create_pending(giver, "gift", {"receiver_id": receiver.id, "waifu_id": w["waifu_id"], "receiver_name": receiver.full_name}, 60)
    caption = f"🎁 GIFT CONFIRMATION\n\n{_display(w)}\n\nReceiver: {receiver.full_name}\nThis request will expire in 1 minute.\nDo you want to confirm this gift?"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm", callback_data=f"giftok:{token}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"giftno:{token}")
    ]])
    if w["image_file_id"]:
        await msg.reply_photo(w["image_file_id"], caption=caption, reply_markup=keyboard)
    else:
        await msg.reply_text(caption, reply_markup=keyboard)


async def gift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "gift")
    if not pending:
        await q.answer("This gift request has expired or does not belong to you.", show_alert=True)
        return
    import json
    data = json.loads(pending["payload"])
    if action == "giftno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Gift cancelled.")
        await _edit_photo_or_text(q, "The gift has been successfully cancelled.")
        return
    if not storage.owned_waifu(q.from_user.id, data["waifu_id"]):
        await q.answer("This character is no longer in your collection.", show_alert=True)
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        already_owned = con.execute("SELECT 1 FROM user_waifus WHERE user_id=? AND waifu_id=? LIMIT 1", (data["receiver_id"], data["waifu_id"])).fetchone()
        if already_owned:
            con.rollback()
            await q.answer("Receiver already owns this waifu.", show_alert=True)
            return
        cur = con.execute(
            "DELETE FROM user_waifus WHERE id=(SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=? ORDER BY obtained_at LIMIT 1)",
            (q.from_user.id, data["waifu_id"])
        )
        if cur.rowcount != 1:
            con.rollback()
            await q.answer("The gift could not be completed.", show_alert=True)
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
    await _edit_photo_or_text(q, f"🎉 GIFT SUCCESSFUL!\n\nCharacter ID: {data['waifu_id']}\nSuccessfully gifted to {data['receiver_name']}.")
    gifted = storage.get_waifu(data["waifu_id"])
    if gifted:
        try:
            if gifted["image_file_id"]:
                await context.bot.send_photo(data["receiver_id"], gifted["image_file_id"],
                    caption=f"🎁 YOU RECEIVED A WAIFU!\n{_display(gifted)}\nAdded to your /collection.")
            else:
                await context.bot.send_message(data["receiver_id"], f"🎁 YOU RECEIVED A WAIFU!\n{_display(gifted)}\nAdded to your /collection.")
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
            await update.effective_message.reply_text("The sell percentage must be between 1 and 100.")
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
        await update.effective_message.reply_text("❌ None of these IDs belong to your collection.")
        return
    day_start = int(datetime.now(ZoneInfo("Asia/Karachi")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    with storage.connect() as con:
        sold_today = con.execute(
            "SELECT COUNT(*) AS n FROM transactions WHERE actor_id=? AND action='sell_waifu' AND created_at>=?",
            (uid, day_start)
        ).fetchone()["n"]
    if sold_today + len(args) > 5:
        await update.effective_message.reply_text("Daily limit reached: you can sell a maximum of 5 characters.")
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
        await q.answer("This sale request has expired or does not belong to you.", show_alert=True)
        return
    import json
    data = json.loads(pending["payload"])
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        if action == "sellno":
            con.execute("UPDATE pending_actions SET status='cancelled' WHERE token=?", (token,))
            con.commit()
            await q.answer("Cancelled.")
            await q.edit_message_text("❌ Sale cancelled.\nNo changes were made.")
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
    await q.edit_message_text(
        "✅ SOLD SUCCESSFULLY!\n\n"
        f"💰 Cash Added: {_fmt(cash_added)}\n"
        "Your collection and balance have been updated."
    )


async def setprofile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    msg = update.effective_message
    if context.args:
        wid = context.args[0]
        w = storage.owned_waifu(uid, wid)
        if not w:
            await msg.reply_text("You don't own this waifu.")
            return
        token = storage.create_pending(uid, "set_profile_waifu", {"waifu_id": w["waifu_id"]}, 60)
        caption = f"Do you want to set {w['name']} as your profile waifu?\n\n{_display(w)}"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm", callback_data=f"setprofileok:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"setprofileno:{token}")
        ]])
        if w["image_file_id"]:
            await msg.reply_photo(w["image_file_id"], caption=caption, reply_markup=keyboard)
        else:
            await msg.reply_text(caption, reply_markup=keyboard)
        return

    reply = msg.reply_to_message
    if reply and reply.photo:
        file_id = reply.photo[-1].file_id
        with storage.connect() as con:
            con.execute(
                """INSERT INTO user_profiles(user_id,profile_photo,profile_waifu_id,updated_at)
                VALUES (?,?,NULL,?) ON CONFLICT(user_id) DO UPDATE SET
                profile_photo=excluded.profile_photo,profile_waifu_id=NULL,updated_at=excluded.updated_at""",
                (uid, file_id, storage.now())
            )
        await msg.reply_text("📸 Profile photo updated successfully!")
        return
    await msg.reply_text("Usage: /setprofile <owned_waifu_id>, or reply to a photo with /setprofile.")


async def setprofile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":", 1)
    pending = storage.get_pending(token, q.from_user.id, "set_profile_waifu")
    if not pending:
        await q.answer("This profile request has expired or does not belong to you.", show_alert=True)
        return
    import json
    data = json.loads(pending["payload"])
    if action == "setprofileno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Profile update cancelled.")
        await _edit_photo_or_text(q, "❌ Profile update cancelled.")
        return
    w = storage.owned_waifu(q.from_user.id, data["waifu_id"])
    if not w:
        await q.answer("You no longer own this waifu.", show_alert=True)
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO user_profiles(user_id,profile_waifu_id,profile_photo,updated_at)
            VALUES (?,?,NULL,?) ON CONFLICT(user_id) DO UPDATE SET
            profile_waifu_id=excluded.profile_waifu_id,profile_photo=NULL,updated_at=excluded.updated_at""",
            (q.from_user.id, w["waifu_id"], storage.now())
        )
    storage.finish_pending(token, "done")
    await q.answer("Profile updated successfully.")
    await _edit_photo_or_text(q, f"💖 Profile Updated Successfully!\n\n{_display(w)}")


async def dupload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _uploader(update.effective_user.id):
        return
    msg = update.effective_message
    wid = context.args[0] if context.args else None
    if not wid and msg.reply_to_message:
        # The image caption may contain an ID line.
        match = re.search(r"ID:\s*(\d{4})", msg.reply_to_message.caption or "", re.I)
        wid = match.group(1) if match else None
    if not wid or not re.fullmatch(r"\d{4}", str(wid)):
        await msg.reply_text(
            "❌ INVALID DUPLOAD COMMAND\n\n"
            "Correct Usage:\n• /dupload 0001\n• Reply to a waifu message → /dupload"
        )
        return
    w = storage.get_waifu(wid)
    if not w:
        await msg.reply_text(
            "❌ WAIFU NOT FOUND\n\nThis waifu does not exist in the database or is already deleted."
        )
        return
    token = storage.create_pending(update.effective_user.id, "delete_waifu", {"waifu_id": wid}, 60)
    caption = (
        "⚠️ CONFIRM WAIFU DELETION\n\n"
        f"🧩 Name: {w['name']}\n🆔 ID: {wid}\n"
        f"🵿 Rarity: {w['rarity']}\n🎬 Anime: {w['anime']}\n\n"
        "This will remove the waifu from the bot database and every user's collection."
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Confirm Delete", callback_data=f"delok:{token}"), InlineKeyboardButton("Cancel", callback_data=f"delno:{token}")]])
    if w["image_file_id"]:
        await msg.reply_photo(w["image_file_id"], caption=caption, reply_markup=keyboard)
    else:
        await msg.reply_text(caption, reply_markup=keyboard)


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
        await _edit_photo_or_text(q, "❎ DELETE CANCELLED\nNo changes were made. Waifu is safe.")
        return
    affected = []
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        waifu = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (wid,)).fetchone()
        if not waifu:
            con.rollback()
            await q.answer("Waifu not found or already deleted.", show_alert=True)
            return
        affected = [row["user_id"] for row in con.execute(
            "SELECT DISTINCT user_id FROM user_waifus WHERE waifu_id=?", (wid,)
        ).fetchall()]
        con.execute("DELETE FROM user_waifus WHERE waifu_id=?", (wid,))
        con.execute("DELETE FROM active_spawns WHERE waifu_id=?", (wid,))
        con.execute("DELETE FROM marketplace_slots WHERE waifu_id=?", (wid,))
        con.execute("UPDATE auctions SET status='cancelled' WHERE waifu_id=? AND status='active'", (wid,))
        con.execute("UPDATE waifus SET deleted_at=? WHERE waifu_id=?", (storage.now(), wid))
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        con.execute("INSERT INTO audit_log(actor_id,action,details,created_at) VALUES (?,?,?,?)",
                    (q.from_user.id, "waifu_deleted", json.dumps({"waifu_id":wid,"affected_users":affected}), storage.now()))
        con.commit()
    await q.answer("Deleted.")
    await _edit_photo_or_text(
        q, f"✅ WAIFU DELETED SUCCESSFULLY\n\n"
        f"🧩 {waifu['name']}\n🆔 ID: {wid}\n"
        "Removed from the bot database and all user collections. The deletion has been logged."
    )
    info = _display(waifu)
    for user_id in affected:
        try:
            if waifu["image_file_id"]:
                await context.bot.send_photo(user_id, waifu["image_file_id"], caption=f"🌐 CHARACTER INFO\n{info}")
            else:
                await context.bot.send_message(user_id, f"🌐 CHARACTER INFO\n{info}")
            await context.bot.send_message(
                user_id,
                "💔 WAIFU REMOVED 💔\n\nThis waifu has been permanently deleted by the system administrators.\n"
                "• Removed from your collection\n• You did NOT lose cash\n• This action cannot be reversed\n\nThank you for understanding 🌸"
            )
        except Exception:
            # A user may have blocked the bot; database deletion remains complete.
            pass


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
        emoji = RARITIES.get(w["rarity"], ("✨",))[0]
        escaped = (
            "❌ ᴛᴏᴏ ꜱʟᴏᴡ! ᴛʜᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴇꜱᴄᴀᴘᴇᴅ! 🏃‍♀️✨\n\n"
            f"🌸 ɴᴀᴍᴇ: {w['name']}\n"
            f"💠 ᴀɴɪᴍᴇ: {w['anime']}\n"
            f"✨ ʀᴀʀɪᴛʏ: {emoji} {w['rarity']}\n"
            f"🆔 ɪᴅ: {w['waifu_id']}"
        )
        try:
            await context.bot.send_message(chat_id=chat_id, text=escaped)
        except Exception:
            pass
