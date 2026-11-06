# WaifuX Prime

Telegram waifu bot project. The supplied partial command source has been preserved for structured integration.

## Current development status

- The original 2,805-line source is stored at `legacy/partial_commands.py` on the integration branch.
- It is a source archive, **not the production entry point**. It contains duplicate function definitions, repeated handler registrations, overlapping callback patterns, and multiple data stores.
- The active modular bot is being assembled in stages. Do not run the legacy file as a production bot until the integration and regression checks are complete.

## Setup

Python 3.11 is recommended. Install the dependencies from `requirements.txt` once the runtime scaffold is added. Configure `BOT_TOKEN` and `OWNER_ID` through Replit Secrets or environment variables. Never commit credentials.

## Data safety

Back up the `data/` directory before deploying or migrating data. Existing SQLite/JSON stores must be reconciled deliberately; do not delete or overwrite them during integration.

## Project structure

- `legacy/` — preserved original source for reference and feature extraction.
- `docs/` — command inventory, integration notes, and architecture decisions.
- `waifux/` — production modules to be added after database and handler boundaries are finalized.

## Development workflow

New feature prompts should be implemented as modules, integrated with the shared database/services, and registered once in the application entry point. Each change should pass syntax/import checks and targeted tests before being considered deployable.
