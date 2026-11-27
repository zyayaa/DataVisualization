---
id: 0004
title: LiteLLM gets a Postgres database as a third service
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
Done-when 6 requires an admin UI login. Brief assumption 3 allows a third service with a named volume if the login needs a database. The G2 fact sheet confirms the login variables `UI_USERNAME` and `UI_PASSWORD` (row 5), but does not say whether the login works without a database. Separately from login, what the UI shows (keys, usage, logs) is data LiteLLM keeps in a database.

The fact sheet adds three things. LiteLLM's official compose example requires a further secret, `LITELLM_SALT_KEY`, which cannot be rotated in place (row 6). Applying the schema on start-up is documented "from v1.109.0" and is unconfirmed for the pinned `v1.108.18` (row 7). The Postgres major and its data directory are not verified (row 8).
## Decision
The stack includes a `db` service running Postgres, pinned to a major version, with its data in the named volume `litellm_pgdata`. It publishes no port. `litellm` receives `DATABASE_URL` pointing at it and waits for its health check. Models stay defined in the committed `litellm/config.yaml`, not in the database.

`LITELLM_SALT_KEY` is a sixth secret. It is listed in `env.example`, passed to `litellm` by name, generated once and never changed.

The Postgres major and data directory are taken from LiteLLM's official compose example and the Postgres image's documentation, and recorded before the service is built. Whether the pinned release applies its schema on start-up is checked at the first `up`; if it does not, that is a block for the user, not a silent extra step or a silent change of pin.
## Alternative rejected
Run LiteLLM with no database and add one only if the login fails. It is one service and two secrets fewer, which this design would normally prefer. It lost because Done-when 6 would rest on behaviour the fact sheet does not confirm, a failure would force the stack to be reshaped mid-build, and a UI with nothing behind it would be of little use even if the login passed.
## Consequences
- Three containers instead of two, two more secrets (`POSTGRES_PASSWORD`, `LITELLM_SALT_KEY`) and one more pinned image.
- LiteLLM's records persist across `docker compose down`; `down -v` deletes them.
- Losing or changing `LITELLM_SALT_KEY` after the first start is not supported by LiteLLM. What exactly becomes unreadable is not on the fact sheet. The README must say the key is set once.
- LiteLLM writes usage records for each request into the volume. The implementer should note in the README what is stored.
- The first `up` of the proxy may stop the item if the pinned release does not apply its schema.
- If the implementer finds the login works without a database, the service stays: this record would have to be superseded to remove it.
