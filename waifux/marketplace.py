"""Personal daily marketplace and timed auctions."""
from __future__ import annotations

import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes

from . import storage
from .waifu_handlers import RARITIES, RARITY_ORDER, _display, _fmt, _owner, _sudo, _rarity_name

DISCOUNTS = {
    "ChibiArc": (6, 11), "WinterArc": (5, 10), "RoyalArc": (6, 15),
    "NeonArc": (4, 8), "CelestialArc": (6, 13), "MangaArc": (7, 17),
}
COMMON_POOL = ["RoyalArc", "NeonArc", "CelestialArc", "MangaArc"]
RARE_POOL = ["ChibiArc", "WinterArc"]


def day_key() -> str:
    return datetime.now(ZoneInfo("Asia/Karachi")).date().isoformat()


def _available(rarity: str):
    with storage.connect() as con:
        return con.execute(
            """SELECT w.* FROM waifus w
            WHERE w.rarity=? AND w.deleted_at IS NULL AND w.image_file_id<>''
            AND NOT EXISTS (SELECT 1 FROM auctions a WHERE a.waifu_id=w.waifu_id)
            ORDER BY RANDOM() LIMIT 10000""", (rarity,)
        ).fetchall()


def _choose_offer(uid: int, exclude: set[str]):
    group = random.choices(["common", "rare"], weights=[70, 30], k=1)[0]
    rarity_groups = [COMMON_POOL, RARE_POOL] if group == "common" else [RARE_POOL, COMMON_POOL]
    for rarities in rarity_groups:
        enabled = []
        for rarity in rarities:
            with storage.connect() as con:
                setting = con.execute("SELECT enabled FROM market_rarity_settings WHERE rarity=?", (rarity,)).fetchone()
            if not setting or setting["enabled"]:
                enabled.append(rarity)
        if not enabled:
            continue
        available = []
        for rarity in enabled:
            available.extend(w for w in _available(rarity) if w["waifu_id"] not in exclude)
        if not available:
            continue
        with storage.connect() as con:
            history_ids = {
                row["waifu_id"] for row in con.execute(
                    "SELECT waifu_id FROM marketplace_history WHERE user_id=?", (uid,)
                )
            }
        # 5% repeat chance; otherwise prefer waifus this user has never seen in the market.
        if random.random() < 0.05:
            repeats = [w for w in available if w["waifu_id"] in history_ids]
            if repeats:
                return random.choice(repeats)
        fresh = [w for w in available if w["waifu_id"] not in history_ids]
        if fresh:
            return random.choice(fresh)
        return random.choice(available)
    return None


def _ensure_offers(uid: int, refresh: bool = False):
    day = day_key()
    with storage.connect() as con:
        existing = con.execute(
            "SELECT * FROM marketplace_slots WHERE user_id=? AND day_key=? ORDER BY slot",
            (uid, day)
        ).fetchall()
    if existing and not refresh:
        return existing

    selected = []
    exclude = set()
    for slot in (0, 1):
        w = _choose_offer(uid, exclude)
        if not w:
            continue
        exclude.add(w["waifu_id"])
        low, high = DISCOUNTS.get(w["rarity"], (5, 10))
        selected.append((slot, w, random.randint(low, high)))
    if not selected:
        raise ValueError("No eligible waifus are currently available in the marketplace.")

    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        if not refresh:
            current = con.execute(
                "SELECT * FROM marketplace_slots WHERE user_id=? AND day_key=? ORDER BY slot",
                (uid, day)
            ).fetchall()
            if current:
                con.rollback()
                return current
        else:
            refresh_row = con.execute(
                "SELECT refreshes FROM market_refreshes WHERE user_id=? AND day_key=?",
                (uid, day)
            ).fetchone()
            if refresh_row and refresh_row["refreshes"] >= 2:
                con.rollback()
                raise ValueError("Daily refresh limit reached (2/2).")
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (uid,))
            balance = con.execute("SELECT cash FROM user_balance WHERE user_id=?", (uid,)).fetchone()["cash"]
            if balance < 50_000:
                con.rollback()
                raise ValueError("You need 50,000 Cash to refresh.")
            con.execute("UPDATE user_balance SET cash=cash-50000 WHERE user_id=?", (uid,))
            con.execute(
                """INSERT INTO market_refreshes(user_id,day_key,refreshes) VALUES (?,?,1)
                ON CONFLICT(user_id,day_key) DO UPDATE SET refreshes=refreshes+1""",
                (uid, day)
            )
            con.execute("DELETE FROM marketplace_slots WHERE user_id=? AND day_key=?", (uid, day))

        inserted = 0
        for slot, w, discount in selected:
            still_available = con.execute(
                "SELECT 1 FROM waifus WHERE waifu_id=? AND deleted_at IS NULL AND image_file_id<>'' "
                "AND NOT EXISTS (SELECT 1 FROM auctions WHERE auctions.waifu_id=waifus.waifu_id)",
                (w["waifu_id"],)
            ).fetchone()
            if not still_available:
                continue
            con.execute(
                """INSERT INTO marketplace_slots(user_id,slot,waifu_id,discount_percent,day_key,purchased)
                VALUES (?,?,?,?,?,0)""",
                (uid, slot, w["waifu_id"], discount, day)
            )
            con.execute(
                """INSERT INTO marketplace_history(user_id,waifu_id,last_offered_at) VALUES (?,?,?)
                ON CONFLICT(user_id,waifu_id) DO UPDATE SET last_offered_at=excluded.last_offered_at""",
                (uid, w["waifu_id"], storage.now())
            )
            inserted += 1
        if not inserted:
            con.rollback()
            raise ValueError("Marketplace offers changed. Please try again.")
        con.commit()
        return con.execute(
            "SELECT * FROM marketplace_slots WHERE user_id=? AND day_key=? ORDER BY slot",
            (uid, day)
        ).fetchall()


def _owned_count(uid: int, wid: str) -> int:
    with storage.connect() as con:
        return con.execute(
            "SELECT COUNT(*) AS n FROM user_waifus WHERE user_id=? AND waifu_id=?",
            (uid, wid)
        ).fetchone()["n"]


def _market_text(uid: int, slot: int, offer):
    w = storage.get_waifu(offer["waifu_id"])
    if not w:
        return "Offer is no longer available."
    original = int(w["price"])
    sale = int(original * (100 - offer["discount_percent"]) / 100)
    status = "❎ PURCHASED" if offer["purchased"] else "🛒 AVAILABLE"
    return (
        "╔══════════════════════╗\n"
        "     🏪✨ DAILY MARKETPLACE ✨🏪\n"
        "╚══════════════════════╝\n"
        f"🎭 Name ➤ {w['name']}\n📺 Anime ➤ {w['anime']}\n"
        f"🆔 Waifu ID ➤ {w['waifu_id']}\n💫 Rarity ➤ {RARITIES[w['rarity']][0]} {w['rarity']}\n"
        f"💎 Original Price ➤ {_fmt(original)} Cash\n"
        f"💸 Sale Price ➤ {_fmt(sale)} Cash\n"
        f"📉 Discount ➤ {offer['discount_percent']}% OFF\n"
        f"🟢 Status ➤ {status}\n🎴 Owned ➤ {_owned_count(uid, w['waifu_id'])}\n"
        f"\n📦 Daily offer {slot + 1}/2"
    )


def _market_keyboard(uid: int, slot: int, offer):
    bought = bool(offer["purchased"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅", callback_data=f"mkt:{uid}:{1-slot}:view"),
         InlineKeyboardButton("Buy" if not bought else "❎", callback_data=f"mkt:{uid}:{slot}:buy" if not bought else "mktnoop"),
         InlineKeyboardButton("➡", callback_data=f"mkt:{uid}:{1-slot}:view")],
        [InlineKeyboardButton("♛ Auction", callback_data=f"mkt:{uid}:{slot}:auction"),
         InlineKeyboardButton("Refresh 50,000 Cash", callback_data=f"mkt:{uid}:{slot}:refresh")],
        [InlineKeyboardButton("Close", callback_data=f"mkt:{uid}:{slot}:close")]
    ])


async def marketplace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    try:
        offers = _ensure_offers(uid)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc))
        return
    if not offers:
        await update.effective_message.reply_text("There are no marketplace offers available right now.")
        return
    offer = offers[0]
    w = storage.get_waifu(offer["waifu_id"])
    await update.effective_message.reply_photo(
        w["image_file_id"], caption=_market_text(uid, 0, offer), has_spoiler=True,
        reply_markup=_market_keyboard(uid, 0, offer)
    )


async def marketplace_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.data == "mktnoop":
        await q.answer("This offer has already been purchased.")
        return
    _, owner_raw, slot_raw, action = q.data.split(":")
    uid, slot = int(owner_raw), int(slot_raw)
    if q.from_user.id != uid:
        await q.answer("This is another user's private marketplace.", show_alert=True)
        return
    day = day_key()
    if action == "close":
        await q.answer()
        await q.message.delete()
        return
    if action == "refresh":
        try:
            offers = _ensure_offers(uid, refresh=True)
        except ValueError as exc:
            await q.answer(str(exc), show_alert=True)
            return
        slot = 0
    elif action == "buy":
        with storage.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            daily = con.execute("SELECT purchases FROM market_daily_purchases WHERE user_id=? AND day_key=?", (uid, day)).fetchone()
            if daily and daily["purchases"] >= 2:
                con.rollback()
                await q.answer("Daily limit reached: you can buy only 2 waifus per day.", show_alert=True)
                return
            offer = con.execute(
                "SELECT * FROM marketplace_slots WHERE user_id=? AND slot=? AND day_key=?",
                (uid, slot, day)
            ).fetchone()
            if not offer or offer["purchased"]:
                con.rollback()
                await q.answer("Offer unavailable or already purchased.", show_alert=True)
                return
            w = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (offer["waifu_id"],)).fetchone()
            if not w:
                con.rollback()
                await q.answer("Waifu no longer available.", show_alert=True)
                return
            price = int(w["price"] * (100 - offer["discount_percent"]) / 100)
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (uid,))
            bal = con.execute("SELECT cash FROM user_balance WHERE user_id=?", (uid,)).fetchone()["cash"]
            if bal < price:
                con.rollback()
                await q.answer("Insufficient Cash. Earn more coins and try again.", show_alert=True)
                return
            con.execute("UPDATE user_balance SET cash=cash-? WHERE user_id=?", (price, uid))
            con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (uid, w["waifu_id"], storage.now(), "marketplace"))
            con.execute("UPDATE marketplace_slots SET purchased=1 WHERE user_id=? AND slot=? AND day_key=?", (uid, slot, day))
            con.execute("INSERT INTO market_daily_purchases(user_id,day_key,purchases) VALUES (?,?,1) ON CONFLICT(user_id,day_key) DO UPDATE SET purchases=purchases+1", (uid, day))
            con.execute("INSERT INTO transactions(tx_id,actor_id,action,amount,waifu_id,details,created_at) VALUES (?,?,?,?,?,?,?)",
                        (__import__("uuid").uuid4().hex, uid, "marketplace_buy", price, w["waifu_id"], json.dumps({"discount": offer["discount_percent"]}), storage.now()))
            con.commit()
        await q.answer("Purchase successful!")
        offers = _ensure_offers(uid)
    elif action == "auction":
        await q.answer()
        await _show_auction(q, uid)
        return
    else:
        offers = _ensure_offers(uid)
    offer = next((o for o in offers if int(o["slot"]) == slot), None)
    if not offer:
        await q.answer("Offer not available.", show_alert=True)
        return
    w = storage.get_waifu(offer["waifu_id"])
    await q.answer()
    await q.edit_message_media(
        media=InputMediaPhoto(media=w["image_file_id"], caption=_market_text(uid, slot, offer), has_spoiler=True),
        reply_markup=_market_keyboard(uid, slot, offer)
    )


async def auction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    args = context.args
    if not _sudo(uid):
        return
    if not args:
        await update.effective_message.reply_text(
            "AUCTION FORMAT\n/auction <waifu_id> <starting_bid> [hours]\n"
            "Example: /auction 2342 1000000 24\n/auction users"
        )
        return
    if args[0].lower() == "users":
        with storage.connect() as con:
            rows = con.execute(
                """SELECT b.bidder_id,b.amount,b.created_at,up.username,up.bot_user_id FROM auction_bids b
                JOIN auctions a ON a.auction_id=b.auction_id
                JOIN (SELECT auction_id,bidder_id,MAX(amount) AS max_amount
                      FROM auction_bids GROUP BY auction_id,bidder_id) latest
                  ON latest.auction_id=b.auction_id AND latest.bidder_id=b.bidder_id
                 AND latest.max_amount=b.amount
                LEFT JOIN user_profiles up ON up.user_id=b.bidder_id
                WHERE a.status='active'
                ORDER BY b.amount DESC,b.created_at ASC"""
            ).fetchall()
        if not rows:
            await update.effective_message.reply_text("No active auction bids.")
            return
        lines = ["🔨 AUCTION BIDDERS (highest first)"]
        for i, row in enumerate(rows, 1):
            if row["username"]:
                name = f"@{row['username']}"
            else:
                name = f"User {row['bot_user_id'] or storage.ensure_bot_user_id(row['bidder_id'])}"
            public_id = row["bot_user_id"] or storage.ensure_bot_user_id(row["bidder_id"])
            lines.append(f"{i}. {name} | ID: {public_id} | {_fmt(row['amount'])} Cash")
        await update.effective_message.reply_text("\n".join(lines))
        return
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await update.effective_message.reply_text("Usage: /auction <waifu_id> <starting_bid> [hours]")
        return
    wid, amount = args[0], int(args[1])
    try:
        hours = int(args[2]) if len(args) > 2 else 24
        if not 1 <= hours <= 168 or amount <= 0:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text("The starting bid must be positive and the duration must be 1–168 hours.")
        return
    w = storage.get_waifu(wid)
    if not w or not w["image_file_id"]:
        await update.effective_message.reply_text("THIS WAIFU IS NOT UPLOADED IN BOT DATA BASE.")
        return
    try:
        with storage.connect() as con:
            con.execute(
                "INSERT INTO auctions(waifu_id,seller_id,starting_bid,current_bid,ends_at,status,created_at) VALUES (?,?,?,?,?,'active',?)",
                (wid, uid, amount, amount, storage.now() + hours * 3600, storage.now())
            )
    except Exception:
        await update.effective_message.reply_text("This waifu is already listed in an auction.")
        return
    await update.effective_message.reply_photo(
        w["image_file_id"],
        caption=f"🎉 Auction Listed Successfully!\n\n{_display(w)}\n"
                f"💎 Starting Bid: {_fmt(amount)} Cash\n⌛ Duration: {hours} hours\n"
                "🏪 Users can view and bid from /marketplace."
    )


async def _show_auction(q, uid: int) -> None:
    with storage.connect() as con:
        auction = con.execute(
            "SELECT * FROM auctions WHERE status='active' AND ends_at>? ORDER BY ends_at LIMIT 1",
            (storage.now(),)
        ).fetchone()
    if not auction:
        await q.answer("AUCTION IS NOT AVAILABLE.", show_alert=True)
        return
    w = storage.get_waifu(auction["waifu_id"])
    remaining = max(0, auction["ends_at"] - storage.now())
    text = (
        f"🔨 AUCTION\n{_display(w)}\n"
        f"Starting bid: {_fmt(auction['starting_bid'])}\n"
        f"Current bid: {_fmt(auction['current_bid'])}\n"
        f"Bidders: {_bidder_count(auction['auction_id'])}\n"
        f"Time left: {remaining//3600}h {(remaining%3600)//60}m"
    )
    await q.message.reply_photo(w["image_file_id"], caption=text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Bid Amount", callback_data=f"aucbid:{uid}:{auction['auction_id']}"),
                                            InlineKeyboardButton("Back", callback_data=f"mkt:{uid}:0:view")]]))


def _bidder_count(auction_id: int) -> int:
    with storage.connect() as con:
        return con.execute("SELECT COUNT(DISTINCT bidder_id) AS n FROM auction_bids WHERE auction_id=?", (auction_id,)).fetchone()["n"]


async def auction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    _, uid, auction_id = q.data.split(":")
    if q.from_user.id != int(uid):
        await q.answer("This auction button belongs to another user.", show_alert=True)
        return
    context.user_data["active_auction_id"] = int(auction_id)
    await q.answer()
    await q.message.reply_text("Send /bid <amount> in this chat to place a bid.")


async def bid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    auction_id = context.user_data.get("active_auction_id")
    if not auction_id or not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Open the auction using the Marketplace button, then send /bid <amount>.")
        return
    amount = int(context.args[0])
    with storage.connect() as con:
        auction = con.execute("SELECT * FROM auctions WHERE auction_id=? AND status='active' AND ends_at>?", (auction_id, storage.now())).fetchone()
        if not auction:
            await update.effective_message.reply_text("AUCTION IS NOT AVAILABLE.")
            return
        if int(auction["seller_id"]) == uid:
            await update.effective_message.reply_text("You cannot bid on your own auction.")
            return
        current = max(int(auction["current_bid"]), int(auction["starting_bid"]))
        if amount <= current:
            await update.effective_message.reply_text(f"Your bid must be higher than the current bid of {_fmt(current)}.")
            return
        cash, _ = storage.get_balance(uid)
        if cash < amount:
            await update.effective_message.reply_text("❌ Insufficient balance for this bid.")
            return
    token = storage.create_pending(uid, "auction_bid", {"auction_id": auction_id, "amount": amount}, 60)
    await update.effective_message.reply_text(
        f"🔨 BID CONFIRMATION\n\nYour bid: {_fmt(amount)} Cash\nCurrent bid: {_fmt(current)} Cash\n"
        "Cash will not be deducted now. You will be charged only if you win the auction. Confirm?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm Bid", callback_data=f"bidok:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"bidno:{token}")
        ]])
    )


async def bid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "auction_bid")
    if not pending:
        await q.answer("Bid request expired.", show_alert=True)
        return
    data = json.loads(pending["payload"])
    if action == "bidno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Bid cancelled.")
        await q.edit_message_text("❌ Bid cancelled. No cash was charged.")
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        auction = con.execute(
            "SELECT * FROM auctions WHERE auction_id=? AND status='active' AND ends_at>?",
            (int(data["auction_id"]), storage.now())
        ).fetchone()
        if not auction or int(auction["seller_id"]) == q.from_user.id:
            con.rollback()
            await q.answer("Auction is no longer available.", show_alert=True)
            return
        amount = int(data["amount"])
        current = max(int(auction["current_bid"]), int(auction["starting_bid"]))
        if amount <= current:
            con.rollback()
            await q.answer(f"Someone has already bid {_fmt(current)}. Submit a higher bid.", show_alert=True)
            return
        con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (q.from_user.id,))
        bal = con.execute("SELECT cash FROM user_balance WHERE user_id=?", (q.from_user.id,)).fetchone()["cash"]
        if bal < amount:
            con.rollback()
            await q.answer("Insufficient balance.", show_alert=True)
            return
        con.execute("UPDATE auctions SET current_bid=?,highest_bidder=? WHERE auction_id=?", (amount, q.from_user.id, int(data["auction_id"])))
        con.execute("INSERT INTO auction_bids(auction_id,bidder_id,amount,created_at) VALUES (?,?,?,?)", (int(data["auction_id"]), q.from_user.id, amount, storage.now()))
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        con.commit()
    await q.answer("Bid confirmed!")
    await q.edit_message_text(f"✅ BID CONFIRMED\nYour bid: {_fmt(amount)} Cash\nYou are now the highest bidder.")


async def settle_auctions(context: ContextTypes.DEFAULT_TYPE) -> None:
    due_ids = []
    with storage.connect() as con:
        due_ids = [r["auction_id"] for r in con.execute(
            "SELECT auction_id FROM auctions WHERE status='active' AND ends_at<=?", (storage.now(),)
        ).fetchall()]
    for auction_id in due_ids:
        winner = None
        waifu = None
        with storage.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            auction = con.execute("SELECT * FROM auctions WHERE auction_id=? AND status='active'", (auction_id,)).fetchone()
            if not auction or auction["ends_at"] > storage.now():
                con.rollback()
                continue
            bids = con.execute("SELECT bidder_id,amount FROM auction_bids WHERE auction_id=? ORDER BY amount DESC,created_at ASC", (auction_id,)).fetchall()
            for bid in bids:
                bal = con.execute("SELECT cash FROM user_balance WHERE user_id=?", (bid["bidder_id"],)).fetchone()
                if bal and bal["cash"] >= bid["amount"]:
                    winner = bid
                    break
            waifu = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (auction["waifu_id"],)).fetchone()
            if winner and waifu:
                con.execute("UPDATE user_balance SET cash=cash-? WHERE user_id=?", (winner["amount"], winner["bidder_id"]))
                con.execute("INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)", (winner["bidder_id"], auction["waifu_id"], storage.now(), "auction"))
                con.execute("INSERT INTO transactions(tx_id,actor_id,action,amount,waifu_id,created_at) VALUES (?,?,?,?,?,?)",
                            (__import__("uuid").uuid4().hex, winner["bidder_id"], "auction_win", winner["amount"], auction["waifu_id"], storage.now()))
                con.execute("UPDATE auctions SET status='completed' WHERE auction_id=?", (auction_id,))
            else:
                con.execute("UPDATE auctions SET status='expired' WHERE auction_id=?", (auction_id,))
            con.commit()
        if winner and waifu:
            try:
                await context.bot.send_photo(winner["bidder_id"], waifu["image_file_id"],
                    caption=f"🎉 AUCTION WON!\n{_display(waifu)}\nPaid: {_fmt(winner['amount'])} Cash. Added to your /collection.")
            except Exception:
                pass
        else:
            # No valid funded bid remained at settlement time.
            pass



async def marketspawn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /marketspawn <rarity> on/off")
        return
    rarity = _rarity_name(context.args[0])
    status = context.args[1].lower()
    if rarity not in COMMON_POOL + RARE_POOL or status not in {"on", "off"}:
        await update.effective_message.reply_text("Invalid marketplace rarity or on/off value.")
        return
    with storage.connect() as con:
        con.execute(
            "INSERT INTO market_rarity_settings(rarity,enabled) VALUES (?,?) ON CONFLICT(rarity) DO UPDATE SET enabled=excluded.enabled",
            (rarity, int(status == "on"))
        )
    await update.effective_message.reply_text(f"🏪 Marketplace {rarity} offers {status.upper()}.")
