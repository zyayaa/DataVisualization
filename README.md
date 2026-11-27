# data-visualization-agent

LangChain/LangGraph project for data visualization (early scaffold). A Docker Compose stack runs three services: `litellm` (an LLM proxy), `db` (its Postgres database) and `sandbox` (a container for code an LLM generates).

## Set-up

1. Copy the example file: `cp env.example .env`
2. Fill in `.env`: every name in it needs a value. Use letters, digits, `-` and `_` only; `LITELLM_MASTER_KEY` must start with `sk-`.
3. Start the stack: `docker compose up -d`. The first run builds the sandbox image and can take minutes.

The proxy listens on `http://127.0.0.1:4000` (loopback only). The admin UI is at `http://127.0.0.1:4000/ui`; log in with `UI_USERNAME` and `UI_PASSWORD`. API callers send `Authorization: Bearer <LITELLM_MASTER_KEY>`.

`docker compose down` stops the stack. Two checkouts of the repository on one host share one stack, because the project name is fixed (`docs/adr/0002-fixed-compose-project-name-the-sandbox-is-found-by-labels.md`).

## The salt key

`LITELLM_SALT_KEY` is generated once and never changed. It cannot be rotated in place: LiteLLM encrypts stored credentials with it, so a changed key makes them unreadable.

## The database volume

The volume `litellm_pgdata` holds the Postgres database of the proxy (keys, settings). `docker compose down` keeps it; `docker compose down -v` deletes it.

## The sandbox

The sandbox has no network, no secrets and one read-write mount: `workspace/` at `/workspace`. It runs as the image's own user, `sandboxuser`, with no user remapping (`docs/adr/0006-the-sandbox-runs-as-the-images-user-with-no-user-remapping.md`). On Linux, writes to the workspace mount may fail when the owner of `workspace/` has another user id than `sandboxuser`; this is a known limitation, not fixed with `user:`. The host reaches the sandbox only through `docker exec`, finding it by its Compose labels (`docs/adr/0001-the-sandbox-has-no-network-and-is-controlled-through-docker-exec.md`).

`workspace/*.parquet` is stored with Git LFS; without `git-lfs` the file is a small pointer.

## Claude models

The proxy serves one alias, `haiku`, mapped in `litellm/config.yaml` to `anthropic/claude-haiku-5-5`. It calls Anthropic with `ANTHROPIC_API_KEY` from `.env`, a pay-as-you-go key from console.anthropic.com; a Claude subscription does not work here.

## Tests

- Static tests: `uv run --with pytest pytest`
- Stack tests (need Docker and `.env`; a person runs them): `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`
