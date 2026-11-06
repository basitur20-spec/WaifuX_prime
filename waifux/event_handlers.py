"""One-time reward events, group filters and owner broadcast."""
from __future__ import annotations

import uuid
import asyncio

from telegram import Update
from telegram.constants import ChatMemberStatus, ChatType
from telegram.ext import ContextTypes

from . import storage
from .waifu_handlers import _owner


async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    with storage.connect() as con:
        con.execute(
            """INSERT INTO user_profiles(user_id,username,first_name,updated_at)
            VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,first_name=excluded.first_name,updated_at=excluded.updated_at""",
            (user.id, user.username, user.first_name, storage.now())
        )
        con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (user.id,))
    storage.ensure_bot_user_id(user.id)


async def gclaim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.effective_message.reply_text(
            "GCLAIM HELP\n/gclaim 500000 — cash\n/gclaim 200 d — diamonds\n/gclaim waifu 1234 — waifu"
        )
        return
    if args[0].lower() == "waifu" and len(args) == 2:
        w = storage.get_waifu(args[1])
        if not w:
            await update.effective_message.reply_text("Waifu ID not found.")
            return
        reward_type, value = "waifu", args[1]
    elif len(args) == 2 and args[1].lower() in {"d", "diamond", "diamonds"} and args[0].isdigit():
        reward_type, value = "diamonds", args[0]
    elif len(args) == 1 and args[0].isdigit():
        reward_type, value = "cash", args[0]
    else:
        await update.effective_message.reply_text("Invalid format. Use /gclaim 500000, /gclaim 200 d, or /gclaim waifu 1234.")
        return
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE claim_events SET active=0")
        con.execute(
            "INSERT INTO claim_events(event_name,reward_type,reward_value,active,created_at) VALUES (?,?,?,?,?)",
            ("Community Reward", reward_type, value, 1, storage.now())
        )
        con.commit()
    await update.effective_message.reply_text("✅ Claim reward created. Users can now use /claim once.")


async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    with storage.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        event = con.execute(
            "SELECT * FROM claim_events WHERE active=1 ORDER BY event_id DESC LIMIT 1"
        ).fetchone()
        if not event:
            con.rollback()
            await update.effective_message.reply_text("😔 No rewards available right now.")
            return
        try:
            con.execute(
                "INSERT INTO user_claims(event_id,user_id,claimed_at) VALUES (?,?,?)",
                (event["event_id"], uid, storage.now())
            )
        except Exception:
            con.rollback()
            await update.effective_message.reply_text("❌ You have already claimed this reward.")
            return
        value = event["reward_value"]
        if event["reward_type"] == "cash":
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (uid,))
            con.execute("UPDATE user_balance SET cash=cash+? WHERE user_id=?", (int(value), uid))
            reward_text = f"💰 {_fmt(int(value))} Cash"
        elif event["reward_type"] == "diamonds":
            con.execute("INSERT OR IGNORE INTO user_balance(user_id) VALUES (?)", (uid,))
            con.execute("UPDATE user_balance SET diamonds=diamonds+? WHERE user_id=?", (int(value), uid))
            reward_text = f"💎 {int(value):,} Diamonds"
        else:
            waifu = con.execute("SELECT * FROM waifus WHERE waifu_id=? AND deleted_at IS NULL", (value,)).fetchone()
            if not waifu:
                con.rollback()
                await update.effective_message.reply_text("Reward waifu no longer exists.")
                return
            con.execute(
                "INSERT INTO user_waifus(user_id,waifu_id,obtained_at,source) VALUES (?,?,?,?)",
                (uid, value, storage.now(), "claim")
            )
            reward_text = f"🌸 {waifu['name']} ({value})"
        con.execute(
            "INSERT INTO transactions(tx_id,actor_id,action,amount,waifu_id,created_at) VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex, uid, "event_claim", int(value) if event["reward_type"] != "waifu" else 0,
             value if event["reward_type"] == "waifu" else None, storage.now())
        )
        con.commit()
    if event["reward_type"] == "waifu":
        await update.effective_message.reply_photo(waifu["image_file_id"], caption=f"🎉 Congratulations! You claimed your reward!\n{reward_text}")
    else:
        await update.effective_message.reply_text(f"🎉 Congratulations! You claimed your reward!\n{reward_text}")


def _fmt(value: int) -> str:
    return f"{int(value):,}"


async def _is_chat_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == ChatType.PRIVATE:
        return False
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with storage.connect() as con:
        rows = con.execute("SELECT keyword FROM chat_filters WHERE chat_id=? ORDER BY keyword", (update.effective_chat.id,)).fetchall()
    await update.effective_message.reply_text(
        "📋 Chat filters:\n" + ("\n".join(row["keyword"] for row in rows) if rows else "No filters added.")
    )


async def filter_add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_chat_admin(update, context):
        return
    raw = update.effective_message.text.partition(" ")[2].strip()
    if "|" not in raw:
        await update.effective_message.reply_text("Usage: /filter <keyword> | <response>")
        return
    keyword, response = (part.strip() for part in raw.split("|", 1))
    if not keyword or not response:
        await update.effective_message.reply_text("Both a keyword and a response are required.")
        return
    with storage.connect() as con:
        con.execute(
            "INSERT INTO chat_filters(chat_id,keyword,response,created_by) VALUES (?,?,?,?) ON CONFLICT(chat_id,keyword) DO UPDATE SET response=excluded.response,created_by=excluded.created_by",
            (update.effective_chat.id, keyword.casefold(), response, update.effective_user.id)
        )
    await update.effective_message.reply_text(f"✅ Filter '{keyword}' added.")


async def filter_delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_chat_admin(update, context):
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /delfilter <keyword>")
        return
    with storage.connect() as con:
        cur = con.execute("DELETE FROM chat_filters WHERE chat_id=? AND keyword=?", (update.effective_chat.id, " ".join(context.args).casefold()))
    await update.effective_message.reply_text("Filter deleted." if cur.rowcount else "Filter not found.")


async def filter_delete_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_chat_admin(update, context):
        return
    with storage.connect() as con:
        con.execute("DELETE FROM chat_filters WHERE chat_id=?", (update.effective_chat.id,))
    await update.effective_message.reply_text("✅ All chat filters deleted.")


async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text or msg.text.startswith("/"):
        return
    with storage.connect() as con:
        rows = con.execute("SELECT keyword,response FROM chat_filters WHERE chat_id=?", (msg.chat_id,)).fetchall()
    text = msg.text.casefold()
    for row in rows:
        if row["keyword"] in text:
            await msg.reply_text(row["response"])
            return


async def send_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _owner(update.effective_user.id):
        return
    msg = update.effective_message
    text = msg.text.partition(" ")[2].strip()
    source = msg.reply_to_message
    if not text and not source:
        await msg.reply_text("Usage: /send <message> or reply to a message/media with /send.")
        return
    with storage.connect() as con:
        rows = con.execute("SELECT user_id FROM user_profiles").fetchall()
    sent = failed = 0
    for row in rows:
        target_id = row["user_id"]
        try:
            if source:
                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=msg.chat_id,
                    message_id=source.message_id
                )
            else:
                await context.bot.send_message(target_id, text)
            sent += 1
        except Exception as exc:
            retry_after = getattr(exc, "retry_after", None)
            if retry_after:
                await asyncio.sleep(float(retry_after))
                try:
                    if source:
                        await context.bot.copy_message(
                            chat_id=target_id,
                            from_chat_id=msg.chat_id,
                            message_id=source.message_id
                        )
                    else:
                        await context.bot.send_message(target_id, text)
                    sent += 1
                    continue
                except Exception:
                    pass
            failed += 1
        await asyncio.sleep(0.03)
    await msg.reply_text(f"📢 Broadcast complete. Sent: {sent}, failed: {failed}.")
