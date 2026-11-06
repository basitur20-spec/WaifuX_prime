# WaifuX Prime

WaifuX Prime is a modular Telegram waifu-collection bot built from the supplied command source and the saved feature specification. The original source is preserved under `legacy/`; new gameplay, collection, trading, marketplace and admin flows are separated into modules.

## Runtime and setup

- Python 3.11
- `python-telegram-bot[job-queue]==20.7`
- SQLite persistence in `data/balance_system.db`

Install and run:

```bash
pip install -r requirements.txt
python main.py
```

Required environment variables / Replit Secrets:

| Secret | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram bot token from BotFather |
| `OWNER_ID` | Numeric Telegram user ID of the owner |

Optional:

| Variable | Purpose |
|---|---|
| `WAIFU_CHANNEL_ID` | Channel ID or @username for new-upload announcements |
| `WAIFUX_DATA_DIR` | Override the local data directory (default: `data`) |

Never commit tokens, local databases, or user data. Back up the complete `data/` directory before deploying. The bot reuses `data/balance_system.db` for balances and the new waifu tables. On first startup, it attempts a one-time import from `data/collection.db` and `data/users.json`; review the backup before deploying this migration.

## Main commands

| Feature | Commands |
|---|---|
| Start/help | `/start`, `/help` |
| Collection | `/collection [@username|user_id]`, `/fav [waifu_id]` / `/fave`, `/dmode`, `/setprofile`, `/profile [@username|user_id]` |
| Catalogue | `/upload`, `/dupload <waifu_id>`, `/f <waifu_id>`, `/find <waifu_id>`, `/dfind <name>` |
| Gameplay | `/hunt <name>` in groups, `/waifu`, `/marriage`, `/propose` |
| Collection transfer | `/gift <waifu_id>` by reply, `/trade <your_id> <their_id>` by reply |
| Economy | `/sell <waifu_id> [more_ids]`, `/sell diamonds <amount>`, plus the preserved economy/game commands |
| Marketplace | `/marketplace`, `/marketspawn <rarity> on/off`, `/auction <waifu_id> <starting_bid> [hours]`, `/bid <amount>`, `/auction users` |
| Admin | `/spawn <rarity> on/off`, `/changetime <2-120 minutes>`, `/give`, `/gclaim`, `/claim`, `/stop`, `/run`, `/send` |
| Group filters | `/filter <keyword> | <response>`, `/filters`, `/delfilter <keyword>`, `/delall` |

## Upload format

Reply to a photo with `/upload` and details, or use the command with a photo caption:

```text
Name: Character Name
Rarity: Shiny
Anime: Anime Name
Price: 40000
ID: 1234
Aliases: alias one, alias two
```

Name, rarity and anime are required. Price and ID may be omitted; the bot estimates price from Telegram photo resolution/file size within the rarity range and generates a free four-digit ID. Name/anime typos are corrected only when a close match exists in the current catalogue. Upload access is limited to Owner and Uploader roles. Set `WAIFU_CHANNEL_ID` if upload announcements should be posted to a channel.

## Architecture

| Path | Responsibility |
|---|---|
| `main.py` | Application startup and polling |
| `waifux/config.py` | Validated environment configuration |
| `waifux/handlers.py` | Single command/callback registration point |
| `waifux/storage.py` | Shared SQLite schema, atomic balance/collection operations and legacy migration |
| `waifux/waifu_handlers.py` | Uploads, spawning, collections, profiles, gifts, sales and character lookup |
| `waifux/marketplace.py` | Daily marketplace, bids and scheduled auction settlement |
| `waifux/social_handlers.py` | Bilateral trading and privileged gifting |
| `waifux/event_handlers.py` | One-time claims, chat filters, user tracking and owner broadcast |
| `legacy/` | Preserved original source and untouched backup |
| `docs/` | Command inventory and deployment caveats |
| `tests/` | Offline persistence, migration and source-integrity tests |

## Validation and known limitations

GitHub Actions runs Python compilation and pytest. Passing CI verifies syntax and the offline storage/migration tests; it does **not** replace a live Telegram test. Before production deployment, test the bot in a private group with disposable users and a backup database.

Upload correction is catalogue-based fuzzy matching (not general AI spell-check). Price uses a resolution/file-size quality heuristic (not visual AI analysis). Anti-spam muting requires the bot to have administrator permission to restrict members. Each user receives a stable 11-digit bot ID; Telegram IDs remain internal. Profile, collection and privileged-gift lookup accept the bot ID or a known username. Review `docs/KNOWN_ISSUES.md` before merging.
