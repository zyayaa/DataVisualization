# Design: Docker Compose stack with sandbox and LiteLLM proxy

Read for this design: `docs/epics/001-docker-compose-stack-with-sandbox-and-li/brief.md`, `docs/architecture.md`, `sandbox/Dockerfile` (staged), `.gitignore`, `.gitattributes`, `.sdlc.json`, `.claude/settings.json`, `main.py`, `pyproject.toml`. There are no accepted decision records to honour (`docs/adr/` does not exist).

Three findings from the repository shape the design:

1. `.gitignore` contains only `.idea/`. `.env` is **not** ignored today, although CLAUDE.md says it must never be committed. This epic is the first to put real secrets in `.env`, so it must add the ignore rule before anything else.
2. `.claude/settings.json` denies `Read(./.env)` and `Read(./.env.*)`. A committed example file named `.env.example` matches the second rule, so the agents that build and review this epic could not read it. The example file is therefore named `env.example` (ADR 0005).
3. Nothing about Anthropic's terms or LiteLLM's handling of subscription tokens could be verified: the repository contains nothing on either, and this design had no access to outside documentation. Both are treated as open gates (ADR 0003), not as facts.

## Components touched or added

| Component | Path | Change |
|---|---|---|
| Compose stack | `compose.yaml` (repo root) | **New.** Three services: `sandbox`, `litellm`, `db`. Top-level `name: data-visualization-agent`. |
| Sandbox image | `sandbox/Dockerfile` | **Committed unchanged** (brief assumption 8). Build context is `./sandbox`, never the repo root, so neither `.env` nor the 53 MB parquet enters a build context. |
| LiteLLM proxy config | `litellm/config.yaml` | **New.** Model aliases and upstream credential wiring. Mounted read-only into the `litellm` container. Holds no secret values, only `os.environ/<NAME>` references. |
| LiteLLM database | service `db`, named volume `litellm_pgdata` | **New.** Postgres, owned entirely by LiteLLM. No published port. |
| Example env file | `env.example` (repo root) | **New.** Secret names with placeholder values and one comment line each. |
| Ignore rules | `.gitignore` | **Changed.** Gains `.env` and `.env.*`. |
| Readme | `README.md` | **Changed.** Gains the steps: copy `env.example` to `.env`, fill it in, `docker compose up -d`. |
| `main.py`, `pyproject.toml`, `uv.lock` | | **Untouched.** No Python wiring (out of scope). |

Service shape (schema, not final text):

```yaml
name: data-visualization-agent

services:
  sandbox:
    build: ./sandbox
    network_mode: none            # no interface but loopback; no ports, no networks key
    init: true                    # PID 1 is `tail`; lets `compose down` stop it promptly and reaps exec'd children
    volumes:
      - ./workspace:/workspace    # read-write
    # no environment, no env_file, no docker socket

  litellm:
    image: <official LiteLLM proxy image, pinned to one release tag>
    command: ["--config", "/app/config.yaml"]
    ports:
      - "127.0.0.1:4000:4000"     # API and admin UI share this port
    volumes:
      - ./litellm/config.yaml:/app/config.yaml:ro
    environment:                  # explicit mapping, one line per variable
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY:?set LITELLM_MASTER_KEY in .env}
      CLAUDE_CODE_OAUTH_TOKEN: ${CLAUDE_CODE_OAUTH_TOKEN:?set CLAUDE_CODE_OAUTH_TOKEN in .env}
      UI_USERNAME: ${UI_USERNAME:?set UI_USERNAME in .env}
      UI_PASSWORD: ${UI_PASSWORD:?set UI_PASSWORD in .env}
      DATABASE_URL: postgresql://litellm:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}@db:5432/litellm
    depends_on:
      db: { condition: service_healthy }

  db:
    image: postgres:<pinned major>
    environment:
      POSTGRES_USER: litellm
      POSTGRES_DB: litellm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
    volumes:
      - litellm_pgdata:/var/lib/postgresql/data   # path must match the pinned major's data directory
    healthcheck: pg_isready
    # no ports

volumes:
  litellm_pgdata:
```

Rules the compose file must hold to:

- `sandbox` has `network_mode: none` and nothing else network-related. It shares no network with `litellm` or `db`.
- `sandbox` receives no environment variable from `.env` and mounts only `./workspace`. The repo root, `.env` and the Docker socket are never mounted into any container.
- The only published port in the stack is `127.0.0.1:4000`.
- The string `ANTHROPIC_API_KEY` appears in no committed file of the stack (`compose.yaml`, `litellm/config.yaml`, `env.example`).
- No CPU or memory limits on `sandbox` (brief assumption 7). No further hardening (capability drops, read-only root) is added in this epic; the brief does not ask for it.

## Interfaces

**Host agent to sandbox (contract for a later epic; nothing is wired now).**
- Transport: the Docker Engine API on the host (`exec`). Exec goes through the Docker daemon, not through the container's network, so it works with `network_mode: none`.
- Lookup: by Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. The container name is not part of the contract.
- Defaults inherited from the image: user `sandboxuser`, working directory `/workspace`.
- Files: `workspace/` on the host is `/workspace` in the container, read-write. This is the only way data moves in or out.

**Host to proxy.**
- `POST http://127.0.0.1:4000/v1/chat/completions` (OpenAI-compatible), header `Authorization: Bearer <LITELLM_MASTER_KEY>`, body `{"model": "<alias>", "messages": [...]}`.
- Aliases: `opus`, `sonnet`, `haiku`, mapping to Opus 5.5, Sonnet 5.5 and Haiku 5.5. The aliases carry no version, so callers do not change when the models do. The exact upstream model identifiers are taken from Anthropic's published model list at build time; this design does not guess them.
- Missing or wrong key: HTTP 401 (Done-when 5).
- The caller presents only the master key. The subscription token is held by the proxy and never sent by the caller. This rules out any set-up in which the client forwards its own Anthropic credential through the proxy.

**Admin UI.** `http://127.0.0.1:4000/ui`, login with `UI_USERNAME` / `UI_PASSWORD`.

**Secret names (`env.example`).**

| Name | Read by | Note |
|---|---|---|
| `LITELLM_MASTER_KEY` | `litellm` | Client-facing key. LiteLLM's convention is believed to be an `sk-` prefix; confirm against the pinned release. |
| `CLAUDE_CODE_OAUTH_TOKEN` | `litellm` | Subscription token the user generates themselves (brief assumption 6). The name in `.env` is this stack's own; the `environment:` mapping can rename it to whatever the proxy expects. |
| `UI_USERNAME`, `UI_PASSWORD` | `litellm` | Admin UI login. Names believed to be LiteLLM's; confirm against the pinned release. |
| `POSTGRES_PASSWORD` | `db`, and `litellm` inside `DATABASE_URL` | Letters, digits, `-` and `_` only, because it is placed in a URL and Compose interpolates `$`. |

`env.example` states that same character rule for every generated value. A missing variable makes `docker compose up` fail at once with the `:?` message, instead of starting a half-configured proxy.

**The subscription-token gate (ADR 0003).** Three checks, in this order. The first two come before any other work item is built.

- **G1, terms.** Read Anthropic's current terms for the user's plan and its current documentation on where a subscription token may be used. The user makes the call; the answer is recorded in the epic's `decisions.md` as a `block-answer` entry. No agent can give this answer on the user's behalf.
- **G2, capability.** Confirm from the pinned LiteLLM release's own documentation that it can hold a subscription token server-side and present it as the upstream Anthropic credential, with no API key.
- **G3, live.** One chat-completion through the proxy returns a Claude reply while no `ANTHROPIC_API_KEY` exists in `.env`, in the compose file or in the container's environment. This is Done-when 4.

If G1 says the use is forbidden, or G2/G3 show it works only by making the proxy pose as Anthropic's own client (its identity, system prompt or user agent), the epic **stops and reports back**. It does not switch to an API key and does not work around a block.

**Verification notes for the plan.**
- Done-when 1 to 3 need only Docker. The sandbox image has no `curl`; the outbound check runs through Python inside the container and should not depend on DNS alone (connect to an IP address).
- Done-when 2 creates a file in `workspace/`; the check must delete it afterwards so it is not left untracked in git.
- Done-when 4 to 6 need the user's real `.env`. Agents cannot read `.env` (deny rule), and `docker` is not in `.sdlc.json` `allowed_bash`. Whether these three are run by the user by hand, or `docker` is allowed for the build, is the user's decision, not this design's.

## Data model changes

None in the application. The `db` service holds LiteLLM's own schema, which LiteLLM creates and migrates; no code in this repository reads or writes it. Its data lives in the named volume `litellm_pgdata` and survives `docker compose down` (it is removed only with `down -v`). The implementer should confirm that the pinned image applies its schema on start-up without an extra step.

## New dependencies

- **Docker Engine with Compose v2** on the host (brief assumption 9).
- **LiteLLM proxy image**, pinned to one release tag, not a moving tag. The container holds the subscription token, so what runs in it must not change unannounced. The implementer picks the newest stable release that passes G2 and writes the tag in `compose.yaml`.
- **Postgres image**, pinned to a major version.
- No Python dependency is added. `pyproject.toml` and `uv.lock` do not change.

## Decisions

- The sandbox runs with `network_mode: none`; the host agent reaches it only through Docker Engine exec and the `workspace/` mount (ADR 0001)
- The Compose project name is fixed to `data-visualization-agent`, and the sandbox is found by Compose labels, not by container name (ADR 0002)
- The proxy holds the Claude subscription token server-side; a three-step gate (terms, capability, live) must pass, and a failure stops the epic with no API-key fallback and no workaround (ADR 0003)
- LiteLLM gets a Postgres database as a third service, `db`, with the named volume `litellm_pgdata` (ADR 0004)
- One root `.env` serves Compose and `python-dotenv`; the committed example is `env.example`; secrets reach containers by explicit `environment:` mapping; `.env` is added to `.gitignore` (ADR 0005)
- The sandbox runs as the image's `sandboxuser` with no user remapping; bind-mount write access on Linux hosts is a documented limitation (ADR 0006)

## Change to the architecture document

Apply to `docs/architecture.md` once the epic is built.

**Components table: add these rows.**

```
| Compose stack | `compose.yaml` | Implemented: services `sandbox`, `litellm`, `db` |
| Sandbox image | `sandbox/Dockerfile` | Implemented; started by the stack, nothing execs into it yet |
| LiteLLM proxy config | `litellm/config.yaml` | Implemented; no code calls the proxy yet |
| Example env file | `env.example` | Implemented (names only, no values) |
```

**Components: add a subsection after `### workspace/`.**

```
### Compose stack

`docker compose up -d` from the repository root starts three containers under the fixed project name `data-visualization-agent`.

- `sandbox`: built from `sandbox/Dockerfile` (Python 3.15-slim, pandas, seaborn, matplotlib, scipy, Excel readers, non-root `sandboxuser`). It idles on `tail -f /dev/null`. It has no network (`network_mode: none`), no secrets and one mount: `workspace/` at `/workspace`, read-write.
- `litellm`: the LiteLLM proxy. It listens on `127.0.0.1:4000` only, serving an OpenAI-compatible API and the admin UI at `/ui`. It exposes the aliases `opus`, `sonnet` and `haiku`, and calls Anthropic with the user's Claude subscription token. No Anthropic API key is configured anywhere.
- `db`: Postgres for LiteLLM's own records, with no published port. Its data is in the named volume `litellm_pgdata`.

The agent (`main.py`) is not a container. It runs on the host.
```

**Boundaries: replace the whole section with this.**

```
`main.py` still calls nothing. The stack sets these boundaries for the code that will:

- The host may call the proxy at `http://127.0.0.1:4000` with the master key. The proxy is not reachable from the LAN.
- The host may control `sandbox` through the Docker Engine API (exec). The container is found by the Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`.
- `sandbox` may call nothing: not the internet, not the proxy, not the database, not the host. Data enters and leaves it only through `workspace/`.
- Only `litellm` talks to Anthropic and to `db`.
- No container mounts the repository root, `.env` or the Docker socket.
```

**Data model: replace "None. There is no schema, database, state object or persisted output." with this.**

```
The application has no schema, state object or persisted output. The stack's Postgres database belongs to LiteLLM, which creates and migrates its schema; no code in this repository reads or writes it.
```

**Dependencies: add after the runtime line.**

```
The stack needs Docker Engine with Compose v2, the LiteLLM proxy image and the Postgres image, each pinned in `compose.yaml`.
```

**Dependencies: replace the `docker` intent bullet with this.**

```
- `docker`: controlling the `sandbox` container from the host (exec). The container exists; no code uses the library yet.
```

**Dependencies, gaps: replace the "No LLM provider integration" bullet with these two.**

```
- A proxy that reaches Claude exists, but no client library is installed to call it (no `langchain-openai`, `langchain-anthropic` or similar).
- The sandbox image installs `pandas` but no parquet engine (`pyarrow` or `fastparquet`), so code run in the sandbox cannot read the dataset yet.
```

**Configuration and secrets: replace the section body with this.**

```
- `.env` at the repository root is read by Docker Compose (variable substitution) and by `load_dotenv()` in `main.py`. It is git-ignored.
- `env.example` lists the names: `LITELLM_MASTER_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`. It is not named `.env.example` because the project's permission rules deny reading `.env.*`.
- Each container receives only the variables it is given by name in `compose.yaml`. `sandbox` receives none.
- The subscription token is generated by the user and expires; the stack does not refresh it.
- No Python code reads any of these variables yet.
```

**Decision records: replace "None. `docs/adr/` does not exist yet." with the list of ADR 0001 to 0006 by title.**
