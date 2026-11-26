# data-visualization-agent

LangChain/LangGraph project for data visualization (early scaffold). Python, managed with `uv`.

## Commands

- Setup: `uv sync`
- Test: `uv run --with pytest pytest`. There are no tests yet and pytest exits 5 for an empty suite; `.sdlc.json` tolerates exit 5 with `|| [ $? -eq 5 ]`. Remove that tolerance once the first test exists.
- Run: `uv run python main.py`

## Traps

- `pyproject.toml` requires Python `>=3.15`; use the `.venv` that `uv` creates.
- `workspace/` holds the data (a ~53 MB parquet file is committed directly; GitHub warns above 50 MB). Do not add more large files without Git LFS.
- Secrets come from `.env` via `python-dotenv`; never commit it.
- There is no `.gitignore` yet.
