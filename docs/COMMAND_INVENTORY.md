# Command inventory — supplied source

This inventory describes commands that have implementations in `legacy/partial_commands.py` and are registered by the modular entry point. It does not claim features that were only mentioned in help text or earlier planning.

| Group | Registered commands | Notes |
|---|---|---|
| Core | `/start`, `/help` | Start menu and help callbacks |
| Economy | `/balance`, `/explore`, `/bonus`, `/bonusrefresh`, `/pay`, `/payrefresh` | SQLite balance plus JSON cooldown/bonus data |
| Games | `/roll`, `/darts`, `/goal`, `/mines`, `/endmines` | Game handlers preserved from supplied source |
| Codes | `/gen`, `/redeem`, `/dgen`, `/dredeem`, `/redeemtoggle`, `/dredeemtoggle` | Toggle commands separated from redeem commands to remove duplicate registrations |
| Collection | `/collection` | SQLite collection viewer and inline query support |
| Leaderboard | `/dtops` | Cash, diamonds, waifu and rarity views; hunter leaderboard is placeholder text in source |
| Roles | `/addsudo`, `/rsudo`, `/sudolist`, `/sudocommands`, `/adduploader`, `/ruploader`, `/uploaderlist`, `/uploadercommands` | Owner ID from environment; SUDO/uploader lists loaded from JSON files |

## Not implemented in the supplied file

The following appeared in help text or prior project plans but have no corresponding working handler in this source snapshot: `/hunt`, `/waifu`, `/fav`, `/marriage`, `/propose`, `/marketplace`, `/market`, `/buy`, `/gift`, `/trade`, `/profile`, `/upload`, and character spawning/catalogue management. These must be added from their actual feature prompts/code rather than fabricated.

## Integration notes

- `main.py` is the only polling entry point.
- `waifux/config.py` validates `BOT_TOKEN` and `OWNER_ID` environment variables.
- `waifux/handlers.py` registers each command once.
- Callback patterns are specific; collection image callbacks are registered before the collection paging/close route.
- The original source remains archived so feature behavior can be compared during later extraction.
