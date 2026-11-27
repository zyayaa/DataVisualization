---
id: 001/01
title: The proxy, its database and the admin UI start from the env file and refuse callers without the master key
type: feature         # feature | bug | task | skeleton
size: M               # XS | S | M ; L must be split
risk: high            # low | medium | high ; high pauses for your approval
ui: none              # none | web | cli
hitl: true            # true if a person must do part of it; pauses for you
---
## Context
This is the first item of the epic. After it, a filled-in `.env` and `docker compose up -d` start:
- `litellm`, pinned to the `Tag:` of the newest probe verdict record in `decisions.md`;
- `db`, its Postgres database.

The proxy has no model yet. A caller with no key or a wrong key gets 401, the master key is accepted, and the admin UI at `/ui` takes the login from `.env`.

The item also:
- makes `.env` impossible to commit;
- adds `env.example` with the five base secret names (`LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`);
- adds the repository's first tests.

The item is the same under either verdict of the token test, except for the image tag. The two container images are covered by design.md, "New dependencies".

The gate (ADR 0003, ADR 0007) runs before this item: fact-sheet rows 10 to 13, then G2a and G2b, then the verdict record. Everything LiteLLM- or Postgres-specific comes from those records in `decisions.md`, never from memory:
- the image tag;
- the Postgres tag and its data directory.

The pipeline proves only the files. Live behaviour is checked by a person with the stack suite (`STACK_TESTS=1`), whose test names are fixed in plan.md, "Stack-suite contract".

## Acceptance criteria
- AC1: Given the committed `.gitignore` When `git check-ignore -v .env` runs Then it names a rule from the committed `.gitignore`  — check: test
- AC2: Given the committed `.gitignore` When `git check-ignore -v .env.local` runs Then it names a rule from the committed `.gitignore`  — check: test
- AC3: Given the committed `.gitignore` When `git check-ignore env.example` runs Then it reports `env.example` as not ignored  — check: test
- AC4: Given `compose.yaml` When it is parsed Then its top-level `name` is `data-visualization-agent`  — check: test
- AC5: Given `compose.yaml` When it is parsed Then it defines the services `litellm` and `db`; the test does not require that these are the only services  — check: test
- AC6: Given `compose.yaml` and fact-sheet row 13 When the volumes are read Then the named volume `litellm_pgdata` is declared and mounted by `db` at the data directory of row 13, and by no other service  — check: test
- AC7: Given `compose.yaml` When the `ports` of every service are collected Then the only published port is `127.0.0.1:4000:4000`, on `litellm`  — check: test
- AC8: Given `compose.yaml` and the newest probe verdict record When the `litellm` image is read Then it is exactly `ghcr.io/berriai/litellm:<Tag>` with that record's `Tag`  — check: test
- AC9: Given `compose.yaml` and fact-sheet row 13 When the `db` image is read Then it is exactly the Postgres tag of row 13  — check: test
- AC10: Given `compose.yaml` When every `${...}` interpolation is read Then each has the form `${NAME:?message}`  — check: test
- AC11: Given `compose.yaml` When every service is read Then none has an `env_file` key or an environment entry with a name and no value  — check: test
- AC12: Given `compose.yaml` When the volumes of every service are read Then none mounts the repository root, `.env` or `/var/run/docker.sock`  — check: test
- AC13: Given `compose.yaml` When the `litellm` environment is read Then it holds at least `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD` and `DATABASE_URL`, the last being `postgresql://litellm:${POSTGRES_PASSWORD:?...}@db:5432/litellm`; the test checks "at least" so item 02 can add one key  — check: test
- AC14: Given `compose.yaml` When the `db` environment is read Then it holds `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm` and `POSTGRES_PASSWORD`  — check: test
- AC15: Given `compose.yaml` When the `litellm` service is read Then it depends on `db` with `condition: service_healthy`  — check: test
- AC16: Given `compose.yaml` When the `db` service is read Then it declares a health check that uses `pg_isready`  — check: test
- AC17: Given `env.example` and `compose.yaml` When the names defined in `env.example` are compared with the names interpolated in `compose.yaml` Then the two sets are equal  — check: test
- AC18: Given `env.example` When its names are read Then they include `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD` and `POSTGRES_PASSWORD`; the test checks "include" so item 02 can add the token  — check: test
- AC19: Given `env.example` When it is read Then every name has a placeholder value and a comment line directly above it  — check: test
- AC20: Given `env.example` When it is read Then the `LITELLM_MASTER_KEY` placeholder starts with `sk-`  — check: test
- AC21: Given `env.example` When it is read Then it states that generated values use only letters, digits, `-` and `_`  — check: test
- AC22: Given `env.example` When the comment above `LITELLM_SALT_KEY` is read Then it says the key is generated once and never changed  — check: test
- AC23: Given `compose.yaml`, `litellm/config.yaml` and `env.example` When their text is searched Then the string `ANTHROPIC_API_KEY` occurs in none of them  — check: test
- AC24: Given `compose.yaml` When the `litellm` service is read Then `./litellm/config.yaml` is mounted read-only at the path its `command` passes to `--config`  — check: test
- AC25: Given `litellm/config.yaml` When it is loaded Then it parses as YAML  — check: test
- AC26: Given `litellm/config.yaml` When its keys are read Then no key name contains `forward`, `system`, `user-agent` or `user_agent`  — check: test
- AC27: Given `litellm/config.yaml` When its text is searched in any letter case Then, apart from the variable name `CLAUDE_CODE_OAUTH_TOKEN`, it contains none of `claude code`, `claude-code`, `claude_code`, `claude-cli`  — check: test
- AC28: Given `STACK_TESTS` is not set When pytest runs `tests/stack/test_proxy.py` Then it exits 0, runs no test, and reports these as skipped: `test_litellm_and_db_are_running`, `test_db_is_healthy`, `test_proxy_reports_ready`, `test_missing_key_gets_401`, `test_wrong_key_gets_401`, `test_master_key_is_not_refused`, `test_master_key_has_sk_prefix`, `test_ui_page_is_served`, `test_proxy_port_is_loopback_only`, `test_compose_refuses_an_empty_env`  — check: test
- AC29: Given `STACK_TESTS` is not set When `uv run --with pytest pytest` runs Then it exits 0  — check: command

## Edge cases
- Files: `decisions.md` has no probe verdict record, or no fact-sheet rows 10 to 13, when the item starts. Stop with `BLOCKED`; the tag, the Postgres tag and the data directory are not guessed.
- Files: a `.env` entry in the person's `.git/info/exclude` must not satisfy AC1. It asks for the rule in the committed `.gitignore`.
- Files: `POSTGRES_PASSWORD` sits inside a URL, so the character rule applies to it.
- Files: `ANTHROPIC_API_KEY` exported in the person's shell must not reach a container. The explicit `environment:` mapping guarantees it; item 02 observes it.
- Live (person): the pinned release does not start with a config that defines no model. Report it as a block; no placeholder model is added.
- Live (person): the schema is not applied on start-up (fact-sheet row 7 is unconfirmed for `v1.108.18`). Report it as a block; no migration step is added and the pin does not move.
- Live (person): the proxy answers a keyless request with something other than 401 while no model exists. Report it as a block.
- Live (person): the first `up` pulls images, so the `stack_up` fixture allows 15 minutes.

## Out of scope
- Any Claude model, the subscription token and `CLAUDE_CODE_OAUTH_TOKEN`: item 02.
- The `sandbox` service and the README: item 03.
- `docs/architecture.md`: applied at ship from design.md.
- Any edit to `.sdlc.json`, `.claude/settings.json`, `sandbox/Dockerfile`, `main.py`, `pyproject.toml` or `uv.lock`.
- Any API-key, Bedrock or Vertex provider.
- Any configuration done inside the LiteLLM UI.

## Technical notes
Interfaces/contracts:
- Rules, fixed values, the probe verdict record format and the stack-suite contract are in plan.md, "Interfaces and contracts". The record has the lines `G2a`, `G2b`, `Verdict`, `Tag` and `Wiring`, and the newest one wins.
- `litellm`:
  - `command: ["--config", "/app/config.yaml"]`, with `./litellm/config.yaml` mounted read-only at `/app/config.yaml`;
  - port `127.0.0.1:4000:4000`;
  - `depends_on: db: condition: service_healthy`;
  - environment `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD` and `DATABASE_URL`.
- `litellm/config.yaml` defines no model in this item.
- `db`:
  - the Postgres tag of row 13, with `litellm_pgdata` mounted at row 13's data directory;
  - `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm`, `POSTGRES_PASSWORD`;
  - a `pg_isready` health check;
  - no ports.
- Readiness: `GET /health/readiness`, with no authentication.
- Proxy: `POST http://127.0.0.1:4000/v1/chat/completions` with `Authorization: Bearer <LITELLM_MASTER_KEY>`. Admin UI at `http://127.0.0.1:4000/ui`.
- Test helpers are pytest fixtures, so no test module imports another. Items 02 and 03 reuse them unchanged:

```python
# tests/conftest.py  (written by the test author, locked, never changed later)
@pytest.fixture(scope="session")
def repo_root() -> pathlib.Path
@pytest.fixture(scope="session")
def compose(repo_root) -> dict                  # compose.yaml through yaml.safe_load
@pytest.fixture(scope="session")
def proxy_config(repo_root) -> dict             # litellm/config.yaml; {} when it holds no mapping
@pytest.fixture(scope="session")
def interpolated_names(repo_root) -> set[str]   # NAME of every ${NAME...} in compose.yaml
@pytest.fixture(scope="session")
def example_env_names(repo_root) -> set[str]    # names defined in env.example

# tests/stack/conftest.py  (written by the implementer, never changed later)
PROXY_URL = "http://127.0.0.1:4000"
PROJECT = "data-visualization-agent"
@pytest.fixture(scope="session")
def docker_compose(repo_root) -> Callable[..., subprocess.CompletedProcess]  # output captured, never echoed
@pytest.fixture(scope="session")
def secrets(repo_root) -> Mapping[str, str]     # dotenv_values(".env"); never printed
@pytest.fixture(scope="session")
def stack_up(docker_compose) -> None            # `up -d` (allows 15 minutes), polls readiness, leaves the stack up
@pytest.fixture(scope="session")
def chat() -> Callable[[str, str | None], tuple[int, dict]]   # (alias, bearer) -> (status, parsed body)
@pytest.fixture(scope="session")
def container_env_names(docker_compose) -> Callable[[str], set[str]]  # service -> variable names, values dropped
```

- Every module under `tests/stack/` carries a module-level skip unless `STACK_TESTS=1`. Nothing there touches Docker at import or collection time.
- YAML is parsed with PyYAML, already locked through `langchain-core`. HTTP uses the standard library.
- Secrecy rules for the stack suite:
  - `.env` values exist only inside the test process.
  - An `assert` takes only a precomputed boolean, a status code or a name.
  - Output of `docker compose config` and `docker inspect` is never echoed.

Files expected to change: `.gitignore`, `compose.yaml`, `litellm/config.yaml`, `env.example`, `CLAUDE.md`, `tests/conftest.py`, `tests/test_proxy_files.py`, `tests/stack/conftest.py`, `tests/stack/test_proxy.py`
Existing tests expected to change: none
Dependencies to add: none
Docs to update: `CLAUDE.md`:
- The Test line: tests exist; the stack suite runs only with `STACK_TESTS=1`, and only a person runs it; the exit-5 tolerance in `.sdlc.json` no longer has an effect, and only the user can remove it, on the base branch.
- The traps: the example file is `env.example` because agents cannot read `.env.*`; `.env` is now git-ignored.

## Manual checks
none

## Human step
**Before the build: the gate.** This is best done before the spec pull request is merged, so both records merge with the spec.
1. With the session, complete the fact sheet in `decisions.md` with rows 10 to 13:
   - the Messages endpoint and the API version header;
   - the exact name and value of the OAuth beta header;
   - the config key names for W1 and W2 in the pinned release;
   - the Postgres tag and its data directory.

   If the beta header's value contains a flag that names Claude Code, stop and ask the user before G2a.
2. Run G2a exactly as design.md writes it:
   - a fresh token from `claude setup-token`;
   - no `system` field;
   - no user-agent override;
   - no other header;
   - no verbose or trace flag.
3. Only if G2a returned 200, run G2b:
   - one throwaway LiteLLM container on `v1.108.18`, published on `127.0.0.1` only, with one alias and a throwaway master key;
   - try W1, then W2 (for W2, use the variable name `CLAUDE_UPSTREAM_AUTHORIZATION`);
   - if both fail for a LiteLLM-side reason, try both once more on `v1.111.0`;
   - remove the container afterwards.
4. A 429, a 5xx or an error about the model is not a verdict. Repeat later, or with another model identifier.
5. Have the session record the verdict in `decisions.md` with the lines `G2a`, `G2b`, `Verdict`, `Tag` and `Wiring`. Never record the token or response headers.
6. Keep the token and the probe's files outside the repository. `.env` is not git-ignored yet.

**After the build, when the item pauses for you**, on a machine with Docker:
1. Add `.env` to `.git/info/exclude`.
2. Check out the item's branch, copy `env.example` to `.env` and fill it in:
   - a master key starting with `sk-`;
   - a salt key, generated once;
   - the UI user and password;
   - the Postgres password.
3. Run `docker compose up -d`, then `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`.
4. Read the `litellm` logs to confirm the schema was applied on start-up with no extra step.
5. In a browser, check that `http://127.0.0.1:4000/ui` accepts the login from `.env` and refuses a wrong password (Done when 6).
6. Run `docker compose down`, then `docker compose up -d`. The login should still work, and the volume `data-visualization-agent_litellm_pgdata` should still exist.
7. Merge the pull request only if all of that holds. Otherwise tell the session what failed.

Never paste `.env`, or the output of `docker compose config` or `docker inspect`.
