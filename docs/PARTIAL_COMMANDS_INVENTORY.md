# Partial command source — integration inventory

Source: `legacy/partial_commands.py` (2,805 lines; preserved unchanged from the supplied file).

## Implementations present in the supplied source

| Area | Commands / callbacks | Notes |
|---|---|---|
| Entry and help | `/start`; callback help pages | Start/help UI exists; help is callback-driven. |
| Staff roles | `/addsudo`, `/rsudo`, `/sudolist`, `/sudocommands`, `/adduploader`, `/ruploader`, `/uploaderlist`, `/uploadercommands` | JSON-backed role lists; currently duplicated role configuration. |
| Balance and exploration | `/balance`, `/explore` | SQLite balance DB plus JSON cooldown. |
| Bonuses | `/bonus`, `/bonusrefresh` | Daily/weekly rewards and streak data in JSON. |
| Codes | `/gen`, `/redeem`, `/dgen`, `/dredeem` | Cash/diamond and waifu code flows; owner toggles are incorrectly registered under the same command names as redeem. |
| Transfers | `/pay`, `/payrefresh` | Pending payment and cooldown state currently kept in process memory. |
| Games | `/roll`, `/darts`, `/goal`, `/mines`, `/endmines` | Game logic and callback flows exist; require balance atomicity and restart-safety review. |
| Leaderboards | `/dtops` | Balance, diamonds, collection count and rarity; hunter leaderboard explicitly has no connected hunt data. |
| Collection | `/collection`, inline collection query | Separate SQLite collection DB; favorite-management flow is not implemented in this source. |

## Features mentioned in the full bot prompt but not implemented by this partial file

The larger project prompt describes additional character spawning/hunting, daily waifu claims, favorite selection, marriage/proposals, upload/catalog management, marketplace/auction, selling, gifting/trading, profiles, filters, and other admin tools. These must be implemented from their prompt specifications; they are not assumed to exist merely because they appear in the old README/help text.

## Integration blockers to resolve

1. Duplicate definitions: `load_users`, `init_db`, `get_balance`, `update_balance`, `load_json`, `save_json`, `add_waifu_to_collection`, `parse_amount`, and `format_cash`.
2. Duplicate command registrations: `/balance`, `/explore`, `/redeem`, `/dredeem`, `/dtops`, and `/collection`.
3. `/redeem` and `/dredeem` are also used for owner toggles, making the toggle handlers unreachable when registered after the primary handlers.
4. Collection callbacks use overlapping `^cw_` and `^cw_img` patterns; the broad route can consume image callbacks.
5. The collection code defines a second `add_waifu_to_collection` with a different signature from the code-redemption helper.
6. Payment/game state is held in process memory, so pending operations and cooldowns disappear on restart. Balance transfers and rewards need transactional database operations.
7. Hardcoded owner/sudo/uploader IDs must be moved to environment configuration or managed role storage. No secrets or credentials should be committed.
8. The source uses separate JSON and SQLite stores with inconsistent collection formats. A compatibility layer and explicit migration plan are required before consolidating them.

## Integration policy

Preserve the legacy source as a reference. Extract each feature into a focused module, centralize configuration and persistence, register every command/callback exactly once, and add tests for permissions, cooldowns, callback ownership, and balance/collection consistency. Do not silently discard unfinished features.
