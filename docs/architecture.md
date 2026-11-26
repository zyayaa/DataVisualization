# Architecture

Status: early scaffold. This document describes the repository as it is today. Anything labelled **Intent** is stated or implied by the project metadata but has no code behind it.

## Purpose

- **Intent** (from `pyproject.toml`): "LangChain and LangGraph project for data visualization". The project name is `data-visualization-agent`.
- **Implemented:** a single entry point that prints `Hello World`. No agent, graph, tool, chart or data-loading code exists.

## Components

| Component | Path | State |
|---|---|---|
| Entry point | `main.py` | Implemented (placeholder) |
| Data workspace | `workspace/` | One dataset committed; nothing reads it |
| Project metadata | `pyproject.toml`, `uv.lock` | Implemented |
| Workflow tooling | `.sdlc.json`, `.claude/settings.json`, `.github/ISSUE_TEMPLATE/sdlc-inbox.yml`, `docs/epics/README.md` | Development process only, not part of the runtime |

### `main.py`

The whole application, 8 lines:

- Defines the module constant `WORKSPACE_PATH = "./workspace"`. It is not used anywhere. The path is relative, so it resolves against the current working directory, not the file's location.
- Calls `load_dotenv()` at import time, loading a `.env` file into the environment if one exists. No environment variable is read afterwards.
- Under `if __name__ == "__main__":` prints `Hello World`.

There is no package, no other module, and no test.

### `workspace/`

- `workspace/consumo_horario_mobilidade_eletrica_01_a_10.parquet`, about 53 MB, committed directly to git (no Git LFS).
- By its file name it holds hourly electric-mobility (EV charging) consumption. Its schema, time range and the meaning of `01_a_10` are not documented in the repository and no code inspects them.
- **Intent:** `WORKSPACE_PATH` suggests this folder is where the system will read data from (and possibly write to). That is not implemented.

## Boundaries

There are none to describe yet: one module, no internal calls, no external calls. `main.py` makes no network request, starts no container, and does not open the dataset.

## Data model

None. There is no schema, database, state object or persisted output. The only data is the parquet file above, which is untouched by code.

## Dependencies

Runtime: Python `>=3.15`, managed with `uv` (`uv sync` to set up, `uv run python main.py` to run).

| Declared dependency | Locked version | Used by code today |
|---|---|---|
| `python-dotenv` | 1.2.4 | Yes (`load_dotenv()`) |
| `langchain` | 1.5.2 | No |
| `langchain-core` | 1.8.4 | No |
| `langgraph` | 1.2.24 | No |
| `docker` | 7.2.0 | No |

**Intent** implied by the unused dependencies, with no code behind any of it:

- `langchain` / `langgraph`: an LLM agent built as a graph.
- `docker`: container control from Python; its purpose is not stated anywhere in the repository.

Gaps between the stated intent and what is installed:

- No library that can read parquet (no `pandas`, `pyarrow`, `polars` or `duckdb`).
- No plotting library.
- No LLM provider integration (no `langchain-openai`, `langchain-anthropic` or similar), so no model can be called.

## Configuration and secrets

- `.env` is loaded if present; none is committed and no variable name is defined or consumed by the code.
- There is no `.gitignore` at the repository root.

## Tests and checks

- No tests exist. The configured check is `uv run --with pytest pytest || [ $? -eq 5 ]`, which tolerates pytest's "no tests collected" exit code.
- `pytest` is not a declared dependency; it is supplied at run time by `uv run --with pytest`.
- No lint or type-check configuration is present in `pyproject.toml`.

## Decision records

None. `docs/adr/` does not exist yet.
