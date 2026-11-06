# WaifuX Prime

Modularized runtime for the supplied Telegram waifu-bot command source. Development is staged: the original 2,805-line implementation remains preserved under `legacy/`, while the entry point, configuration, and handler registration are separated into `main.py` and `waifux/`.

## Current status

- `main.py` is the sole application entry point.
- `waifux/config.py` reads `BOT_TOKEN` and `OWNER_ID` from environment variables / Replit Secrets.
- `waifux/handlers.py` registers the implemented commands once and uses specific callback patterns.
- `legacy/partial_commands.py` preserves the supplied feature implementations while business logic is extracted incrementally.
- The command inventory and known limitations are documented under `docs/`.

This branch is not yet declared production-ready. Some feature names shown in the old help text have no implementation in the supplied source; see `docs/COMMAND_INVENTORY.md` and `docs/KNOWN_ISSUES.md`.

## Setup

Python 3.11 is recommended.

1. Install dependencies: `pip install -r requirements.txt`.
2. Add `BOT_TOKEN` and numeric `OWNER_ID` to Replit Secrets (or environment variables).
3. Start the bot with `python main.py`.

Do not commit tokens, local databases, or user data. Back up the `data/` directory before deploying or migrating. Existing SQLite/JSON stores are intentionally not deleted by the integration work.

## Project layout

| Path | Responsibility |
|---|---|
| `main.py` | Application startup and polling |
| `waifux/config.py` | Validated environment configuration |
| `waifux/handlers.py` | Single command/callback registration point |
| `legacy/partial_commands.py` | Preserved supplied implementation, pending staged extraction |
| `docs/` | Command inventory and integration notes |
| `tests/` | Offline source-integrity checks |

## Development policy

New feature prompts should be implemented as isolated modules, connected to shared services/storage, registered once, and covered by tests before merging. Never fabricate missing command behavior from help text alone.
