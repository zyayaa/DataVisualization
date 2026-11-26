---
id: 001/01
title: The proxy answers as Claude through the subscription token, and only for the master key
type: feature         # feature | bug | task | skeleton
size: M               # XS | S | M ; L must be split
risk: high            # low | medium | high ; high pauses for your approval
ui: none              # none | web | cli
hitl: true            # true if a person must do part of it; pauses for you
---
## Context
This is the first item of the epic, and the one that can cancel it. After it, a filled-in `.env` and `docker compose up -d` start the `litellm` proxy and its Postgres database `db`. A caller on the host who holds the master key gets a Claude reply from the aliases `opus`, `sonnet` and `haiku`. A caller with no key or a wrong key gets 401. The admin UI at `/ui` accepts the login from `.env`. Upstream, the proxy authenticates with the user's Claude subscription token, which it holds server-side. No Anthropic API key exists anywhere (ADR 0003).

The item also makes `.env` impossible to commit (its first change, ADR 0005), adds `env.example` with the secret names, adds the repository's first tests, and removes the exit-5 tolerance from the test check, as `CLAUDE.md` instructs.

Gate G2 (ADR 0003) opens this item. A person reads the documentation of the LiteLLM release to be pinned and Anthropic's model list, fills in the G2 fact sheet (plan.md, "Interfaces and contracts"), and the session records it in `decisions.md` as a `block-answer`. Build every LiteLLM-specific detail from that record, never from memory: image tag, credential setting, variable names, model identifiers, readiness endpoint, Postgres major. Gate G1 is answered: the user chose to use the subscription token (decisions.md, 2026-11-26).

Agents cannot run `docker` or read `.env`, so the live checks are opt-in stack tests under `tests/stack/`. They run only with `STACK_TESTS=1`, and a person runs them.

## Acceptance criteria
- AC1: Given the repository after this item When `git check-ignore .env` runs Then it reports `.env` as ignored  — check: test
- AC2: Given the repository after this item When `git check-ignore .env.local` runs Then it reports `.env.local` as ignored  — check: test
- AC3: Given the repository after this item When `git check-ignore env.example` runs Then it reports `env.example` as not ignored  — check: test
- AC4: Given `compose.yaml` When it is parsed Then its top-level `name` is `data-visualization-agent`  — check: test
- AC5: Given `compose.yaml` When it is parsed Then it defines the services `litellm` and `db`; the test does not require that these are the only services  — check: test
- AC6: Given `compose.yaml` When it is parsed Then the named volume `litellm_pgdata` is declared and mounted by `db` and by no other service  — check: test
- AC7: Given `compose.yaml` When the `ports` of every service are collected Then the only published port is `127.0.0.1:4000:4000`, on `litellm`  — check: test
- AC8: Given `compose.yaml` When the `litellm` image reference is read Then it carries a release-version tag: not absent, not `latest`, not a `main-*` tag  — check: test
- AC9: Given `compose.yaml` When the `db` image reference is read Then it is a Postgres image whose tag starts with a major version number  — check: test
- AC10: Given `compose.yaml` When the `environment` of `litellm` and `db` is read Then every value that carries a secret has the form `${NAME:?message}`  — check: test
- AC11: Given `compose.yaml` When every service is read Then none has an `env_file` key or a bare pass-through environment entry (a name with no value)  — check: test
- AC12: Given `compose.yaml` When the volumes of every service are read Then none mounts the repository root, `.env` or `/var/run/docker.sock`  — check: test
- AC13: Given `env.example` and `compose.yaml` When the names defined in `env.example` are compared with the names interpolated as `${NAME...}` in `compose.yaml` Then the two sets are equal  — check: test
- AC14: Given `env.example` When it is read Then every name has a placeholder value and a comment line directly above it  — check: test
- AC15: Given `env.example` When it is read Then it states that generated values use only letters, digits, `-` and `_`  — check: test
- AC16: Given `compose.yaml`, `litellm/config.yaml` and `env.example` When their text is searched Then the string `ANTHROPIC_API_KEY` occurs in none of them  — check: test
- AC17: Given `litellm/config.yaml` When it is parsed Then it defines exactly the model aliases `opus`, `sonnet` and `haiku`, each mapped to an Anthropic model of the matching family  — check: test
- AC18: Given `litellm/config.yaml` When every credential value in it is read Then each is an `os.environ/<NAME>` reference  — check: test
- AC19: Given `compose.yaml` When the `litellm` service is read Then `./litellm/config.yaml` is mounted read-only at the path its `command` passes to `--config`  — check: test
- AC20: Given `litellm/config.yaml` When it is parsed Then it enables no forwarding of client headers to the upstream, and sets no system prompt, user agent or client-identity header  — check: test
- AC21: Given `compose.yaml` When the `litellm` service is read Then it depends on `db` with `condition: service_healthy`  — check: test
- AC22: Given `compose.yaml` When the `db` service is read Then it declares a health check  — check: test
- AC23: Given `.sdlc.json` When the `test` check's command is read Then it no longer tolerates exit code 5  — check: test
- AC24: Given `STACK_TESTS` is not set When `uv run --with pytest pytest` runs Then it exits 0  — check: command
- AC25: Given `STACK_TESTS` is not set When the default suite runs Then every test under `tests/stack/` is reported as skipped  — check: test
- AC26: Given an empty env file and an environment without the stack's variables When `docker compose config` runs Then it exits non-zero (stack test, run by a person)  — check: test
- AC27: Given an empty env file and an environment without the stack's variables When `docker compose config` runs Then its error names a missing variable (stack test, run by a person)  — check: test
- AC28: Given a filled-in `.env` When `docker compose up -d` has run Then the `litellm` and `db` containers are both running (stack test, run by a person)  — check: test
- AC29: Given a filled-in `.env` When `docker compose up -d` has run Then Docker reports `db` as healthy (stack test, run by a person)  — check: test
- AC30: Given the stack is up When the proxy's readiness endpoint is polled Then it answers as ready within the test's timeout (stack test, run by a person)  — check: test
- AC31: Given the stack is up When a chat completion is sent with the master key to each of `opus`, `sonnet` and `haiku` Then each response has status 200 (stack test, run by a person; gate G3, Done when 4)  — check: test
- AC32: Given the stack is up When a chat completion is sent with the master key to each alias Then each response carries a non-empty assistant message (stack test, run by a person; Done when 4)  — check: test
- AC33: Given the filled-in `.env` When its names are read Then `ANTHROPIC_API_KEY` is not among them (stack test, run by a person; Done when 4)  — check: test
- AC34: Given the stack is up When Docker reports the `litellm` container's environment Then no variable named `ANTHROPIC_API_KEY` is in it (stack test, run by a person; Done when 4)  — check: test
- AC35: Given the stack is up When a chat completion is sent with no `Authorization` header Then the response status is 401 (stack test, run by a person; Done when 5)  — check: test
- AC36: Given the stack is up When a chat completion is sent with a wrong bearer value Then the response status is 401 (stack test, run by a person; Done when 5)  — check: test
- AC37: Given the stack is up When `GET http://127.0.0.1:4000/ui` is requested Then the response is an HTML page (stack test, run by a person; Done when 6)  — check: test
- AC38: Given the stack is up When Docker reports the published ports of `litellm` Then port 4000 is bound to host address `127.0.0.1` only (stack test, run by a person)  — check: test

## Edge cases
- G2 finds no documented server-side route for the token, or only a route where each client forwards its own credential, or a route that requires the proxy to present Claude Code's identity: stop before building and report. No API key, no workaround.
- G3 returns an upstream authentication error, or an error saying the credential is authorised only for Claude Code: stop and report. Do not add identity headers, a user agent or a system prompt to get past it.
- An alias the user's subscription plan does not cover fails at request time: report it as a block. Do not delete the alias silently.
- An expired token gives an upstream authentication error that looks like a regression: the stack test's failure message says to check the token first.
- `ANTHROPIC_API_KEY` exported in the person's shell must not reach any container. The explicit `environment:` mapping guarantees this, and AC34 observes it.
- The first `up` pulls images, so the readiness wait needs a generous timeout.
- The Postgres data directory differs by major version. The volume path must match the pinned major from the fact sheet.
- If the fact sheet names a further secret the release needs when a database is present (for example a salt key), it goes into both `env.example` and `compose.yaml`, and AC13 keeps them in step.
- `POSTGRES_PASSWORD` sits inside `DATABASE_URL`, so the character rule (letters, digits, `-`, `_`) applies to it.
- pytest prints compared values on failure, so no secret value may sit in an assertion expression, a test id or a parameter. The output of `docker compose config` contains resolved secrets and is never echoed.

## Out of scope
- The `sandbox` service, the README set-up steps and the architecture document update: item 02.
- Any edit to `sandbox/Dockerfile`, `main.py`, `pyproject.toml` or `uv.lock`.
- Any API-key, Bedrock or Vertex provider, or any fallback to one.
- Any configuration done inside the LiteLLM UI (teams, budgets, virtual keys).
- Any change to `.claude/settings.json` or to `allowed_bash` in `.sdlc.json`.

## Technical notes
Interfaces/contracts:
- `compose.yaml` follows the shape in design.md and the rules in plan.md, "Interfaces and contracts". In this item it holds the services `litellm` and `db` and the volume `litellm_pgdata`. Item 02 adds `sandbox` to the same file.
- `litellm`: image pinned to the fact-sheet tag; `command: ["--config", "/app/config.yaml"]`; `./litellm/config.yaml` mounted read-only at `/app/config.yaml`; port `127.0.0.1:4000:4000`; `depends_on: db: condition: service_healthy`; environment `LITELLM_MASTER_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` (which may be renamed inside the container to what the fact sheet says the proxy expects), `UI_USERNAME`, `UI_PASSWORD`, and `DATABASE_URL=postgresql://litellm:${POSTGRES_PASSWORD:?...}@db:5432/litellm`.
- `db`: Postgres pinned to the fact-sheet major; `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm`, `POSTGRES_PASSWORD`; a `pg_isready` health check; no ports; `litellm_pgdata` mounted at the pinned major's data directory.
- Secret names in `env.example`: `LITELLM_MASTER_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`, plus any further secret the fact sheet names.
- Proxy: `POST http://127.0.0.1:4000/v1/chat/completions`, header `Authorization: Bearer <LITELLM_MASTER_KEY>`, body `{"model": "<alias>", "messages": [...]}`. Admin UI at `http://127.0.0.1:4000/ui`.
- Test helpers that item 02 reuses unchanged:

```python
# tests/conftest.py
REPO_ROOT: pathlib.Path
def load_compose() -> dict                               # parsed compose.yaml
def interpolated_names() -> set[str]                     # names used as ${NAME...} in compose.yaml
def example_env_names() -> set[str]                      # names defined in env.example
def pytest_collection_modifyitems(config, items) -> None # skips `stack` items unless STACK_TESTS=1

# tests/stack/conftest.py
PROXY_URL = "http://127.0.0.1:4000"
PROJECT = "data-visualization-agent"
def docker_compose(*args: str, timeout: float = ...) -> subprocess.CompletedProcess  # captured, never echoed
@pytest.fixture(scope="session")
def secrets() -> Mapping[str, str]                       # values of .env via dotenv_values; never printed
@pytest.fixture(scope="session")
def stack_up(secrets) -> None                            # `docker compose up -d`, waits for readiness, leaves the stack running
def chat(alias: str, bearer: str | None) -> tuple[int, dict]  # status and parsed body of a chat-completion call
```

- Tests under `tests/stack/` carry the marker `stack`. YAML is parsed with `yaml.safe_load`; PyYAML is already locked through `langchain-core`. HTTP calls use the standard library.
- Secrecy rules for stack tests: `.env` values are read only inside the test process. Assertions compare status codes, booleans and names, never secret values.

Files expected to change: `.gitignore`, `compose.yaml`, `litellm/config.yaml`, `env.example`, `tests/conftest.py`, `tests/test_proxy_stack_files.py`, `tests/stack/conftest.py`, `tests/stack/test_proxy.py`, `.sdlc.json` (the `test` check command only), `CLAUDE.md`
Existing tests expected to change: none (there are no tests yet)
Dependencies to add: none in Python. Two container images, both covered by the design: the LiteLLM proxy image pinned to the release tag from the G2 fact sheet (the proxy itself), and a Postgres image pinned to a major version (LiteLLM's database, ADR 0004).
Docs to update: `CLAUDE.md` (the Test line: tests now exist, the exit-5 tolerance is gone, how the stack suite is switched on, and that agents do not run it)

## Manual checks
- In a browser, `http://127.0.0.1:4000/ui` accepts `UI_USERNAME` / `UI_PASSWORD` from `.env` (Done when 6).
- In a browser, the same login page refuses a wrong password.
- After `docker compose down` and `docker compose up -d`, the login still works.
- After `docker compose down`, the volume `data-visualization-agent_litellm_pgdata` still exists.
- The `litellm` logs show the database schema applied on start-up with no extra step.

## Human step
Before the build (gate G2):
1. Read the documentation of the LiteLLM release to be pinned and Anthropic's published model list.
2. Fill in the G2 fact sheet from plan.md, "Interfaces and contracts": image and tag, the server-side credential setting and the variable it expects, whether that route presents Claude Code's identity, the three model identifiers, the UI variable names and master-key format, any further secret, whether the schema is applied on start-up, the Postgres major and its data directory, and the readiness endpoint.
3. If there is no documented way for the proxy to hold the subscription token server-side with no API key, or that way makes the proxy present Claude Code's identity, the epic stops here.

The session records the answer in `decisions.md` as a `block-answer`.

After the build (gate G3, Done when 4 to 6), on a machine with Docker:
1. Copy `env.example` to `.env`.
2. Fill it with real values, including a token from `claude setup-token`.
3. Run `docker compose up -d`.
4. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`.
5. Do the manual checks.
6. Report the pytest summary and the result of the browser login.

Never paste `.env` or the output of `docker compose config`. If `.sdlc.json` cannot be edited from an item branch, make the one-line change to the test check by hand.
