# data-visualization-agent

LangChain/LangGraph project for data visualization (early scaffold). Python, managed with `uv`.

## Commands

- Setup: `uv sync`
- Test: `uv run --with pytest pytest`. There are no tests yet and pytest exits 5 for an empty suite; `.sdlc.json` tolerates exit 5 with `|| [ $? -eq 5 ]`. Remove that tolerance once the first test exists.
- Run: `uv run python main.py`

## Traps

- `pyproject.toml` requires Python `>=3.15`; use the `.venv` that `uv` creates.
- `workspace/` holds the data. `*.parquet` is stored with Git LFS (see `.gitattributes`), so `git-lfs` must be installed before cloning; without it the file is a small text pointer. Add other large formats to `.gitattributes` before committing them.
- Secrets come from `.env` via `python-dotenv`; never commit it.
