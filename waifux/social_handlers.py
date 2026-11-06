"""User-to-user trades and privileged waifu grants."""
from __future__ import annotations

import json
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from . import storage
from .waifu_handlers import _owner, _sudo, _uploader, _display


async def trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target or target.is_bot or target.id == update.effective_user.id:
        await msg.reply_text("Trade ke liye doosre user ke message par reply karo.")
        return
    if len(context.args) != 2 or not all(x.isdigit() for x in context.args):
        await msg.reply_text("Usage: reply to user message, then /trade <your_waifu_id> <their_waifu_id>")
        return
    actor = update.effective_user.id
    own = storage.owned_waifu(actor, context.args[0])
    theirs = storage.owned_waifu(target.id, context.args[1])
    if not own:
        await msg.reply_text("Tumhari collection mein pehli waifu ID nahi mili.")
        return
    if not theirs:
        await msg.reply_text("Target user ke collection mein doosri waifu ID nahi mili.")
        return
    payload = {
        "initiator_id": actor, "target_id": target.id,
        "initiator_waifu": own["waifu_id"], "target_waifu": theirs["waifu_id"],
        "initiator_name": update.effective_user.full_name, "target_name": target.full_name,
    }
    token = storage.create_pending(actor, "trade", payload, 120)
    await msg.reply_text(
        f"🔁 TRADE REQUEST\n\nYou offer: {own['name']} ({own['waifu_id']})\n"
        f"You receive: {theirs['name']} ({theirs['waifu_id']})\n"
        f"Trade partner: {target.full_name}\n\n"
        "Trade tabhi complete hogi jab doosra user accept kare.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Accept Trade", callback_data=f"trdaccept:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"trdcancel:{token}")
        ]])
    )


async def trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    with storage.connect() as con:
        row = con.execute(
            "SELECT * FROM pending_actions WHERE token=? AND action='trade' AND status='pending' AND expires_at>=?",
            (token, storage.now())
        ).fetchone()
        if not row:
            await q.answer("Trade request expire ho gayi.", show_alert=True)
            return
        data = json.loads(row["payload"])
        actor, target = int(data["initiator_id"]), int(data["target_id"])
        if q.from_user.id not in (actor, target):
            await q.answer("Ye trade tumhare liye nahi hai.", show_alert=True)
            return
        if action == "trdaccept" and q.from_user.id != target:
            await q.answer("Trade partner hi accept kar sakta hai.", show_alert=True)
            return
        if action == "trdcancel":
            con.execute("UPDATE pending_actions SET status='cancelled' WHERE token=?", (token,))
            con.commit()
            await q.answer("Trade cancelled.")
            await q.edit_message_text("❌ Trade request cancelled.")
            return
        con.execute("BEGIN IMMEDIATE")
        own_a = con.execute(
            "SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=? ORDER BY obtained_at LIMIT 1",
            (actor, data["initiator_waifu"])
        ).fetchone()
        own_b = con.execute(
            "SELECT id FROM user_waifus WHERE user_id=? AND waifu_id=? ORDER BY obtained_at LIMIT 1",
            (target, data["target_waifu"])
        ).fetchone()
        if not own_a or not own_b:
            con.rollback()
            await q.answer("Collection update ho chuki hai; trade complete nahi ho sakti.", show_alert=True)
            return
        con.execute("DELETE FROM user_waifus WHERE id=?", (own_a["id"],))
        con.execute("DELETE FROM user_waifus WHERE id=?", (own_b["id"],))
        con.execute(
            "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
            (actor, data["target_waifu"], storage.now(), "trade")
        )
        con.execute(
            "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
            (target, data["initiator_waifu"], storage.now(), "trade")
        )
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        for user_id, target_id, wid in (
            (actor, target, data["target_waifu"]), (target, actor, data["initiator_waifu"])
        ):
            con.execute(
                "INSERT INTO transactions(tx_id,actor_id,target_id,action,waifu_id,created_at) VALUES (?,?,?,?,?,?)",
                (uuid.uuid4().hex, user_id, target_id, "trade", wid, storage.now())
            )
        con.commit()
    await q.answer("Trade successful!")
    await q.edit_message_text("🎉 TRADE COMPLETED! Donon users ki collections update ho gayi hain.")
    for recipient, wid in ((actor, data["target_waifu"]), (target, data["initiator_waifu"])):
        w = storage.get_waifu(wid)
        if w:
            try:
                await context.bot.send_photo(
                    recipient, w["image_file_id"],
                    caption=f"🔁 Trade successful! Ye waifu tumhari /collection mein add ho gayi.\n{_display(w)}"
                )
            except Exception:
                pass


async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not (_owner(uid) or _sudo(uid) or _uploader(uid)):
        return
    msg = update.effective_message
    replied_user = msg.reply_to_message.from_user if msg.reply_to_message else None
    if context.args and context.args[0].lower() == "history":
        if not _owner(uid):
            return
        with storage.connect() as con:
            if replied_user:
                rows = con.execute(
                    "SELECT actor_id,target_id,waifu_id,created_at FROM transactions WHERE action='admin_gift' AND actor_id=? ORDER BY created_at DESC LIMIT 30",
                    (replied_user.id,)
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT actor_id,target_id,waifu_id,created_at FROM transactions WHERE action='admin_gift' ORDER BY created_at DESC LIMIT 30"
                ).fetchall()
        if not rows:
            await msg.reply_text("📭 No give history found.")
            return
        await msg.reply_text(
            "📜 GIVE COMMAND HISTORY\n" + "\n".join(
                f"{i}. {r['actor_id']} → {r['target_id']} | Waifu {r['waifu_id']} | {r['created_at']}"
                for i, r in enumerate(rows, 1)
            )
        )
        return
    if not context.args or not context.args[0].isdigit():
        await msg.reply_text("📦 GIVE WAIFU — USAGE GUIDE\nReply to a user: /give <waifu_id>\nUsing username or user ID: /give <waifu_id> @username_or_id")
        return
    target_id = None
    target_name = None
    if replied_user and not replied_user.is_bot:
        target_id, target_name = replied_user.id, replied_user.full_name
    elif len(context.args) >= 2:
        target_ref = context.args[1].lstrip("@")
        with storage.connect() as con:
            if target_ref.isdigit():
                target = con.execute("SELECT user_id,first_name,username FROM user_profiles WHERE user_id=?", (int(target_ref),)).fetchone()
            else:
                target = con.execute("SELECT user_id,first_name,username FROM user_profiles WHERE lower(username)=lower(?)", (target_ref,)).fetchone()
        if target:
            target_id = int(target["user_id"])
            target_name = target["first_name"] or (f"@{target['username']}" if target["username"] else str(target_id))
    if target_id is None:
        await msg.reply_text("⚠️ User not found. Reply to their message or use a username/user ID already known to the bot.")
        return
    if target_id == uid and not _owner(uid):
        await msg.reply_text("🚫 Sudo/uploader apne aap ko waifu gift nahi kar sakte.")
        return
    w = storage.get_waifu(context.args[0])
    if not w:
        await msg.reply_text("⚠️ Invalid Waifu ID. This waifu does not exist.")
        return
    token = storage.create_pending(uid, "admin_gift", {
        "target_id": target_id, "waifu_id": w["waifu_id"], "target_name": target_name
    }, 60)
    await msg.reply_photo(
        w["image_file_id"], caption=f"🎁 CONFIRM WAIFU GIFT\n{_display(w)}\nReceiver: {target_name}\nConfirm gift?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm Gift", callback_data=f"giveok:{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"givno:{token}")
        ]])
    )


async def give_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    action, token = q.data.split(":")
    pending = storage.get_pending(token, q.from_user.id, "admin_gift")
    if not pending:
        await q.answer("Request expire ho gayi.", show_alert=True)
        return
    data = json.loads(pending["payload"])
    if action == "givno":
        storage.finish_pending(token, "cancelled")
        await q.answer("Gift cancelled.")
        await q.edit_message_caption("Gift cancelled.")
        return
    w = storage.get_waifu(data["waifu_id"])
    if not w:
        await q.answer("Waifu no longer exists.", show_alert=True)
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
            (data["target_id"], data["waifu_id"], storage.now(), "admin_gift")
        )
        con.execute("UPDATE pending_actions SET status='done' WHERE token=?", (token,))
        con.execute(
            "INSERT INTO transactions(tx_id,actor_id,target_id,action,waifu_id,created_at) VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex, q.from_user.id, data["target_id"], "admin_gift", data["waifu_id"], storage.now())
        )
        con.commit()
    await q.answer("Gift sent.")
    await q.edit_message_caption("🎉 Gift successfully sent.")
    try:
        await context.bot.send_photo(
            data["target_id"], w["image_file_id"],
            caption=f"🎁 You received a waifu gift!\n{_display(w)}\nAdded to your /collection."
        )
    except Exception:
        pass
