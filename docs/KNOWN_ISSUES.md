# Known issues and deployment checks

The modular feature handlers and storage layer have been added, and the current GitHub Actions run verifies Python compilation plus offline tests. This is not yet proof of live Telegram behavior.

## Before production

1. **Live Telegram verification is still required.** Test /start, inline callbacks, uploads, group spawn, anti-spam restrictions, daily claims, gifts, trades, sales, marketplace purchases and auction settlement with disposable users.
2. **Upload automation is intentionally limited.** The bot validates fields and assigns a random price within the rarity range when price is omitted. It does not currently perform AI spelling correction or image-quality analysis.
3. **Channel announcements are optional.** Set `WAIFU_CHANNEL_ID`; the bot account must be able to post in that channel.
4. **Group permissions matter.** Anti-spam mute needs administrator rights to restrict members. Spawn messages need permission to send photos.
5. **User identifiers are Telegram IDs.** The separate bot-generated 11-digit public ID layer from the broader prompt is not implemented; lookup by Telegram ID or known username is used.
6. **Legacy source remains preserved, not fully refactored.** Some economy/game commands still execute legacy functions with their original data structures and duplicate definitions. Do not assume every legacy code path has been made concurrency-safe.
7. **Migration is one-time and should be backed up.** The importer reads `data/collection.db` and `data/users.json` once. Legacy rows without catalogue metadata may receive conservative placeholder pricing. Verify migrated collections before deploying to a live database.
8. **Database is SQLite.** Synchronous SQLite calls run inside async handlers. This is suitable for initial testing/small groups but should be load-tested before high-volume deployment.
9. **No external character catalogue is bundled.** The bot needs uploaded characters (photo file IDs, names, anime and rarities) before hunt, daily waifu, marketplace or auction rewards can operate.
10. **Optional environment values:** `WAIFU_CHANNEL_ID` controls announcement posting; `WAIFUX_DATA_DIR` changes the data directory. Required secrets remain `BOT_TOKEN` and numeric `OWNER_ID`.

## Integrity safeguards

- Original source backup remains untouched under `legacy/`.
- Existing balance DB is reused rather than replaced.
- Collection/economy changes use SQLite transactions in the new storage layer.
- Gift/trade/sale/marketplace actions use confirmation or transaction checks.
- User tokens and local database files must not be committed.
