# Command inventory

This inventory reflects the commands registered by `waifux/handlers.py`. Registration means a handler exists; it does not guarantee that every Telegram/API edge case has been live-tested. See `docs/KNOWN_ISSUES.md`.

## Public commands

| Category | Commands |
|---|---|
| Core | `/start`, `/help` |
| Collection/profile | `/collection`, `/fav`, `/fave`, `/dmode`, `/setprofile`, `/profile` |
| Waifu gameplay | `/hunt`, `/waifu`, `/marriage`, `/propose` |
| Catalogue lookup | `/f`, `/find`, `/dfind` |
| Economy | `/balance`, `/explore`, `/bonus`, `/pay`, `/redeem`, `/dredeem` |
| Transfers | `/gift`, `/trade`, `/sell` |
| Marketplace/auction use | `/marketplace`, `/bid` |
| Games | `/roll`, `/darts`, `/goal`, `/mines`, `/endmines` |
| Group filters | `/filters`, `/filter`, `/delfilter`, `/delall` |
| Event claim | `/claim` |

## Staff permission matrix

The bot reads the single configured `OWNER_ID` from Replit Secrets and persistent role lists in `data/sudo_users.json` and `data/uploader_users.json`. No individual Sudo/Uploader IDs need to be stored as Replit Secrets.

| Role | Commands |
|---|---|
| Owner | Unrestricted access to every registered command, plus all Owner, Sudo and Uploader controls |
| Sudo | `/auction`, `/auction users`, `/gen`, `/dgen`, `/changetime`, `/dupload`, `/give`, `/dtops`, `/sudolist`, `/sudocommands` |
| Uploader | `/upload`, `/uploaderlist`, `/uploadercommands` |
| Owner only | `/addsudo`, `/rsudo`, `/adduploader`, `/ruploader`, `/bonusrefresh`, `/payrefresh`, `/marketspawn`, `/spawn`, `/redeemtoggle`, `/dredeemtoggle`, `/gclaim`, `/send`, `/stop`, `/run` |

Notes:
- The Owner can use every command even if not present in either staff JSON list.
- Sudo and Uploader role lists are stored automatically and persist across restarts when the Replit filesystem persists.
- Sudo can generate cash codes with `/gen`; diamond-code generation remains Owner-only in the command implementation.
- Unknown/unimplemented slash commands are silently ignored; they are not advertised as working commands.
- Unauthorized staff commands are silently ignored.
- The Help Center uses separate category buttons. The Staff Guide is shown only to recognized staff, and each role guide is checked again when opened.

## Upload syntax

Send a photo with a caption, or reply to a photo with `/upload`, using:
```text
Name: Character Name
Rarity: Shiny
Anime: Anime Name
Price: optional
ID: optional
Aliases: optional, comma-separated
```
Price, ID and Aliases are optional. IDs are four digits. The bot assigns an in-range default price when no price is supplied.

## Important behavior notes

- Group hunting requires 50 non-command group messages and respects the configured spawn interval.
- Group anti-spam restriction requires Telegram admin permission.
- The marketplace allows two purchases and two paid refreshes per user per Pakistan calendar day.
- Auctions are settled by the scheduled JobQueue task after their end time.
- Existing collection SQLite/JSON data is imported into the shared DB; balances remain in the existing `balance_system.db`.
- Each user receives a stable 11-digit public bot ID. Profile, collection and privileged-gift lookup accept this ID or a known username.
- Marketplace offers use the six configured rarities, 70/30 rarity-group selection and prefer 95% unseen / 5% previously offered waifus when fresh inventory exists.
