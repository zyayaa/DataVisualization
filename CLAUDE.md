# data-visualization-agent

LangChain/LangGraph project for data visualization (early scaffold). Python, managed with `uv`.

## Commands

- Setup: `uv sync`
- Test: `uv run --with pytest pytest`. Static tests live in `tests/`. The stack suite in `tests/stack/` is skipped unless `STACK_TESTS=1` and only a person runs it (it needs Docker and `.env`). The exit-5 tolerance in `.sdlc.json` no longer has an effect; only the user can remove it, on the base branch.
- Run: `uv run python src/main.py`
- Stack: copy `env.example` to `.env` and fill it in, then `docker compose up -d` (litellm, db, sandbox); `docker compose down` stops it (`down -v` deletes the `litellm_pgdata` database volume).
- Stack tests (person only): `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`

## Traps

- `pyproject.toml` requires Python `>=3.15`; use the `.venv` that `uv` creates.
- `workspace/` holds the data. `*.parquet` is stored with Git LFS (see `.gitattributes`), so `git-lfs` must be installed before cloning; without it the file is a small text pointer. Add other large formats to `.gitattributes` before committing them.
- Secrets come from `.env` via `python-dotenv`; never commit it.
- The example file is `env.example` (not `.env.example`) because agents cannot read `.env.*`. `.env` and `.env.*` are git-ignored by the committed `.gitignore`.
