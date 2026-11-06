"""WaifuX Prime Telegram bot entry point."""
from __future__ import annotations

import logging

from telegram.ext import Application

from waifux.config import Settings
from waifux.handlers import register_handlers


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    settings = Settings.from_env()
    app = Application.builder().token(settings.bot_token).build()
    register_handlers(app, settings.owner_id)
    logging.getLogger(__name__).info("WaifuX Prime is starting")
    app.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
