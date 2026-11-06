# Known integration issues

These items must be resolved before calling the bot production-ready:

1. The supplied source defines several functions more than once. Python keeps the last definition, which can silently change behavior.
2. The original `main()` has duplicate registrations for `/balance`, `/explore`, `/redeem`, and `/dredeem`. The new entry point avoids duplicate registrations and assigns owner toggles to `/redeemtoggle` and `/dredeemtoggle`.
3. The source defines `add_waifu_to_collection` twice with incompatible signatures. The `/dredeem` path currently calls the two-argument form after the seven-argument SQLite function has replaced it. This requires a deliberate collection/data migration before that feature can be considered fixed.
4. Character commands referenced by help text (including `/hunt`, `/waifu`, `/fav`, `/marriage`, `/propose`, and catalog/upload operations) are not implemented in this supplied source file. They must be integrated from the user's actual code/prompts.
5. Economy, bonus, payment, and game flows need behavioral tests with a disposable database; syntax checks alone do not validate balance correctness or concurrency.
6. SQLite writes are synchronous inside async Telegram handlers. Move persistence calls behind a service/repository layer and consider an async DB strategy before high-load deployment.
7. Existing JSON and SQLite stores overlap in purpose. Preserve backups and define one source of truth before migrating user collections or balances.

Do not merge this branch into the production branch until the critical items above have been addressed or explicitly accepted.
