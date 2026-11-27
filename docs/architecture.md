# Architecture

Status: early scaffold. This document describes the repository as it is today. Anything labelled **Intent** is stated or implied by the project metadata but has no code behind it.

## Purpose

- **Intent** (from `pyproject.toml`): "LangChain and LangGraph project for data visualization". The project name is `data-visualization-agent`.
- **Implemented:** a single entry point that prints `Hello World`. No agent, graph, tool, chart or data-loading code exists.

## Components

| Component | Path | State |
|---|---|---|
| Entry point | `src/main.py` | Implemented (placeholder) |
| Data workspace | `workspace/` | One dataset committed; nothing reads it |
| Project metadata | `pyproject.toml`, `uv.lock` | Implemented |
| Compose stack | `compose.yaml` | Implemented: services `sandbox`, `litellm`, `db` |
| Sandbox image | `sandbox/Dockerfile` | Implemented; started by the stack, nothing execs into it yet |
| LiteLLM proxy config | `litellm/config.yaml` | Implemented with no model (`model_list: []`); no code calls the proxy yet |
| Example env file | `env.example` | Implemented (names only, no values) |
| Workflow tooling | `.sdlc.json`, `.claude/settings.json`, `.github/ISSUE_TEMPLATE/sdlc-inbox.yml`, `docs/epics/README.md` | Development process only, not part of the runtime |

### `src/main.py`

The whole application, 8 lines:

- Defines the module constant `WORKSPACE_PATH = "./workspace"`. It is not used anywhere. The path is relative, so it resolves against the current working directory, not the file's location.
- Calls `load_dotenv()` at import time, loading a `.env` file into the environment if one exists. No environment variable is read afterwards.
- Under `if __name__ == "__main__":` prints `Hello World`.

There is no package, no other module, and no test.

### `workspace/`

- `workspace/consumo_horario_mobilidade_eletrica_01_a_10.parquet`, about 53 MB, stored with Git LFS (`.gitattributes` tracks `*.parquet`).
- By its file name it holds hourly electric-mobility (EV charging) consumption. Its schema, time range and the meaning of `01_a_10` are not documented in the repository and no code inspects them.
- **Intent:** `WORKSPACE_PATH` suggests this folder is where the system will read data from (and possibly write to). That is not implemented.

### Compose stack

`docker compose up -d` from the repository root starts three containers under the fixed project name `data-visualization-agent`.

- `sandbox`: built from `sandbox/Dockerfile` (Python 3.15-slim, pandas, seaborn, matplotlib, scipy, Excel readers, non-root `sandboxuser`). It idles on `tail -f /dev/null`, with Docker's init process as PID 1 (`init: true`). It has no network (`network_mode: none`), no secrets and one mount: `workspace/` at `/workspace`, read-write.
- `litellm`: the LiteLLM proxy, pinned to the release tag `v1.108.18`. It listens on `127.0.0.1:4000` only, serving an OpenAI-compatible API, the admin UI at `/ui` and an unauthenticated readiness check at `/health/readiness`. The recorded verdict of the capability probe (ADR 0007) is "No Claude": the one probe returned HTTP 429 and the user chose not to configure Claude. So the proxy has no Claude model (`model_list: []`) and holds no subscription token. Configuring Claude later needs a new verdict record. No Anthropic API key is configured anywhere.
- `db`: Postgres (`postgres:16`) for LiteLLM's own records, with no published port. Its data is in the named volume `litellm_pgdata`. `litellm` starts only once `db` reports healthy.

The agent (`src/main.py`) is not a container. It runs on the host.

## Boundaries

`src/main.py` still calls nothing. The stack sets these boundaries for the code that will:

- The host may call the proxy at `http://127.0.0.1:4000` with the master key. The proxy is not reachable from the LAN.
- The host caller never sends an Anthropic credential to the proxy. The proxy forwards no client headers to Anthropic.
- The host may control `sandbox` through the Docker Engine API (exec). The container is found by the Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`.
- `sandbox` may call nothing: not the internet, not the proxy, not the database, not the host. Data enters and leaves it only through `workspace/`.
- Only `litellm` talks to Anthropic and to `db`.
- The proxy never presents Claude Code's identity to Anthropic: no Claude Code system prompt, user agent, client header or identity header (ADR 0003).
- No container mounts the repository root, `.env` or the Docker socket.

## Data model

The application has no schema, state object or persisted output. The stack's Postgres database belongs to LiteLLM, which creates and migrates its schema; no code in this repository reads or writes it. The only data is the parquet file above, which is untouched by code.

## Dependencies

Runtime: Python `>=3.15`, managed with `uv` (`uv sync` to set up, `uv run python src/main.py` to run).

The stack needs Docker Engine with Compose v2, the LiteLLM proxy image (`ghcr.io/berriai/litellm`, pinned to `v1.108.18`) and the Postgres image (`postgres:16`, a major-version tag), both set in `compose.yaml`. Changing the LiteLLM tag means running the capability probe of ADR 0007 again first.

| Declared dependency | Locked version | Used by code today |
|---|---|---|
| `python-dotenv` | 1.2.4 | Yes (`load_dotenv()`) |
| `langchain` | 1.5.2 | No |
| `langchain-core` | 1.8.4 | No |
| `langgraph` | 1.2.24 | No |
| `docker` | 7.2.0 | No |

**Intent** implied by the unused dependencies, with no code behind any of it:

- `langchain` / `langgraph`: an LLM agent built as a graph.
- `docker`: controlling the `sandbox` container from the host (exec). The container exists; no code uses the library yet.

Gaps between the stated intent and what is installed:

- No library that can read parquet (no `pandas`, `pyarrow`, `polars` or `duckdb`).
- No plotting library.
- A proxy exists, but it has no Claude model, and no client library is installed to call it (no `langchain-openai`, `langchain-anthropic` or similar).
- The sandbox image installs `pandas` but no parquet engine (`pyarrow` or `fastparquet`), so code run in the sandbox cannot read the dataset yet.

## Configuration and secrets

- `.env` at the repository root is read by Docker Compose (variable substitution) and by `load_dotenv()` in `src/main.py` (it searches upward from `src/`). It is git-ignored.
- `env.example` lists the names: `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`. A `CLAUDE_CODE_OAUTH_TOKEN` would be added only after a "Build with Claude" verdict. It is not named `.env.example` because the project's permission rules deny reading `.env.*`.
- Each container receives only the variables it is given by name in `compose.yaml`. `sandbox` receives none. Compose refuses to start if any of them is unset.
- `LITELLM_SALT_KEY` is set once. LiteLLM cannot rotate it in place.
- Using a subscription token through the proxy is outside what Anthropic's documentation says OAuth is designed for. The user accepted that risk for their own account and their own use (`decisions.md`, ADR 0003). The stack is personal and local: it must not be shared or deployed. There is no API-key fallback.
- No Python code reads any of these variables yet.

## Tests and checks

- No tests exist. The configured check is `uv run --with pytest pytest || [ $? -eq 5 ]`, which tolerates pytest's "no tests collected" exit code.
- `pytest` is not a declared dependency; it is supplied at run time by `uv run --with pytest`.
- No lint or type-check configuration is present in `pyproject.toml`.

## Decision records

In `docs/adr/`:

- 0001: The sandbox has no network and is controlled through Docker exec
- 0002: Fixed Compose project name; the sandbox is found by labels
- 0003: The proxy holds the Claude subscription token, behind a gate that can stop the epic
- 0004: LiteLLM gets a Postgres database as a third service
- 0005: One root .env, an example named env.example, secrets mapped by name
- 0006: The sandbox runs as the image's user, with no user remapping
- 0007: The capability gate is a live probe with a direct control request, run before the build
