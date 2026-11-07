import os
import json
import random
import time
import sqlite3

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------------------
# CONFIG
# ---------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("Bot_Token")
OWNER_MENTION = "@Basit_ur"
DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
BOT_DATA_FILE = f"{DATA_DIR}/bot_data.json"
USER_INFO_FILE = f"{DATA_DIR}/user_info.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------
# FILE SYSTEM
# ---------------------------
def ensure_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    for f_path in [USERS_FILE, BOT_DATA_FILE, USER_INFO_FILE]:
        if not os.path.exists(f_path):
            with open(f_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

def load_users():
    ensure_files()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    ensure_files()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------------------
# /START COMMAND
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_files()
    user = update.effective_user

    text = (
        f"𝐇𝐄𝐋𝐋𝐎🕊️ {user.first_name},\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ 𝑊𝑒𝑙𝑐𝑜𝑚𝑒 𝑡𝑜 𝑾𝒂𝒊𝒇𝒖𝑿_𝑷𝒓𝒊𝒎𝒆 ✨\n\n"
        "𝙸 𝚊𝚖 𝚢𝚘𝚞𝚛 𝚞𝚕𝚝𝚒𝚖𝚊𝚝𝚎 𝚊𝚗𝚒𝚖𝚎 𝚠𝚊𝚒𝚏𝚞 𝚌𝚘𝚖𝚙𝚊𝚗𝚒𝚘𝚗.\n"
        "𝙰𝚍𝚍 𝚖𝚎 𝚝𝚘 𝚢𝚘𝚞𝚛 𝚐𝚛𝚘𝚞𝚙 𝚊𝚗𝚍 𝚜𝚝𝚊𝚛𝚝 𝚢𝚘𝚞𝚛 𝚓𝚘𝚞𝚛𝚗𝚎𝚢 𝚗𝚘𝚠!\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [
            InlineKeyboardButton("𝑼𝑷𝑫𝑨𝑻𝑬𝑺💫", url="https://t.me/+4UJ1aAf4-ypiNThk"),
            InlineKeyboardButton("𝑺𝑼𝑷𝑷𝑶𝑹𝑻🏪", url="https://t.me/+LfvrnvE8x3I3OGU0"),
        ],
        [
            InlineKeyboardButton(
                "𝑺𝑻𝑨𝑹𝑻 𝑱𝑶𝑼𝑹𝑵𝑬𝒀✨",
                url=f"https://t.me/{context.bot.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton("𝑮𝑹𝑶𝑼𝑷☘️", url="https://t.me/movieandweb_s_group"),
            InlineKeyboardButton("𝑯𝑬𝑳𝑷⚙", callback_data="OPEN_HELP"),
        ],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------
# EDIT START MESSAGE (BACK)
# ---------------------------
async def edit_start_message(query, context: ContextTypes.DEFAULT_TYPE):
    ensure_files()
    user = query.from_user

    text = (
        f"𝐇𝐄𝐋𝐋𝐎🕊️ {user.first_name},\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ 𝑊𝑒𝑙𝑐𝑜𝑚𝑒 𝑡𝑜 𝑾𝒂𝒊𝒇𝒖𝑿_𝑷𝒓𝒊𝒎𝒆 ✨\n\n"
        "𝙸 𝚊𝚖 𝚢𝚘𝚞𝚛 𝚞𝚕𝚝𝚒𝚖𝚊𝚝𝚎 𝚊𝚗𝚒𝚖𝚎 𝚠𝚊𝚒𝚏𝚞 𝚌𝚘𝚖𝚙𝚊𝚗𝚒𝚘𝚗.\n"
        "𝙰𝚍𝚍 𝚖𝚎 𝚝𝚘 𝚢𝚘𝚞𝚛 𝚐𝚛𝚘𝚞𝚙 𝚊𝚗𝚍 𝚜𝚝𝚊𝚛𝚝 𝚢𝚘𝚞𝚛 𝚓𝚘𝚞𝚛𝚗𝚎𝚢 𝚗𝚘𝚠!\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [
            InlineKeyboardButton("𝑼𝑷𝑫𝑨𝑻𝑬𝑺💫", url="https://t.me/+4UJ1aAf4-ypiNThk"),
            InlineKeyboardButton("𝑺𝑼𝑷𝑷𝑶𝑹𝑻🏪", url="https://t.me/+LfvrnvE8x3I3OGU0"),
        ],
        [
            InlineKeyboardButton(
                "𝑺𝑻𝑨𝑹𝑻 𝑱𝑶𝑼𝑹𝑵𝑬𝒀✨",
                url=f"https://t.me/{context.bot.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton("𝑮𝑹𝑶𝑼𝑷☘️", url="https://t.me/movieandweb_s_group"),
            InlineKeyboardButton("𝑯𝑬𝑳𝑷⚙", callback_data="OPEN_HELP"),
        ],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------
# HELP MENUS
# ---------------------------
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "📘 HELP CENTER\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select a category below to learn how commands work.\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [
            InlineKeyboardButton("𝑪𝑶𝑴𝑴𝑨𝑵𝑫𝑺 📜", callback_data="HELP_COMMANDS_1"),
            InlineKeyboardButton("𝑮𝑨𝑴𝑬𝑺 🎮", callback_data="HELP_GAMES"),
        ],
        [InlineKeyboardButton("𝑩𝑨𝑪𝑲 ⬅", callback_data="HELP_BACK_TO_START")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_commands_page1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "/balance\n→ Check your cash and diamonds\n\n"
        "/explore\n→ Explore and earn rewards\n\n"
        "/bonus\n→ Claim daily or weekly bonus\n\n"
        "/pay\n→ Transfer coins to another user\n\n"
        "/roll\n→ Play odd/even dice\n\n"
        "/darts\n→ Play the darts betting game\n\n"
        "/goal\n→ Play the goal betting game\n\n"
        "/mines\n→ Play the mines game"
    )

    keyboard = [
        [
            InlineKeyboardButton("𝑵𝒆𝒙𝒕 𝑷𝒂𝒈𝒆 ➡", callback_data="HELP_COMMANDS_2"),
            InlineKeyboardButton("𝑩𝒂𝒄𝒌 ⬅", callback_data="OPEN_HELP"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_commands_page2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "/collection\n→ View your collected waifu IDs\n\n"
        "/dtops\n→ View the leaderboard\n\n"
        "/gen\n→ Generate cash or diamond codes (staff)\n\n"
        "/redeem\n→ Redeem a cash or diamond code\n\n"
        "/dgen\n→ Generate waifu codes (staff)\n\n"
        "/dredeem\n→ Redeem a waifu code\n\n"
        "/redeemtoggle on/off\n→ Control staff cash-code redemption\n\n"
        "/dredeemtoggle on/off\n→ Control staff waifu-code redemption"
    )

    keyboard = [[InlineKeyboardButton("𝑩𝒂𝒄𝒌 ⬅", callback_data="HELP_COMMANDS_1")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "/roll\n→ To Roll dice 🎲 (odd/even)\n\n"
        "/darts\n→ To Bet in darts 🎯\n\n"
        "/goal\n→ To Bet in goal ⚽\n\n"
        "/mines\n→ Play mines 💣💥"
    )

    keyboard = [[InlineKeyboardButton("𝑩𝒂𝒄𝒌 ⬅", callback_data="OPEN_HELP")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------
# CALLBACK ROUTER
# ---------------------------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # 🔒 Safety
    if not data:
        return

    # ===========================
    # BONUS SYSTEM ROUTE
    # ===========================
    if data.startswith("bonus_"):
        await bonus_callback(update, context)
        return

    # ===========================
    # HELP SYSTEM ROUTE
    # ===========================
    if data == "OPEN_HELP":
        await help_menu(update, context)

    elif data == "HELP_COMMANDS_1":
        await help_commands_page1(update, context)

    elif data == "HELP_COMMANDS_2":
        await help_commands_page2(update, context)

    elif data == "HELP_GAMES":
        await help_games(update, context)

    elif data == "HELP_BACK_TO_START":
        await edit_start_message(query, context)

    # ===========================
    # UNKNOWN CALLBACK (SAFE EXIT)
    # ===========================
    else:
        await query.answer("❌ Invalid action", show_alert=False)


# ---------------------------
# SUDO SYSTEM CORE (UPDATED)
# ---------------------------
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json

SUDO_FILE = "sudo_users.json"
OWNER_ID = 8163432539  # Your Telegram ID

# ---------------------------
# JSON DB helpers
# ---------------------------
def load_sudo():
    try:
        with open(SUDO_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_sudo(sudo_list):
    with open(SUDO_FILE, "w") as f:
        json.dump(sudo_list, f)


# ---------------------------
# OWNER CHECK
# ---------------------------
def is_sudo_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


# ---------------------------
# ADD SUDO
# ---------------------------
async def add_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo_owner(update.effective_user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("Reply to a user to add as SUDO.")
        return

    user_id = reply.from_user.id
    username = reply.from_user.username or reply.from_user.first_name or str(user_id)
    sudo_list = load_sudo()

    if user_id in sudo_list:
        await update.message.reply_text("⚠️ This user is already a SUDO.")
        return

    sudo_list.append(user_id)
    save_sudo(sudo_list)

    # Owner feedback
    await update.message.reply_text(
        f"✅ SUDO ADDED SUCCESSFULLY!\nUser @{username} has been promoted to SUDO."
    )

    # DM to new SUDO with button
    try:
        keyboard = [[InlineKeyboardButton("𝑪𝑶𝑴𝑴𝑨𝑵𝑫𝑺", callback_data="SUDO_GUIDE")]]
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 CONGRATULATIONS @{username}!\n"
                f"You have been promoted to SUDO.\n\n"
                f"Tap the button below to view all SUDO commands."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except:
        pass


# ---------------------------
# REMOVE SUDO
# ---------------------------
async def remove_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo_owner(update.effective_user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("Reply to a SUDO user to remove.")
        return

    user_id = reply.from_user.id
    username = reply.from_user.username or reply.from_user.first_name or str(user_id)
    sudo_list = load_sudo()

    if user_id not in sudo_list:
        await update.message.reply_text("⚠️ This user is not a SUDO.")
        return

    sudo_list.remove(user_id)
    save_sudo(sudo_list)

    await update.message.reply_text(
        f"🗑️ SUDO REMOVED SUCCESSFULLY!\nUser @{username} has been removed from SUDO role."
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Your SUDO access has been revoked by the owner.",
        )
    except:
        pass


# ---------------------------
# SUDO LIST (username + name)
# ---------------------------
async def sudo_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_sudo_owner(user_id) and not is_sudo(user_id):
        return

    sudo_list = load_sudo()
    if not sudo_list:
        await update.message.reply_text("No SUDO users found.")
        return

    msg = "👑 SUDO USERS LIST\n\n"
    for i, uid in enumerate(sudo_list, 1):
        try:
            user = await context.bot.get_chat(uid)
            name = user.first_name or "Hidden"
            username = f"@{user.username}" if user.username else ""
            msg += f"{i}. {name} {username} | ID: {uid}\n"
        except:
            msg += f"{i}. Unknown | ID: {uid}\n"

    await update.message.reply_text(msg)


# ---------------------------
# SUDO COMMANDS
# ---------------------------
SUDO_COMMANDS = [
    "/gen <amount> <quantity> [cash/dimond]",
    "/dgen <waifu_id> <quantity>",
    "/changetime <2-120 minutes>",
    "/give <waifu_id> <username|bot_user_id>",
    "/dtops",
    "/sudolist",
    "/sudocommands",
]


SUDO_EXAMPLES = {
    "/auction <waifu_id> <starting_bid> [hours]": "Create a 24-hour auction by default. Example: /auction 2342 1000000",
    "/auction users": "View active auction bidders. Example: /auction users",
    "/gen <amount> <quantity> [cash/dimond]": "Generate cash/diamond codes. Example: /gen 500000 10",
    "/dgen <waifu_id> <quantity>": "Generate waifu codes. Example: /dgen 2947 5",
    "/changetime <2-120 minutes>": "Change group spawn timing. Example: /changetime 10",
    "/dupload <waifu_id>": "Delete an uploaded waifu. Example: /dupload 38429",
    "/give <waifu_id> <username|bot_user_id>": "Grant a waifu to a user.",
    "/dtops": "View rarity-wise waifu upload statistics.",
    "/sudolist": "View Sudo members.",
    "/sudocommands": "Open the Sudo command guide.",
}


def build_sudo_commands_text() -> str:
    text = "🛡️ SUDO COMMAND PANEL\n\n"
    for cmd in SUDO_COMMANDS:
        text += f"{cmd}\n{SUDO_EXAMPLES.get(cmd, '')}\n\n"
    return text


async def sudo_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sudo_list = load_sudo()
    if not is_sudo_owner(user_id) and user_id not in sudo_list:
        return

    text = build_sudo_commands_text()

    # If used in group, send to DM
    if update.message.chat.type != "private":
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except:
            await update.message.reply_text(
                "Cannot send DM. Please start a chat with the bot first."
            )
    else:
        await update.message.reply_text(text)


# ---------------------------
# DM BUTTON CALLBACK (SUDO_GUIDE)
# ---------------------------
async def sudo_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_sudo_owner(query.from_user.id) and not is_sudo(query.from_user.id):
        await query.answer("This guide is only for Owner and Sudo.", show_alert=True)
        return
    await query.answer()
    await context.bot.send_message(chat_id=query.from_user.id, text=build_sudo_commands_text())





# ---------------------------
# UPLOADER SYSTEM CORE
# ---------------------------
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json

UPLOADER_FILE = "uploader_users.json"
OWNER_ID = 8163432539  # Same owner ID

# ---------------------------
# JSON DB helpers
# ---------------------------
def load_uploaders():
    try:
        with open(UPLOADER_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_uploaders(uploader_list):
    with open(UPLOADER_FILE, "w") as f:
        json.dump(uploader_list, f)


# ---------------------------
# OWNER CHECK
# ---------------------------
def is_uploader_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


# ---------------------------
# ADD UPLOADER
# ---------------------------
async def add_uploader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_uploader_owner(update.effective_user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("Reply to a user to add as UPLOADER.")
        return

    user_id = reply.from_user.id
    username = reply.from_user.username or reply.from_user.first_name or str(user_id)
    uploader_list = load_uploaders()

    if user_id in uploader_list:
        await update.message.reply_text("⚠️ This user is already an UPLOADER.")
        return

    uploader_list.append(user_id)
    save_uploaders(uploader_list)

    await update.message.reply_text(
        f"✅ UPLOADER ADDED SUCCESSFULLY!\nUser @{username} has been promoted to UPLOADER."
    )

    # DM to new uploader with button
    try:
        keyboard = [[InlineKeyboardButton("𝑪𝑶𝑴𝑴𝑨𝑵𝑫𝑺", callback_data="UPLOADER_GUIDE")]]
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 CONGRATULATIONS @{username}!\n"
                f"You have been promoted to UPLOADER.\n\n"
                f"Tap the button below to view all UPLOADER commands."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except:
        pass


# ---------------------------
# REMOVE UPLOADER
# ---------------------------
async def remove_uploader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_uploader_owner(update.effective_user.id):
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("Reply to an UPLOADER user to remove.")
        return

    user_id = reply.from_user.id
    username = reply.from_user.username or reply.from_user.first_name or str(user_id)
    uploader_list = load_uploaders()

    if user_id not in uploader_list:
        await update.message.reply_text("⚠️ This user is not an UPLOADER.")
        return

    uploader_list.remove(user_id)
    save_uploaders(uploader_list)

    await update.message.reply_text(
        f"🗑️ UPLOADER REMOVED SUCCESSFULLY!\nUser @{username} has been removed from UPLOADER role."
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Your UPLOADER access has been revoked by the owner.",
        )
    except:
        pass


# ---------------------------
# UPLOADER LIST
# ---------------------------
async def uploader_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_uploader_owner(user_id) and not is_uploader(user_id):
        return

    uploader_list = load_uploaders()
    if not uploader_list:
        await update.message.reply_text("No UPLOADER users found.")
        return

    msg = "📤 UPLOADER LIST\n\n"
    for i, uid in enumerate(uploader_list, 1):
        try:
            user = await context.bot.get_chat(uid)
            name = user.first_name or "Hidden"
            username = f"@{user.username}" if user.username else ""
            msg += f"{i}. {name} {username} | ID: {uid}\n"
        except:
            msg += f"{i}. Unknown | ID: {uid}\n"

    await update.message.reply_text(msg)


# ---------------------------
# UPLOADER COMMANDS
# ---------------------------
UPLOADER_COMMANDS = [
    "/upload",
    "/auction <waifu_id> <starting_bid> [hours]",
    "/auction users",
    "/dgen <waifu_id> <quantity>",
    "/dupload <waifu_id>",
    "/give <waifu_id> <username|bot_user_id>",
    "/dtops",
    "/uploaderlist",
    "/uploadercommands",
]


UPLOADER_EXAMPLES = {
    "/upload": "Upload a waifu using an image and caption fields: Name, Rarity, Anime.",
    "/dgen <waifu_id> <quantity>": "Generate waifu codes. Example: /dgen 2947 5",
    "/dupload <waifu_id>": "Delete an uploaded waifu. Example: /dupload 38429",
    "/give <waifu_id> <username|bot_user_id>": "Grant a waifu to a user.",
    "/dtops": "View rarity-wise waifu upload statistics.",
    "/uploaderlist": "View the Uploader members list.",
    "/uploadercommands": "Open the Uploader command guide.",
}


def build_uploader_commands_text() -> str:
    text = "📤 UPLOADER COMMAND PANEL\n\n"
    for cmd in UPLOADER_COMMANDS:
        text += f"{cmd}\n{UPLOADER_EXAMPLES.get(cmd, '')}\n\n"
    return text


async def uploader_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uploader_list = load_uploaders()
    if not is_uploader_owner(user_id) and user_id not in uploader_list:
        return

    text = build_uploader_commands_text()

    if update.message.chat.type != "private":
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except:
            await update.message.reply_text(
                "Cannot send DM. Please start a chat with the bot first."
            )
    else:
        await update.message.reply_text(text)


# ---------------------------
# DM BUTTON CALLBACK
# ---------------------------
async def uploader_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_uploader_owner(query.from_user.id) and not is_uploader(query.from_user.id):
        await query.answer("This guide is only for Owner and Uploaders.", show_alert=True)
        return
    await query.answer()
    await context.bot.send_message(chat_id=query.from_user.id, text=build_uploader_commands_text())



# ===============================
# COMMAND: /BALANCE
# ===============================

import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
BALANCE_DB = f"{DATA_DIR}/balance_system.db"

# ---------- DATABASE ----------

def init_db():
    conn = sqlite3.connect(BALANCE_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id INTEGER PRIMARY KEY,
            cash INTEGER DEFAULT 0,
            diamonds INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_balance(uid):
    try:
        conn = sqlite3.connect(BALANCE_DB)
        cur = conn.cursor()
        cur.execute("SELECT cash, diamonds FROM user_balance WHERE user_id=?", (uid,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO user_balance VALUES (?,0,0)", (uid,))
            conn.commit()
            row = (0,0)
        conn.close()
        return row
    except Exception as e:
        print("Get Balance Error:", e)
        return 0,0

def update_balance(uid, cash_delta=0, diamond_delta=0):
    try:
        cash, dia = get_balance(uid)
        conn = sqlite3.connect(BALANCE_DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO user_balance VALUES (?,?,?)",
            (uid, cash+cash_delta, dia+diamond_delta)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Update Balance Error:", e)

# ---------- /BALANCE COMMAND ----------

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cash, diamonds = get_balance(update.effective_user.id)
        await update.message.reply_text(
            f"💳 Balance Info\n👤 {update.effective_user.first_name}\n💰 Cash: `{cash:,}`\n💎 Diamonds: `{diamonds:,}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        print("Balance Command Error:", e)
        await update.message.reply_text("❌ Failed to fetch balance.")
# ===============================
# COMMAND: /EXPLORE
# ===============================

import random
import time
from telegram import Update
from telegram.ext import ContextTypes
import os, json

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EXPLORE_CD_FILE = f"{DATA_DIR}/explore_cd.json"
EXPLORE_COOLDOWN = 60  # 1 min cooldown

LOW_LOCATIONS = ["Abandoned Village","Old Anime Town","Broken Dojo","Small Forest Camp","Deserted House","Underground alley","Ruined shrine"]
HIGH_LOCATIONS = ["Royal Palace","Hidden Dungeon","Ancient Dragon Cave","Sky Island","Legendary Battlefield","Forbidden capital","Celestial tower"]

# ---------- COOLDOWN FUNCTIONS ----------

def load_json(path, default=None):
    try:
        with open(path,"r") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path,"w") as f:
        json.dump(data,f,indent=2)

def get_explore_cooldown(uid):
    data = load_json(EXPLORE_CD_FILE,{})
    last = data.get(str(uid),0)
    remain = EXPLORE_COOLDOWN - int(time.time() - last)
    return max(0, remain)

def set_explore_cooldown(uid):
    data = load_json(EXPLORE_CD_FILE,{})
    data[str(uid)] = int(time.time())
    save_json(EXPLORE_CD_FILE,data)

# ---------- /EXPLORE COMMAND ----------

async def explore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        cd = get_explore_cooldown(user_id)
        if cd > 0:
            return await update.message.reply_text(f"⏳ Wait {cd}s to explore again.")

        roll = random.randint(1,100)
        if roll <= 85:
            cash = random.randint(2300,3500)
            location = random.choice(LOW_LOCATIONS)
            diamonds = 0
        elif roll <= 95:
            cash = random.randint(3500,4700)
            location = random.choice(HIGH_LOCATIONS)
            diamonds = random.randint(1,2)
        else:
            cash = random.randint(4750,6500)
            location = random.choice(HIGH_LOCATIONS)
            diamonds = random.randint(2,3)

        # Update balance safely
        update_balance(user_id, cash_delta=cash, diamond_delta=diamonds)
        set_explore_cooldown(user_id)

        if diamonds == 0:
            text = f"🗺️ Adventure Complete!\n{location}\n💸 Cash: `{cash:,}`"
        else:
            text = f"🔥 LEGENDARY EXPLORE!\n{location}\n💸 Cash: `{cash:,}`\n💎 Diamonds: `{diamonds:,}`"

        await update.message.reply_text(f"{text}\n✅ Check `/balance`", parse_mode="Markdown")
    except Exception as e:
        print("Explore Command Error:", e)
        await update.message.reply_text("❌ Explore failed.")
# ===============================
# COMMAND: /BONUS + /BONUSREFRESH
# ===============================

import json, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
OWNER_ID = 8163432539

DAILY_BASE = 70000
DAILY_DIAMONDS = 10
WEEKLY_BASE = 300000
WEEKLY_DIAMONDS = 30
DAILY_CD = 86400
WEEKLY_CD = 604800

# ---------- HELPERS ----------

def load_json(path, default=None):
    try:
        with open(path,"r") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path,"w") as f:
        json.dump(data,f,indent=2)

def ensure_user(users, uid):
    users.setdefault(uid,{})
    u = users[uid]
    u.setdefault("daily",0)
    u.setdefault("weekly",0)
    u.setdefault("streak",0)
    u.setdefault("highest_streak",0)
    u.setdefault("last_claim",0)
    return u

def human_time(sec):
    if sec <= 0: return "Ready"
    m,_ = divmod(sec,60)
    h,m = divmod(m,60)
    d,h = divmod(h,24)
    if d: return f"{d}d {h}h"
    return f"{h}h {m}m"

def streak_multiplier(streak):
    if streak >= 30: return 2.0
    if streak >= 14: return 1.0
    if streak >= 7:  return 0.5
    if streak >= 3:  return 0.2
    return 0.0

# ---------- KEYBOARDS ----------

def bonus_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Daily", callback_data="bonus_daily")],
        [InlineKeyboardButton("💸 Weekly", callback_data="bonus_weekly")],
        [
            InlineKeyboardButton("📊 Stats", callback_data="bonus_stats"),
            InlineKeyboardButton("❌ Close", callback_data="bonus_close")
        ]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="bonus_back")]
    ])

# ---------- /BONUS MENU ----------

async def render_bonus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message:
            user = update.message.from_user
            send = update.message.reply_text
        else:
            q = update.callback_query
            user = q.from_user
            send = q.edit_message_text

        users = load_json(USERS_FILE,{})
        udata = ensure_user(users, str(user.id))
        save_json(USERS_FILE, users)

        cash, dia = get_balance(user.id)

        text = (
            f"🎮 **Bonus System**\n\n"
            f"👤 {user.full_name}\n"
        )
        if user.username:
            text += f"💻 @{user.username}\n"

        text += (
            f"🆔 {user.id}\n\n"
            f"💰 Cash: {cash:,}\n"
            f"💎 Diamonds: {dia:,}\n"
            f"🔥 Current Streak: {udata['streak']} days\n"
            f"⭐ Highest Streak: {udata['highest_streak']} days"
        )

        await send(text, reply_markup=bonus_keyboard(), parse_mode="Markdown")
    except Exception as e:
        print("Render Bonus Menu Error:", e)
        if update.message:
            await update.message.reply_text("❌ Bonus menu failed.")
        else:
            await update.callback_query.edit_message_text("❌ Bonus menu failed.")

# ---------- /BONUS COMMAND ----------

async def bonus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_bonus_menu(update, context)

# ---------- CALLBACK ----------

async def bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        await q.answer()

        users = load_json(USERS_FILE,{})
        uid = str(q.from_user.id)
        user = ensure_user(users, uid)
        now = int(time.time())

        if q.data == "bonus_daily":
            remain = DAILY_CD - (now - user["daily"])
            if remain > 0:
                return await q.edit_message_text(f"⏳ Daily bonus in {human_time(remain)}", reply_markup=back_keyboard())

            if now - user["last_claim"] <= DAILY_CD:
                user["streak"] += 1
            else:
                user["streak"] = 1

            user["highest_streak"] = max(user["highest_streak"], user["streak"])
            multiplier = streak_multiplier(user["streak"])
            cash = int(DAILY_BASE * (1 + multiplier))

            update_balance(q.from_user.id, cash_delta=cash, diamond_delta=DAILY_DIAMONDS)
            user["daily"] = now
            user["last_claim"] = now
            save_json(USERS_FILE, users)

            return await q.edit_message_text(
                f"✅ **Daily Bonus Claimed**\n\n💰 +{cash:,}\n💎 +{DAILY_DIAMONDS}\n🔥 Streak: {user['streak']} days\n📈 Multiplier: x{1+multiplier}",
                parse_mode="Markdown", reply_markup=back_keyboard()
            )

        if q.data == "bonus_weekly":
            remain = WEEKLY_CD - (now - user["weekly"])
            if remain > 0:
                return await q.edit_message_text(f"⏳ Weekly bonus in {human_time(remain)}", reply_markup=back_keyboard())

            multiplier = streak_multiplier(user["streak"])
            cash = int(WEEKLY_BASE * (1 + multiplier))
            update_balance(q.from_user.id, cash_delta=cash, diamond_delta=WEEKLY_DIAMONDS)
            user["weekly"] = now
            save_json(USERS_FILE, users)

            return await q.edit_message_text(
                f"✅ **Weekly Bonus Claimed**\n\n💰 +{cash:,}\n💎 +{WEEKLY_DIAMONDS}\n📈 Multiplier: x{1+multiplier}",
                parse_mode="Markdown", reply_markup=back_keyboard()
            )

        if q.data == "bonus_stats":
            return await q.edit_message_text(
                "📊 **Streak Rewards**\n\n3 Days → +20%\n7 Days → +50%\n14 Days → +100%\n30 Days → +200%",
                parse_mode="Markdown", reply_markup=back_keyboard()
            )

        if q.data == "bonus_back":
            return await render_bonus_menu(update, context)

        if q.data == "bonus_close":
            await q.edit_message_text("❌ Bonus menu closed.")
    except Exception as e:
        print("Bonus Callback Error:", e)
        await update.callback_query.edit_message_text("❌ Bonus failed.")

# ---------- /BONUSREFRESH ----------

async def bonusrefresh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        if msg.from_user.id != OWNER_ID:
            return await msg.reply_text("❌ Only owner can use this.")
        if not msg.reply_to_message:
            return await msg.reply_text("❗ Reply to user & type /bonusrefresh")

        target = msg.reply_to_message.from_user
        users = load_json(USERS_FILE,{})
        u = ensure_user(users, str(target.id))
        u["daily"] = 0
        u["weekly"] = 0
        save_json(USERS_FILE, users)

        await msg.reply_text(f"✅ Bonus cooldown refreshed\n🔥 Streak safe", parse_mode="Markdown")
    except Exception as e:
        print("Bonus Refresh Error:", e)
        await msg.reply_text("❌ Bonus refresh failed.")

# =====================================================
# GEN / REDEEM / DGEN / DREDEEM SYSTEM (FULL)
# =====================================================

import json, os, random, string, time
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# ---------------- BASIC CONFIG ----------------

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

GEN_FILE = f"{DATA_DIR}/gen_codes.json"
DGEN_FILE = f"{DATA_DIR}/dgen_codes.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"
USERS_FILE = f"{DATA_DIR}/users.json"

PARSE_MODE = "Markdown"

OWNER_ID = 8163432539
SUDO_USERS = {8470895455}
UPLOADER_USERS = {8570944478, 8186521526}

# ---------------- JSON HELPERS ----------------

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- ROLE CHECKS ----------------

def is_owner(uid): return uid == OWNER_ID
def is_sudo(uid): return uid in SUDO_USERS
def is_uploader(uid): return uid in UPLOADER_USERS

def role(uid):
    if is_owner(uid): return "owner"
    if is_sudo(uid): return "sudo"
    if is_uploader(uid): return "uploader"
    return "user"

# ---------------- SETTINGS ----------------

def get_settings():
    return load_json(SETTINGS_FILE, { "redeem_sudo_allowed": False, "dredeem_sudo_allowed": False })

def save_settings(s): save_json(SETTINGS_FILE, s)

# ---------------- BALANCE ----------------

def add_balance(uid, amount):
    users = load_json(USERS_FILE, {})
    u = users.setdefault(str(uid), {"balance": 0, "collection": []})
    u["balance"] += amount
    save_json(USERS_FILE, users)

# ---------------- COLLECTION (HOOK) ----------------

def add_waifu_id_to_user_collection(uid, waifu_id):
    users = load_json(USERS_FILE, {})
    u = users.setdefault(str(uid), {"balance": 0, "collection": []})
    u["collection"].append(waifu_id)
    save_json(USERS_FILE, users)

# ---------------- CODE GEN ----------------

def make_code():
    return "GOKU-" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(5))

# =====================================================
# /GEN — CASH & DIAMOND CODE
# =====================================================

OWNER_ID = 8163432539
SUDO_USERS = {8470895455}
UPLOADER_USERS = {8570944478, 8186521526}

async def gen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    r = role(uid)  # owner, sudo, uploader, user

    if len(context.args) < 2:
        return await update.message.reply_text(
            "*Usage:*\n`/gen <amount> <quantity> [cash/dimond]`",
            parse_mode=PARSE_MODE
        )

    amount = int(context.args[0])
    qty = int(context.args[1])
    ctype = "cash"
    if len(context.args) == 3 and context.args[2].lower() == "dimond":
        ctype = "dimond"

    # --- permissions ---
    if ctype == "cash" and r not in ("owner", "sudo"):
        return await update.message.reply_text("❌ Only Owner & Sudo can generate cash code")
    if ctype == "dimond" and r != "owner":
        return await update.message.reply_text("❌ Only Owner can generate dimond code")

    code = make_code()

    if ctype == "cash":
        data = load_json(GEN_FILE, {})
        data[code] = {
            "amount": amount,
            "qty": qty,
            "used": [],
            "creator_role": r,
            "scope": "users",
            "type": "cash"
        }
        save_json(GEN_FILE, data)
        await update.message.reply_text(
            f"*NEW CASH CODE GENERATED*\n\n`{code}` 💰 Amount: `{amount:,}` 👥 Quantity: `{qty}`\n\nUse `/redeem {code}`",
            parse_mode=PARSE_MODE
        )
    else:  # dimond
        data = load_json(DGEN_FILE, {})
        data[code] = {
            "amount": amount,
            "qty": qty,
            "used": [],
            "creator_role": r,
            "scope": "users",
            "type": "dimond"
        }
        save_json(DGEN_FILE, data)
        await update.message.reply_text(
            f"*NEW DIMOND CODE GENERATED*\n\n`{code}` 💎 Dimonds: `{amount}` 👥 Quantity: `{qty}`\n\nUse `/redeem {code}`",
            parse_mode=PARSE_MODE
        )

# =====================================================
# /REDEEM — CASH & DIMOND APPLY
# =====================================================

async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ `/redeem <code>`", parse_mode=PARSE_MODE)

    uid = update.effective_user.id
    r = role(uid)
    code = context.args[0]

    data_cash = load_json(GEN_FILE, {})
    data_dimond = load_json(DGEN_FILE, {})

    # --- CASH CODE ---
    if code in data_cash:
        c = data_cash[code]

        if str(uid) in c["used"]:
            return await update.message.reply_text("❌ You already redeemed this code.")
        if c["qty"] <= 0:
            return await update.message.reply_text("❌ Code expired.")

        # Restriction: sudo can't redeem apna code
        if c["creator_role"] == "sudo" and uid in SUDO_USERS:
            return await update.message.reply_text("❌ You cannot redeem your own Sudo code.")

        c["qty"] -= 1
        c["used"].append(str(uid))
        update_balance(uid, cash_delta=c.get("amount",0))
        save_json(GEN_FILE, data_cash)
        await update.message.reply_text(
            f"✅ Cash code redeemed!\n💰 `{c['amount']:,}` added to your balance\nRemaining: `{c['qty']}`",
            parse_mode=PARSE_MODE
        )
        return

    # --- DIMOND CODE ---
    elif code in data_dimond:
        c = data_dimond[code]

        if str(uid) in c["used"]:
            return await update.message.reply_text("❌ You already redeemed this code.")
        if c["qty"] <= 0:
            return await update.message.reply_text("❌ Code expired.")

        # Dimond code: all users including sudo/uploader can redeem
        c["qty"] -= 1
        c["used"].append(str(uid))
        update_balance(uid, diamond_delta=c.get("amount",0))
        save_json(DGEN_FILE, data_dimond)
        await update.message.reply_text(
            f"✅ Dimond code redeemed!\n💎 `{c['amount']}` added to your balance\nRemaining: `{c['qty']}`",
            parse_mode=PARSE_MODE
        )
        return

    else:
        await update.message.reply_text("❌ Invalid code.")

# ---------------------- DGEN/DREDEEM LOGIC SAME ----------------------
# You can keep your existing dgen_cmd/dredeem_cmd from before, diamond codes handled with /gen diamond


# =====================================================
# /DGEN — WAIFU CODE
# =====================================================
async def dgen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    r = role(uid)

    if r not in ("owner", "sudo", "uploader"):
        return

    if len(context.args) < 2:
        return await update.message.reply_text(
            "*Usage:*\n`/dgen <waifu_id> <quantity>`",
            parse_mode=PARSE_MODE
        )

    waifu_id = context.args[0]
    qty = int(context.args[1])
    scope = "users"

    if len(context.args) == 3 and is_owner(uid):
        scope = context.args[2]

    code = make_code()
    data = load_json(DGEN_FILE, {})

    data[code] = {
        "waifu_id": waifu_id,
        "qty": qty,
        "used": [],
        "creator_role": r,
        "scope": scope
    }

    save_json(DGEN_FILE, data)

    await update.message.reply_text(
        f"""*WAIFU CODE GENERATED*

`{code}`
🧩 Waifu ID: `{waifu_id}`
👥 Quantity: `{qty}`

Use `/dredeem {code}`""",
        parse_mode=PARSE_MODE
    )

# =====================================================
# /DREDEEM — WAIFU
# =====================================================
async def dredeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("❌ `/dredeem <code>`", parse_mode=PARSE_MODE)

    uid = update.effective_user.id
    r = role(uid)
    code = context.args[0]

    data = load_json(DGEN_FILE, {})
    settings = get_settings()

    if code not in data:
        return await update.message.reply_text("❌ Invalid code.")

    c = data[code]

    if str(uid) in c["used"]:
        return await update.message.reply_text("❌ Already redeemed.")

    if c["creator_role"] in ("sudo", "uploader") and r in ("sudo", "uploader") and not settings["dredeem_sudo_allowed"]:
        return await update.message.reply_text("❌ This waifu code is for users only.")

    if c["qty"] <= 0:
        return await update.message.reply_text("❌ Code expired.")

    c["qty"] -= 1
    c["used"].append(str(uid))
    add_waifu_id_to_user_collection(uid, c["waifu_id"])
    save_json(DGEN_FILE, data)

    await update.message.reply_text(
        f"""🎉 *CONGRATULATIONS*

🧩 Waifu ID: `{c['waifu_id']}`
📦 Added to your /collection
Remaining Quantity: `{c['qty']}`""",
        parse_mode=PARSE_MODE
    )

# =====================================================
# OWNER TOGGLES
# =====================================================
async def redeem_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    settings = get_settings()
    if "on" in context.args:
        settings["redeem_sudo_allowed"] = True
        msg = "✅ Sudo & Uploader can redeem cash codes."
    else:
        settings["redeem_sudo_allowed"] = False
        msg = "❌ Sudo & Uploader cannot redeem cash codes."

    save_settings(settings)
    await update.message.reply_text(msg)

async def dredeem_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    settings = get_settings()
    if "on" in context.args:
        settings["dredeem_sudo_allowed"] = True
        msg = "✅ Sudo & Uploader can redeem waifu codes."
    else:
        settings["dredeem_sudo_allowed"] = False
        msg = "❌ Sudo & Uploader cannot redeem waifu codes."

    save_settings(settings)
    await update.message.reply_text(msg)









# ===============================
# PAY SYSTEM (CASH + DIAMONDS, SAFE + OWNER)
# ===============================

import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

OWNER_ID = 8163432539
PAY_COOLDOWN = 300

pay_cooldowns = {}
pending_payments = {}

def parse_amount(text):
    return int(text.replace(",", ""))

def format_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m} min {s} sec" if m else f"{s} sec"

def display_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name

# ---------------- /pay ----------------
async def pay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    payer = msg.from_user

    if not msg.reply_to_message:
        await msg.reply_text("❗ Reply to a user and use:\n/pay <amount>")
        return

    receiver = msg.reply_to_message.from_user

    if receiver.is_bot:
        await msg.reply_text("🤖 You can’t pay bots.")
        return

    if payer.id == receiver.id:
        await msg.reply_text("❌ You cannot pay yourself.")
        return

    if not context.args:
        await msg.reply_text("❗ Enter valid amount")
        return

    try:
        amount = parse_amount(context.args[0])
    except:
        await msg.reply_text("❗ Invalid amount (1000 or 1,000)")
        return

    if amount <= 0:
        await msg.reply_text("❗ Enter valid amount")
        return

    if payer.id != OWNER_ID:
        last = pay_cooldowns.get(payer.id, 0)
        remaining = int(PAY_COOLDOWN - (time.time() - last))
        if remaining > 0:
            await msg.reply_text(f"⏳ Wait {format_time(remaining)}")
            return

    ensure_user_balance(payer.id)
    ensure_user_balance(receiver.id)

    cash, diamonds = get_balance(payer.id)

    if cash < amount and diamonds < amount:
        await msg.reply_text("❌ Not enough Cash or Diamonds.")
        return

    tx_id = str(uuid.uuid4())

    pending_payments[tx_id] = {
        "payer": payer.id,
        "receiver": receiver.id,
        "amount": amount,
        "type": None,
        "done": False
    }

    buttons = []

    if cash >= amount:
        buttons.append(
            InlineKeyboardButton(
                "💵 Pay with Cash",
                callback_data=f"pay_type:cash:{tx_id}"
            )
        )

    if diamonds >= amount:
        buttons.append(
            InlineKeyboardButton(
                "💎 Pay with Diamonds",
                callback_data=f"pay_type:diamond:{tx_id}"
            )
        )

    keyboard = InlineKeyboardMarkup([[b] for b in buttons])

    await msg.reply_text(
        f"💸 Choose payment type for **{amount:,}**:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# ---------------- CALLBACK ----------------
async def pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("pay_type:"):
        _, pay_type, tx_id = q.data.split(":")
        data = pending_payments.get(tx_id)

        if not data or data["done"]:
            await q.edit_message_text("❌ Payment expired.")
            return

        if q.from_user.id != data["payer"]:
            await q.answer("❌ Not your payment.", show_alert=True)
            return

        data["type"] = pay_type
        receiver = await context.bot.get_chat(data["receiver"])

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm:{tx_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"pay_cancel:{tx_id}")
            ]
        ])

        await q.edit_message_text(
            f"💸 Pay **{data['amount']:,} "
            f"{'Cash' if pay_type == 'cash' else 'Diamonds'}** to {receiver.mention_html()}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    if not q.data.startswith("pay_"):
        return

    action, tx_id = q.data.split(":")
    data = pending_payments.get(tx_id)

    if not data or data["done"]:
        await q.edit_message_text("❌ Payment already completed.")
        return

    if q.from_user.id != data["payer"]:
        await q.answer("❌ You are not the sender.", show_alert=True)
        return

    data["done"] = True
    pending_payments.pop(tx_id, None)

    payer_id = data["payer"]
    receiver_id = data["receiver"]
    amount = data["amount"]
    pay_type = data["type"]

    cash, diamonds = get_balance(payer_id)

    if pay_type == "cash":
        if cash < amount:
            await q.edit_message_text("❌ Not enough Cash.")
            return
        update_balance(payer_id, cash_delta=-amount)
        update_balance(receiver_id, cash_delta=amount)
        currency = "Cash"
    else:
        if diamonds < amount:
            await q.edit_message_text("❌ Not enough Diamonds.")
            return
        update_balance(payer_id, diamond_delta=-amount)
        update_balance(receiver_id, diamond_delta=amount)
        currency = "Diamonds"

    if payer_id != OWNER_ID:
        pay_cooldowns[payer_id] = time.time()

    sender_name = display_name(q.from_user)

    # ---- DM RECEIVER ----
    try:
        await context.bot.send_message(
            receiver_id,
            f"💖 Yay!\n\n"
            f"You received **{amount:,} {currency}** 🎉\n"
            f"From: {sender_name}\n\n"
            f"✨ Balance updated!\n"
            f"Check with /balance"
        )
    except:
        pass

    await q.edit_message_text("✅ Payment successful!")

# ---------------- OWNER: /payrefresh ----------------
async def payrefresh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if msg.from_user.id != OWNER_ID:
        await msg.reply_text("❌ You are not the owner.")
        return

    if not msg.reply_to_message:
        await msg.reply_text("❗ Reply to a user to reset cooldown.")
        return

    user = msg.reply_to_message.from_user
    pay_cooldowns[user.id] = 0

    await msg.reply_text(
        f"✅ Pay cooldown reset for **{user.full_name}**",
        parse_mode="Markdown"
    )



#===============================
#🎲 /ROLL COMMAND – ODD / EVEN
#===============================
import sqlite3, os, time, asyncio
from telegram import Update
from telegram.ext import ContextTypes

# ===============================
# BALANCE SYSTEM (CORE)
# ===============================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
BALANCE_DB = f"{DATA_DIR}/balance_system.db"

def init_db():
    conn = sqlite3.connect(BALANCE_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_balance (
            user_id INTEGER PRIMARY KEY,
            cash INTEGER DEFAULT 0,
            diamonds INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_balance(user_id: int):
    conn = sqlite3.connect(BALANCE_DB)
    cur = conn.cursor()
    cur.execute("SELECT cash, diamonds FROM user_balance WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO user_balance VALUES (?,0,0)", (user_id,))
        conn.commit()
        row = (0, 0)
    conn.close()
    return row

def update_balance(user_id: int, cash_delta=0, diamond_delta=0):
    cash, diamonds = get_balance(user_id)
    conn = sqlite3.connect(BALANCE_DB)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO user_balance VALUES (?,?,?)",
                (user_id, cash + cash_delta, diamonds + diamond_delta))
    conn.commit()
    conn.close()

def ensure_user_balance(user_id: int):
    get_balance(user_id)

# ===============================
# ROLL COMMAND SYSTEM
# ===============================
ROLL_COOLDOWN = 60
roll_cooldowns = {}

def parse_amount(text: str) -> int:
    return int(text.replace(",", "").strip())

def format_cash(amount: int) -> str:
    return f"{amount:,}"

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # ---------- SHOW USAGE ----------
    if not context.args:
        return await msg.reply_text(
            "🎲 ROLL DICE BET\n\n"
            "Usage:\n"
            "`/roll <amount> <odd|even>`\n"
            "Examples:\n"
            "`/roll 25,000 odd/even`\n"
            "Minimum bet = 5% /balance",
            parse_mode="Markdown"
        )

    # ---------- COOLDOWN ----------
    last = roll_cooldowns.get(user_id, 0)
    remaining = int(ROLL_COOLDOWN - (time.time() - last))
    if remaining > 0:
        return await msg.reply_text(
            f"⏳ **COOLDOWN ACTIVE**\nPlease wait `{remaining}s` before rolling again.",
            parse_mode="Markdown"
        )

    # ---------- ARGUMENT CHECK ----------
    if len(context.args) != 2:
        return await msg.reply_text(
            "❗ **INVALID FORMAT**\nUse `/roll <amount> <odd|even>`\nExample: `/roll 10,000 odd`",
            parse_mode="Markdown"
        )

    # ---------- PARSE AMOUNT ----------
    try:
        bet_amount = parse_amount(context.args[0])
    except:
        return await msg.reply_text("❌ **INVALID AMOUNT**\nUse numbers only, e.g. `/roll 10,000 odd`", parse_mode="Markdown")

    if bet_amount <= 0:
        return await msg.reply_text("❌ Bet must be greater than 0.", parse_mode="Markdown")

    # ---------- ODD/EVEN ----------
    choice = context.args[1].lower()
    if choice not in ("odd", "even"):
        return await msg.reply_text("❗ **INVALID CHOICE**\nMust choose `odd` or `even`.", parse_mode="Markdown")

    # ---------- BALANCE ----------
    ensure_user_balance(user_id)
    cash, _ = get_balance(user_id)

    if cash <= 0:
        return await msg.reply_text("❌ You have no Cash to bet.", parse_mode="Markdown")

    # ---------- MIN 5% ----------
    min_bet = max(1, int(cash * 0.05))
    if bet_amount < min_bet:
        return await msg.reply_text(
            f"⚠️ **BET TOO LOW**\nYour Cash: {format_cash(cash)}\nMinimum 5%: {format_cash(min_bet)}\nTry: `/roll {format_cash(min_bet)} {choice}`",
            parse_mode="Markdown"
        )

    if bet_amount > cash:
        return await msg.reply_text(f"❌ Not enough Cash. You have: {format_cash(cash)}", parse_mode="Markdown")

    # ---------- CUT CASH FIRST ----------
    update_balance(user_id, cash_delta=-bet_amount)

    # ---------- SEND DICE ----------
    dice_msg = await context.bot.send_dice(chat_id=msg.chat_id, emoji="🎲")
    await asyncio.sleep(3)
    dice_value = dice_msg.dice.value
    dice_parity = "odd" if dice_value % 2 == 1 else "even"

    # ---------- APPLY COOLDOWN ----------
    roll_cooldowns[user_id] = time.time()

    # ---------- WIN / LOSS ----------
    if dice_parity == choice:
        win_amount = bet_amount * 2
        update_balance(user_id, cash_delta=win_amount)
        new_cash, _ = get_balance(user_id)
        return await msg.reply_text(
            f"🔥 YOU WON!\n🎲 Dice: {dice_value} ({dice_parity.upper()})\n🎯 Your Bet: {choice.upper()}\n💸 Won: {format_cash(win_amount)}\n💼 New Balance: {format_cash(new_cash)}",
            parse_mode="Markdown"
        )
    else:
        new_cash, _ = get_balance(user_id)
        return await msg.reply_text(
            f"💔 YOU LOST\n🎲 Dice: {dice_value} ({dice_parity.upper()})\n🎯 Your Bet: {choice.upper()}\n💸 Lost: {format_cash(bet_amount)}\n💼 Remaining Balance: {format_cash(new_cash)}",
            parse_mode="Markdown"
        )




# ===============================
# 🎯 /DARTS COMMAND (LIVE DART BET)
# ===============================
import time, asyncio, re
from telegram import Update
from telegram.ext import ContextTypes

DARTS_COOLDOWN = 60  # 1 minute
darts_cooldowns = {}

def format_cash(amount: int) -> str:
    return f"{amount:,}"

def parse_amount(text: str) -> int:
    clean = re.sub(r"[^\d]", "", text)
    return int(clean) if clean else 0

async def darts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # ---------- FORMAT CHECK ----------
    if not context.args:
        return await msg.reply_text(
            "🎯 DART BET USE \n"
            "Usage:\n"
            "`/darts <amount>`\n"
            "Example:\n"
            "`/darts 50,000`\n"
            "Minimum bet = 5% /balance",
            parse_mode="Markdown"
        )

    # ---------- COOLDOWN ----------
    last = darts_cooldowns.get(user_id, 0)
    remaining = int(DARTS_COOLDOWN - (time.time() - last))
    if remaining > 0:
        return await msg.reply_text(
            f"⏳ Cooldown Please wait `{remaining}s` before using /darts again.",
            parse_mode="Markdown"
        )

    # ---------- BALANCE ----------
    ensure_user_balance(user_id)
    cash, _ = get_balance(user_id)

    if cash <= 0:
        return await msg.reply_text(
            "❌ NO CASH AVAILABLE\n"
            "Your balance is empty.\n"
            "Check `/balance` first.",
            parse_mode="Markdown"
        )

    # ---------- PARSE AMOUNT ----------
    try:
        bet_amount = parse_amount(context.args[0])
    except:
        bet_amount = 0

    min_bet = max(1, int(cash * 0.05))

    if bet_amount <= 0:
        return await msg.reply_text(
            "❌ INVALID AMOUNT\n"
            f"💸 Your Cash: `{format_cash(cash)}`\n"
            f"⚠️ Minimum 5% Bet:\n"
            f"`/darts {format_cash(min_bet)}`",
            parse_mode="Markdown"
        )

    if bet_amount < min_bet:
        return await msg.reply_text(
            "⚠️ BET TOO LOW!\n"
            f"💼 Your Cash: `{format_cash(cash)}`\n"
            f"📉 Minimum Required (5%):\n"
            f"`/darts {format_cash(min_bet)}` \n\n",
            parse_mode="Markdown"
        )

    if bet_amount > cash:
        return await msg.reply_text(
            "❌ NOT ENOUGH CASH 💸\n"
            f"💼 Available Balance:\n"
            f"`{format_cash(cash)}`",
            parse_mode="Markdown"
        )

    # ---------- CUT BET FIRST ----------
    update_balance(user_id, cash_delta=-bet_amount)

    # ---------- SEND LIVE DART ----------
    dart_msg = await context.bot.send_dice(
        chat_id=msg.chat_id,
        emoji="🎯"
    )

    await asyncio.sleep(2)

    dart_value = dart_msg.dice.value  # REAL telegram result

    # ---------- APPLY COOLDOWN ----------
    darts_cooldowns[user_id] = time.time()

    # ---------- WIN / LOSS ----------
    if dart_value == 6:
        profit = bet_amount * 3
        total_return = bet_amount * 4
        update_balance(user_id, cash_delta=total_return)

        new_cash, _ = get_balance(user_id)

        return await msg.reply_text(
            "🎯 PERFECT HIT — BULLSEYE!\n"
            "🔥 **INSANE LUCK!**\n"
            f"💸 Bet: `{format_cash(bet_amount)}`\n"
            f"💰 Profit: `{format_cash(profit)}`\n"
            f"🏆 Total Won:\n"f"`{format_cash(total_return)}` Cash💸\n"
            "💼 Check /balance\n",
            parse_mode="Markdown"
        )

    else:
        new_cash, _ = get_balance(user_id)

        return await msg.reply_text(
            "🎯 DART MISSED\n"
            "💔 Better luck next time 🍀\n"
            f"💸 Lost:\n"f"`{format_cash(bet_amount)}` Cash💸\n"
            "💼 Remaining Balance\n"f"`{format_cash(new_cash)}`",
            parse_mode="Markdown"
        )




# ===============================
# ⚽ /GOAL COMMAND (LIVE FOOTBALL BET)
# ===============================
import time, asyncio, re
from telegram import Update
from telegram.ext import ContextTypes

GOAL_COOLDOWN = 60  # 1 minute
goal_cooldowns = {}

def format_cash(amount: int) -> str:
    return f"{amount:,}"

def parse_amount(text: str) -> int:
    clean = re.sub(r"[^\d]", "", text)
    return int(clean) if clean else 0

async def goal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # ---------- FORMAT CHECK ----------
    if not context.args:
        return await msg.reply_text(
            "⚽ GOAL BET USE\n"
            "Usage:\n"
            "`/goal <amount>`\n"
            "Example `/goal 100,000`\n"
            "Minimum bet = 5% /balance",
            parse_mode="Markdown"
        )

    # ---------- COOLDOWN ----------
    last = goal_cooldowns.get(user_id, 0)
    remaining = int(GOAL_COOLDOWN - (time.time() - last))
    if remaining > 0:
        return await msg.reply_text(
            f"⏳ Cooldown Please wait `{remaining}s` before using /goal again.",
            parse_mode="Markdown"
        )

    # ---------- BALANCE ----------
    ensure_user_balance(user_id)
    cash, _ = get_balance(user_id)

    if cash <= 0:
        return await msg.reply_text(
            "❌ NO CASH AVAILABLE\n"
            "Your balance is empty.\n"
            "Check `/balance` first.",
            parse_mode="Markdown"
        )

    # ---------- PARSE AMOUNT ----------
    bet_amount = parse_amount(context.args[0])
    min_bet = max(1, int(cash * 0.05))

    if bet_amount <= 0:
        return await msg.reply_text(
            "❌ INVALID AMOUNT\n"
            f"💼 Your Cash: `{format_cash(cash)}`\n"
            f"⚠️ Minimum 5% Bet:\n"
            f"`/goal {format_cash(min_bet)}`",
            parse_mode="Markdown"
        )

    if bet_amount < min_bet:
        return await msg.reply_text(
            "⚠️ BET TOO LOW!\n"
            f"💼 Your Cash: `{format_cash(cash)}`\n"
            f"📉 Minimum Required (5%):\n"
            f"`/goal {format_cash(min_bet)}`",
            parse_mode="Markdown"
        )

    if bet_amount > cash:
        return await msg.reply_text(
            "❌ NOT ENOUGH CASH 💸\n"
            "💼 Available Balance:f`{format_cash(cash)}`",
            parse_mode="Markdown"
        )

    # ---------- CUT BET ----------
    update_balance(user_id, cash_delta=-bet_amount)

    # ---------- SEND LIVE FOOTBALL ----------
    football_msg = await context.bot.send_dice(
        chat_id=msg.chat_id,
        emoji="⚽"
    )

    await asyncio.sleep(2)

    football_value = football_msg.dice.value  # REAL telegram result

    # ---------- APPLY COOLDOWN ----------
    goal_cooldowns[user_id] = time.time()

    # ---------- RESULT ----------
    # ⚽ GOAL = value >= 4 | MISS = < 4
    if football_value >= 4:
        total_win = int(bet_amount * 2.5)
        update_balance(user_id, cash_delta=total_win)

        new_cash, _ = get_balance(user_id)

        return await msg.reply_text(
            "🎉 GOAAAAAL!!! ⚽🔥\n"
            "Today Is Your Lucky Day. \n"
            f"💸 Bet: `{format_cash(bet_amount)}`\n"
            f"🏆 Won: `{format_cash(total_win)}` Cash💸\n"
            "💼 Check /balance",
            parse_mode="Markdown"
        )

    else:
        new_cash, _ = get_balance(user_id)

        return await msg.reply_text(
            "GOAL⚽ MISS! 💔\n"
            "Better luck next time 🍀\n"
            f"💸 Lost:`{format_cash(bet_amount)}` Cash💸\n"
            "💼 Remaining Balance\n"
            f"`{format_cash(new_cash)}`",
            parse_mode="Markdown"
        )



    # ===============================
    # 💣 MINES GAME (LIVE 5x5)
    # ===============================
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ACTIVE_MINES = {}

MAX_BET = 5000

    # -------------------------------
    # MULTIPLIER BASED ON MINES COUNT
    # -------------------------------
def get_multiplier(safe, mines):
        base = 1 + (mines * 0.15)
        return round(base + (safe * 0.12), 2)

    # -------------------------------
    # BUILD 5x5 BOARD
    # -------------------------------
def build_mines_board(game, reveal=False):
        board = []
        for r in range(5):
            row = []
            for c in range(5):
                idx = r * 5 + c
                if idx in game["opened"]:
                    row.append(InlineKeyboardButton("💎", callback_data="locked"))
                elif reveal and idx in game["mines"]:
                    row.append(InlineKeyboardButton("💣", callback_data="locked"))
                else:
                    row.append(InlineKeyboardButton("⬛", callback_data=f"mine_{idx}"))
            board.append(row)

        if game["safe"] >= 2 and not reveal:
            board.append([InlineKeyboardButton("💎 CashOut", callback_data="mines_cashout")])

        return InlineKeyboardMarkup(board)

    # ===============================
    # /MINES COMMAND
    # ===============================
async def mines_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        args = context.args

        if not args:
            await update.message.reply_text(
                "⚠️ INVALID FORMAT\n"
                "Usage:\n"
                "Default: `/mines 20`\n"
                "`/mines 50 3`\n\n"
                "Min Bet: 20💎 | Max Bet: 5000💎\n"
                "Min Mines: 3",
                parse_mode="Markdown"
            )
            return

        bet = int(args[0])
        mines_count = int(args[1]) if len(args) > 1 else 5

        if bet < 20 or bet > MAX_BET:
            await update.message.reply_text(
                f"❌ Bet must be between 20💎 and {MAX_BET}💎"
            )
            return

        if mines_count < 3 or mines_count >= 25:
            await update.message.reply_text(
                "❌ Minimum mines = 3"
            )
            return

        if user_id in ACTIVE_MINES:
            await update.message.reply_text(
                "⛔ You already have an active mines game!\nUse /endmines"
            )
            return

        ensure_user_balance(user_id)
        cash, diamonds = get_balance(user_id)

        if diamonds < bet:
            await update.message.reply_text(
                "❌ Not enough diamonds 💎"
            )
            return

        update_balance(user_id, diamond_delta=-bet)

        mine_tiles = set(random.sample(range(25), mines_count))

        ACTIVE_MINES[user_id] = {
            "bet": bet,
            "mines": mine_tiles,
            "opened": set(),
            "safe": 0,
            "multiplier": 1.0,
            "owner": user_id,
            "mines_count": mines_count,
            "ended": False
        }

        await update.message.reply_text(
            f"💣 MINES GAME STARTED 💣\n\n"
            f"💎 Bet: {bet}💎\n"
            f"💥 Mines: {mines_count}\n"
            f"📊 Opened: 0 / 25\n"
            f"📈 Multiplier: 1.00x\n"
            f"💰 Potential Win: {bet}💎\n\n"
            f"Good luck 😈",
            reply_markup=build_mines_board(ACTIVE_MINES[user_id])
        )

    # ===============================
    # CALLBACK HANDLER
    # ===============================
async def mines_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if user_id not in ACTIVE_MINES:
            return

        game = ACTIVE_MINES[user_id]

        if query.from_user.id != game["owner"]:
            await query.answer("👀 Spectator mode", show_alert=True)
            return

        if game["ended"]:
            return

        data = query.data

        # -------- CASHOUT --------
        if data == "mines_cashout":
            game["ended"] = True
            win = int(game["bet"] * game["multiplier"])
            update_balance(user_id, diamond_delta=win)

            await query.edit_message_text(
                f"🎉 GAME ENDED — CASHOUT 💎\n\n"
                f"💰 Bet: {game['bet']}💎\n"
                f"📈 Multiplier: {game['multiplier']}x\n"
                f"🏆 Win: {win}💎",
                reply_markup=build_mines_board(game, reveal=True)
            )
            del ACTIVE_MINES[user_id]
            return

        if not data.startswith("mine_"):
            return

        idx = int(data.split("_")[1])

        if idx in game["opened"]:
            return

        # -------- MINE HIT --------
        if idx in game["mines"]:
            game["ended"] = True
            await query.edit_message_text(
                f"💥 BOOM 🤡💣\n\n"
                f"💎 Bet Lost: {game['bet']}💎\n"
                f"😭 Better luck next time!",
                reply_markup=build_mines_board(game, reveal=True)
            )
            del ACTIVE_MINES[user_id]
            return

        # -------- SAFE TILE --------
        game["opened"].add(idx)
        game["safe"] += 1
        game["multiplier"] = get_multiplier(game["safe"], game["mines_count"])
        potential = int(game["bet"] * game["multiplier"])

        await query.edit_message_text(
            f"🎯 SAFE TILE 😎\n\n"
            f"📊 Opened: {game['safe']} / 25\n"
            f"📈 Multiplier: {game['multiplier']}x\n"
            f"💰 Potential Win: {potential}💎",
            reply_markup=build_mines_board(game)
        )

    # ===============================
    # /ENDMINES
    # ===============================
async def endmines(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if user_id not in ACTIVE_MINES:
            await update.message.reply_text("❌ No active mines game")
            return

        game = ACTIVE_MINES[user_id]
        update_balance(user_id, diamond_delta=game["bet"])

        await update.message.reply_text(
            f"🛑 MINES CANCELLED\n"
            f"💎 Returned: {game['bet']}💎"
        )
        del ACTIVE_MINES[user_id]



# ===============================
# 🌍 DTOPS — GLOBAL TOPS SYSTEM (FINAL UPDATED)
# ===============================

import sqlite3
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# ===============================
# DATABASE PATHS
# ===============================
BALANCE_DB = "data/balance_system.db"
USERS_FILE = "data/users.json"

# ===============================
# ROLES
# ===============================
OWNER_ID = 8163432539
SUDO_USERS = {8470895455}
UPLOADER_USERS = {8570944478, 8186521526}

def is_staff(uid):
    return uid == OWNER_ID or uid in SUDO_USERS or uid in UPLOADER_USERS

# ===============================
# AMOUNT FORMAT
# ===============================
def fmt_amount(n: int) -> str:
    if n >= 1_000_000_000_000:
        return f"${round(n/1_000_000_000_000,2)}T"
    if n >= 1_000_000_000:
        return f"${round(n/1_000_000_000,2)}B"
    if n >= 1_000_000:
        return f"${round(n/1_000_000,2)}M"
    if n >= 1_000:
        return f"${round(n/1_000,2)}K"
    return f"${n}"

# ===============================
# USER DISPLAY NAME
# ===============================
async def resolve_user_name(context, uid: int) -> str:
    try:
        user = await context.bot.get_chat(uid)
        if user.username:
            return f"@{user.username}"
        if user.full_name:
            return user.full_name
    except:
        pass
    return f"User {uid}"

# ===============================
# BALANCE TOPS
# ===============================
def top_cash(limit=10):
    con = sqlite3.connect(BALANCE_DB)
    cur = con.cursor()
    cur.execute("SELECT user_id, cash FROM user_balance ORDER BY cash DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return rows

def top_diamonds(limit=10):
    con = sqlite3.connect(BALANCE_DB)
    cur = con.cursor()
    cur.execute("SELECT user_id, diamonds FROM user_balance ORDER BY diamonds DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return rows

# ===============================
# WAIFU + RARITY SYSTEM
# ===============================
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

RARITY_EMOJIS = {
    "Starter":"⚪ Starter",
    "Rising":"🟢 Rising",
    "Shiny":"🟣 Shiny",
    "Ultimate":"🟡 Ultimate",
    "BeachArc":"🏖️ BeachArc",
    "ChibiArc":"👼 ChibiArc",
    "WinterArc":"❄ WinterArc",
    "LoveArc":"💞 LoveArc",
    "DarkArc":"🎃 DarkArc",
    "ChristmasArc":"🎄 ChristmasArc",
    "RoyalArc":"👑 RoyalArc",
    "NeonArc":"💫 NeonArc",
    "CelestialArc":"🪽 CelestialArc",
    "CrossArc":"🧬 CrossArc",
    "MangaArc":"✨ MangaArc",
    "LimitedArc":"🔮 LimitedArc",
    "SpecialArc":"🫧 SpecialArc",
    "DivineArc":"🥵 DivineArc",
    "CinemaArc":"🎥 CinemaArc"
}

RARITY_LIST = list(RARITY_EMOJIS.keys())

def waifu_top(limit=10):
    users = load_users()
    result = []
    for uid, data in users.items():
        count = len(data.get("collection", []))
        result.append((int(uid), count))
    return sorted(result, key=lambda x: x[1], reverse=True)[:limit]

def rarity_stats():
    users = load_users()
    stats = {r:0 for r in RARITY_LIST}

    for u in users.values():
        for w in u.get("collection", []):
            rarity = w.get("rarity")
            if rarity in stats:
                stats[rarity] += 1

    return stats

# ===============================
# MENU
# ===============================
def dtops_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎𝑫𝒊𝒎𝒐𝒏𝒅'𝒔", callback_data="dt_diamonds"),
            InlineKeyboardButton("🦋 𝐖𝒂𝒊𝒇𝒖 𝐓𝒐𝒑", callback_data="dt_waifu")
        ],
        [
            InlineKeyboardButton("💰 𝑩𝒂𝒍𝒂𝒏𝒄𝒆", callback_data="dt_balance")
        ],
        [
            InlineKeyboardButton("🥷 𝑻𝒐𝒑 𝑯𝒖𝒏𝒕𝒆𝒓'𝒔", callback_data="dt_hunters"),
            InlineKeyboardButton("💞𝑹𝒂𝒓𝒊𝒕𝒚", callback_data="dt_rarity")
        ]
    ])

# ===============================
# /DTOPS COMMAND
# ===============================
async def dtops_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Select a leaderboard category from below.",
        reply_markup=dtops_menu()
    )

# ===============================
# CALLBACK HANDLER
# ===============================
async def dtops_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "dt_back":
        return await q.edit_message_text(
            "Select a leaderboard category from below.",
            reply_markup=dtops_menu()
        )

    # 💎 DIAMONDS
    if q.data == "dt_diamonds":
        rows = top_diamonds()
        text = "💠𝑻𝑶𝑷 10 𝑼𝑺𝑬𝑹𝑺 𝑮𝑳𝑶𝑩𝑨𝑳𝑳𝒀 𝑩𝒀 𝑫𝑰𝑨𝑴𝑶𝑵𝑫𝑺💠\n\n"

        for i,(u,v) in enumerate(rows,1):
            name = await resolve_user_name(context, u)
            text += f"{i}. {name} — 💎 {fmt_amount(v)}\n"

    # 💰 BALANCE
    elif q.data == "dt_balance":
        rows = top_cash()
        text = "💰𝑻𝑶𝑷 10 𝑼𝑺𝑬𝑹𝑺 𝑩𝒀 𝑩𝑨𝑳𝑨𝑵𝑪𝑬💰\n\n"

        for i,(u,v) in enumerate(rows,1):
            name = await resolve_user_name(context, u)
            text += f"{i}. {name} — 💸 {fmt_amount(v)}\n"

    # 🦋 WAIFU
    elif q.data == "dt_waifu":
        rows = waifu_top()
        text = "🦋𝑻𝑶𝑷 10 𝑼𝑺𝑬𝑹𝑺 𝑩𝒀 𝑾𝑨𝑰𝑭𝑼🦋\n\n"

        for i,(u,c) in enumerate(rows,1):
            name = await resolve_user_name(context, u)
            text += f"{i}. {name} — 🦋 {c}\n"

    # 🥷 HUNTERS
    elif q.data == "dt_hunters":
        text = "🥷𝑻𝑶𝑷 10 𝑾𝑨𝑰𝑭𝑼 𝑯𝑼𝑵𝑻𝑬𝑹'𝑺🥷\n\nNo hunt system connected yet."

    # 💞 RARITY
    elif q.data == "dt_rarity":
        if not is_staff(uid):
            return

        stats = rarity_stats()
        text = "💞𝑾𝑨𝑰𝑭𝑼 𝑹𝑨𝑹𝑰𝑻𝒀 𝑶𝑽𝑬𝑹𝑽𝑰𝑬𝑾💞\n\n"

        for r in RARITY_LIST:
            emoji_name = RARITY_EMOJIS[r]
            text += f"{emoji_name} — {stats.get(r,0)}\n"

    else:
        return

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅ Back", callback_data="dt_back")]
        ])
    )

# ===============================
# REGISTER HANDLERS
# ===============================
def register_dtops(app):
    app.add_handler(CommandHandler("dtops", dtops_cmd))
    app.add_handler(CallbackQueryHandler(dtops_callback, pattern="^dt_"))



    


# =========================================
# 🌸 WAIFU COLLECTION CORE SYSTEM (FIXED)
# =========================================

import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultPhoto
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, InlineQueryHandler

# Ensure folder exists
os.makedirs("data", exist_ok=True)

COLLECTION_DB = "data/collection.db"


# =========================================
# DATABASE INIT (SAFE CALL EVERYWHERE)
# =========================================
def init_collection_db():

    con = sqlite3.connect(COLLECTION_DB)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS collections(
        user_id INTEGER,
        username TEXT,
        waifu_id TEXT,
        name TEXT,
        anime TEXT,
        rarity TEXT,
        image TEXT,
        favorite INTEGER DEFAULT 0
    )
    """)

    con.commit()
    con.close()


# =========================================
# ADD WAIFU
# =========================================
def add_waifu_to_collection(uid, username, wid, name, anime, rarity, image):

    init_collection_db()

    con = sqlite3.connect(COLLECTION_DB)
    cur = con.cursor()

    cur.execute("""
    INSERT INTO collections
    VALUES(?,?,?,?,?,?,?,0)
    """, (uid, username, wid, name, anime, rarity, image))

    con.commit()
    con.close()


# =========================================
# FETCH COLLECTION
# =========================================
def fetch_collection(uid):

    init_collection_db()

    con = sqlite3.connect(COLLECTION_DB)
    cur = con.cursor()

    cur.execute("""
    SELECT waifu_id,name,anime,rarity,image,favorite
    FROM collections
    WHERE user_id=?
    ORDER BY favorite DESC, anime ASC
    """, (uid,))

    data = cur.fetchall()
    con.close()

    # Codes created before a character catalogue is connected store only IDs
    # in users.json. Include those IDs in the viewer without inventing metadata.
    try:
        users = load_json(USERS_FILE, {})
        user_data = users.get(str(uid), {})
        known_ids = {str(row[0]) for row in data}
        for waifu_id in user_data.get("collection", []):
            wid = str(waifu_id)
            if wid not in known_ids:
                data.append((wid, f"Waifu {wid}", "Catalogue pending", "Unknown", "", 0))
    except (AttributeError, TypeError, ValueError):
        pass

    return data


# =========================================
# RARITY ICONS
# =========================================
RARITY_ICON = {
    "Starter":"⚪",
    "Rising":"🟢",
    "Shiny":"🟣",
    "Ultimate":"🟡",
    "WinterArc":"❄",
    "ChristmasArc":"🎄",
    "LimitedArc":"🔮"
}


# =========================================
# PAGINATION
# =========================================
def paginate(data, page, per_page=10):

    total_pages = max(1, (len(data)+per_page-1)//per_page)

    if page >= total_pages:
        page = total_pages - 1

    start = page * per_page
    end = start + per_page

    return data[start:end], total_pages


# =========================================
# TEXT BUILDER
# =========================================
def build_text(data, page, total_pages):

    if not data:
        return "📚 YOUR WAIFU COLLECTION\n\nNo waifus yet."

    text = f"📚 YOUR WAIFU COLLECTION\nPage {page+1}/{total_pages}\n\n"

    last_anime = None

    for wid,name,anime,rarity,image,fav in data:

        if anime != last_anime:
            text += f"🎬 {anime}\n"
            last_anime = anime

        icon = RARITY_ICON.get(rarity,"⚪")
        fav_icon = "❤️ " if fav else ""

        text += f"{fav_icon}🆔 {wid} | {icon} | {name}\n"

    return text


# =========================================
# /COLLECTION COMMAND
# =========================================
async def collection_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    page = 0

    data = fetch_collection(uid)

    # Favorite image first
    fav = next((x for x in data if x[5]==1), None)

    if fav and fav[4]:
        await update.message.reply_photo(fav[4])

    page_data, total_pages = paginate(data, page)

    text = build_text(page_data, page, total_pages)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Waifus", callback_data=f"cw_img_{uid}_{page}")],
        [
            InlineKeyboardButton("◀ Prev", callback_data=f"cw_prev_{uid}_{page}"),
            InlineKeyboardButton("Next ▶", callback_data=f"cw_next_{uid}_{page}")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="cw_close")]
    ])

    await update.message.reply_text(text, reply_markup=buttons)


# =========================================
# CALLBACK HANDLER
# =========================================
async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    if q.data == "cw_close":
        return await q.message.delete()

    _, action, uid, page = q.data.split("_")

    uid = int(uid)
    page = int(page)

    data = fetch_collection(uid)

    if action == "next":
        page += 1
    elif action == "prev":
        page = max(0, page-1)

    page_data, total_pages = paginate(data, page)

    text = build_text(page_data, page, total_pages)

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Waifus", callback_data=f"cw_img_{uid}_{page}")],
            [
                InlineKeyboardButton("◀ Prev", callback_data=f"cw_prev_{uid}_{page}"),
                InlineKeyboardButton("Next ▶", callback_data=f"cw_next_{uid}_{page}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="cw_close")]
        ])
    )


# =========================================
# IMAGE VIEW
# =========================================
async def collection_image_view(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    _,_,uid,page = q.data.split("_")

    uid = int(uid)
    page = int(page)

    data = fetch_collection(uid)
    page_data, total_pages = paginate(data, page)

    await q.message.reply_text(f"🖼️ YOUR WAIFUS | Page {page+1}/{total_pages}")

    for waifu in page_data:
        if waifu[4]:
            await q.message.reply_photo(waifu[4])


# =========================================
# INLINE MODE
# =========================================
async def inline_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.inline_query
    uid = query.from_user.id

    data = fetch_collection(uid)

    results = []

    for wid,name,anime,rarity,image,fav in data[:50]:
        if not image:
            continue
        results.append(
            InlineQueryResultPhoto(
                id=str(wid),
                photo_url=image,
                thumbnail_url=image,
                caption=f"{name} | {rarity} | {anime}"
            )
        )

    await query.answer(results, cache_time=1)


# =========================================
# REGISTER
# =========================================
def register_collection(app):

    init_collection_db()

    app.add_handler(CommandHandler("collection", collection_cmd))
    app.add_handler(CallbackQueryHandler(collection_callback, pattern="^cw_(next|prev)"))
    app.add_handler(CallbackQueryHandler(collection_image_view, pattern="^cw_img"))
    app.add_handler(InlineQueryHandler(inline_collection))


 

# ---------------------------
# APP START HANDLER BUTTONS
# ---------------------------
def main():
    ensure_files()


    app = Application.builder().token(BOT_TOKEN).build()


    # ===============================
    # HANDLER REGISTER
    # ===============================
    def register_bonus_handlers(app):
        app.add_handler(CommandHandler("bonus", bonus_cmd))
        app.add_handler(CallbackQueryHandler(bonus_callback, pattern="^bonus_"))
        app.add_handler(CommandHandler("bonusrefresh", bonusrefresh_cmd))
        app.add_handler(CommandHandler("balance", balance_cmd))
        app.add_handler(CommandHandler("explore", explore_cmd))


    # BONUS HANDLERS
    register_bonus_handlers(app)
    # ===============================
    # PAY HANDLERS (ADD ONCE)
    # ===============================
    
    app.add_handler(CommandHandler("pay", pay_cmd))
    app.add_handler(CallbackQueryHandler(pay_callback, pattern="^pay_"))
    app.add_handler(CommandHandler("payrefresh", payrefresh_cmd))
    app.add_handler(CommandHandler("roll", roll_cmd))
    app.add_handler(CommandHandler("darts", darts_cmd))
    app.add_handler(CommandHandler("goal", goal_cmd))
    app.add_handler(CommandHandler("mines", mines_cmd))
    app.add_handler(CommandHandler("endmines", endmines))
    app.add_handler(CallbackQueryHandler(mines_callback, pattern="^mine_|mines_cashout$"))
    app.add_handler(CommandHandler("dtops", dtops_cmd))
    app.add_handler(CallbackQueryHandler(dtops_callback, pattern="^dt_"))
    app.add_handler(CommandHandler("collection", collection_cmd))
    app.add_handler(CallbackQueryHandler(collection_callback, pattern="^cw_"))
    app.add_handler(CallbackQueryHandler(collection_image_view, pattern="^cw_img"))
    app.add_handler(InlineQueryHandler(inline_collection))



    # =====================================================
    # REGISTER
    # =====================================================
    def register_gen_system(app):
        app.add_handler(CommandHandler("gen", gen_cmd))
        app.add_handler(CommandHandler("redeem", redeem_cmd))
        app.add_handler(CommandHandler("dgen", dgen_cmd))
        app.add_handler(CommandHandler("dredeem", dredeem_cmd))
        app.add_handler(CommandHandler("redeem", redeem_toggle))
        app.add_handler(CommandHandler("dredeem", dredeem_toggle))

    register_gen_system(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("explore", explore_cmd))
    app.add_handler(CommandHandler("addsudo", add_sudo))
    app.add_handler(CommandHandler("rsudo", remove_sudo))
    app.add_handler(CommandHandler("sudolist", sudo_list_command))
    app.add_handler(CommandHandler("sudocommands", sudo_commands))
    app.add_handler(CallbackQueryHandler(sudo_guide_callback, pattern="SUDO_GUIDE"))
    app.add_handler(CommandHandler("adduploader", add_uploader))
    app.add_handler(CommandHandler("ruploader", remove_uploader))
    app.add_handler(CommandHandler("uploaderlist", uploader_list_command))
    app.add_handler(CommandHandler("uploadercommands", uploader_commands))
    app.add_handler(CallbackQueryHandler(uploader_guide_callback, pattern="UPLOADER_GUIDE"))




    print("WaifuX_Prime Bot Started with SUDO & UPLOADER system")
    app.run_polling()

if __name__ == "__main__":
    main()