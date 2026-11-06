# Command inventory

This inventory reflects commands currently registered by `waifux/handlers.py`. A command being registered does not mean it has been tested against a live Telegram bot; see known issues.

| Group | Commands | Notes |
|---|---|---|
| Core | `/start`, `/help` | Legacy start menu; help currently lists the preserved help sections |
| Economy | `/balance`, `/explore`, `/bonus`, `/bonusrefresh`, `/pay`, `/payrefresh` | Preserved legacy economy handlers |
| Games | `/roll`, `/darts`, `/goal`, `/mines`, `/endmines` | Preserved legacy game handlers |
| Codes | `/gen`, `/redeem`, `/dgen`, `/dredeem`, `/redeemtoggle`, `/dredeemtoggle` | Redeem handlers and owner toggles are separate |
| Collection | `/collection`, `/fav`, `/dmode`, `/setprofile`, `/profile` | Paginated collection, read-only other-user view, favorites and profile settings |
| Catalogue | `/upload`, `/dupload`, `/f`, `/find`, `/dfind` | Catalogue CRUD/lookup and paginated ownership/search views |
| Gameplay | `/hunt`, `/waifu`, `/marriage`, `/propose` | Group spawns, daily claim and random proposal rewards |
| Transfer | `/gift`, `/trade` | Confirmed gifting and bilateral waifu exchange |
| Economy extras | `/sell` | Confirmed sales, rarity-specific payout and daily limit |
| Marketplace | `/marketplace`, `/marketspawn`, `/auction`, `/bid` | Daily offers, refresh limits, auction bidding and scheduled settlement |
| Group/admin | `/spawn`, `/changetime`, `/filter`, `/filters`, `/delfilter`, `/delall` | Rarity spawn switches, interval, group filters |
| Owner | `/give`, `/gclaim`, `/claim`, `/send`, `/stop`, `/run` | Privileged grants, one-time reward event, broadcast and maintenance controls |
| Leaderboard | `/dtops` | Legacy leaderboard implementation; verify each leaderboard mode in a live group |
| Roles | `/addsudo`, `/rsudo`, `/sudolist`, `/sudocommands`, `/adduploader`, `/ruploader`, `/uploaderlist`, `/uploadercommands` | Persistent role lists from legacy JSON files |

## Upload syntax

Use a photo with a caption or reply to a photo with `/upload` and the fields `Name:`, `Rarity:`, `Anime:`; `Price:`, `ID:` and `Aliases:` are optional. IDs are four digits. The bot assigns an in-range default price when none is supplied.

## Important behavior notes

- Group hunting requires 50 non-command group messages and respects the configured spawn interval.
- Group anti-spam restriction requires Telegram admin permission.
- The marketplace allows two purchases and two paid refreshes per user per Pakistan calendar day.
- Auctions are settled by the scheduled JobQueue task after their end time.
- Existing collection SQLite/JSON data is imported once into the shared DB; balances remain in the existing `balance_system.db`.

- Each user receives a stable 11-digit public bot ID. The profile, collection and privileged-gift lookup accept this ID or a known username.
- Marketplace offers are restricted to the six configured rarities, use 70/30 rarity-group selection and prefer 95% unseen / 5% previously offered waifus when fresh inventory exists.
