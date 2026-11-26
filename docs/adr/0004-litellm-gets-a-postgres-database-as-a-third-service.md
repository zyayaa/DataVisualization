---
id: 0004
title: LiteLLM gets a Postgres database as a third service
status: proposed      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
Done-when 6 requires an admin UI login. Brief assumption 3 allows a third service with a named volume if the login needs a database. Whether the pinned LiteLLM release accepts a UI login without a database could not be verified from the repository. Separately from login, what the UI shows (keys, usage, logs) is data LiteLLM keeps in a database.
## Decision
The stack includes a `db` service running Postgres, pinned to a major version, with its data in the named volume `litellm_pgdata`. It publishes no port. `litellm` receives `DATABASE_URL` pointing at it and waits for its health check. Models stay defined in the committed `litellm/config.yaml`, not in the database.
## Alternative rejected
Run LiteLLM with no database and add one only if the login fails. It is one service fewer, which this design would normally prefer. It lost because Done-when 6 would rest on behaviour nobody has confirmed, a failure would force the stack to be reshaped mid-build, and a UI with nothing behind it would be of little use even if the login passed.
## Consequences
- Three containers instead of two, one more secret (`POSTGRES_PASSWORD`) and one more pinned image.
- LiteLLM's records persist across `docker compose down`; `down -v` deletes them.
- LiteLLM writes usage records for each request into the volume. The implementer should note in the README what is stored.
- If the pinned release needs a further secret when a database is present, its name is added to `env.example`.
- If the implementer finds the login works without a database, the service stays: this record would have to be superseded to remove it.
