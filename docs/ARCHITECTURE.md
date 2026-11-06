# Architecture and integration plan

The supplied command source is preserved under `legacy/` and is not imported by the runtime. Production code is being extracted into `waifux/` in feature-sized modules.

## Boundaries

- `waifux/config.py`: validated environment settings and role configuration.
- `waifux/db/`: SQLite connections, schema, transactions, and compatibility/migration code.
- `waifux/services/`: reusable business rules (economy, codes, collection, cooldowns).
- `waifux/handlers/`: Telegram command and callback adapters only.
- `main.py`: build the PTB application and register each handler exactly once.

## Integration order

1. Configuration, logging, and database transaction layer.
2. Balance/economy primitives and migration strategy for the existing `balance_system.db`, `collection.db`, and JSON stores.
3. Staff roles and command authorization.
4. Existing supplied commands, one feature group at a time.
5. Character catalog, spawn/hunt/claim, favorites, social, market, and other prompt-only features.
6. Regression tests and deployment smoke checks.

## Non-negotiable invariants

- A user cannot spend more cash/diamonds than their balance.
- Multi-row balance and collection changes execute in a single database transaction.
- A callback must verify the acting user and operation owner.
- Every command and callback pattern is registered once, with specific patterns before broad routers.
- Cooldowns and pending operations that affect currency are persisted, not held only in process memory.
- Existing user data is backed up and migrated explicitly; no silent reset or destructive schema replacement.
