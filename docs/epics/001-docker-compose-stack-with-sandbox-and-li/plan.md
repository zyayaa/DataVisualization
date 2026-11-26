# Plan: Docker Compose stack with sandbox and LiteLLM proxy

## Interfaces and contracts

**Files of the stack.** `compose.yaml` (repo root), `litellm/config.yaml`, `env.example` (repo root), `.gitignore`, `README.md`, `CLAUDE.md`, and `sandbox/Dockerfile` (existing code from pull request #3, never edited by an item). No slice touches `main.py`, `pyproject.toml` or `uv.lock`.

**Limits of the item pipeline (they shape every slice).**
- The pipeline's script runs each criterion's command itself.
  - A `test` criterion must fail before the build and pass after it.
  - A `command` criterion must pass after it and may already pass before.
  - So only what runs without Docker and without `.env` can be a criterion. A skipped stack test exits 0 and cannot be one.
- An item cannot change `.sdlc.json`, `.claude/settings.json`, a CI workflow, `docs/architecture.md`, `docs/adr/` or `docs/epics/`.
  - `docs/architecture.md` is updated at ship from design.md, "Change to the architecture document". That section already lists ADR 0001 to 0007.
  - The exit-5 tolerance in `.sdlc.json` stays. Once tests exist it has no effect.
- Manual checks listed on an item go to an agent that cannot run `docker` or read `.env`, and it must report what it could not do as failed. Every slice therefore says `Manual checks: none`, and what a person checks is under "Human step".
- The item fields "Existing tests expected to change", "Dependencies to add" and "Manual checks" must read exactly `none`. Any other wording switches a guard off or spawns the verifier.

**Subscription-token gate (ADR 0003, ADR 0007).** A person runs it before slice 01 is built, in this order.
1. **Fact-sheet completion.** From primary sources, the session appends a `block-answer` to `decisions.md` that continues the fact sheet's numbering:
   - Row 10: Anthropic's Messages endpoint and the API version header (name and value).
   - Row 11: the exact name and value of the OAuth beta header LiteLLM adds (the page of row 2).
   - Row 12: the config key names in the pinned release for W1 (the deployment's credential) and W2 (static upstream headers on a deployment), and whether a header value accepts an `os.environ/` reference.
   - Row 13: the Postgres image tag (major) and its data directory. This settles row 8.
2. **G2a, control.** One direct request to Anthropic, as written in design.md.
3. **G2b, proxy.** Only after G2a returned 200. One throwaway container, W1 then W2, on `v1.108.18`. Both may be tried once more on `v1.111.0` if both failed for a LiteLLM-side reason.

**Probe verdict record.** A second `block-answer` in `decisions.md` with these lines. It never holds the token or response headers.
```
G2a: <HTTP status>[ <error type>]
G2b: not run | <tag> <W1|W2> <HTTP status>[ <error type>]   (one line per attempt)
Verdict: Build with Claude | No Claude
Tag: v1.108.18 | v1.111.0
Wiring: W1 | W2 | none
```
- `Tag` is `v1.108.18` unless the verdict is "Build with Claude" and the attempt that passed ran on `v1.111.0`.
- The newest verdict record wins.
- A worker that finds no verdict record, or no rows 10 to 13, stops with `BLOCKED`. Nothing about LiteLLM or Anthropic is built from memory.

**Fixed values.**

| Fact | Value | Source |
|---|---|---|
| LiteLLM image | `ghcr.io/berriai/litellm:<Tag>` | row 1, verdict record |
| Upstream models | `opus` → `anthropic/claude-opus-5-5`, `sonnet` → `anthropic/claude-sonnet-5-5`, `haiku` → `anthropic/claude-haiku-5-5` | rows 2, 4 |
| Readiness | `GET /health/readiness`, no authentication, 503 while the database is unreachable | row 9 |
| Master key | starts with `sk-` | row 5 |
| UI login | `UI_USERNAME`, `UI_PASSWORD`, at `/ui` | row 5 |
| Salt key | `LITELLM_SALT_KEY`, generated once, never changed | row 6 |
| Postgres tag and data directory | as recorded | row 13 |
| OAuth beta header | name and value as recorded | row 11 |
| Config key names for W1 and W2 | as recorded | row 12 |

**What the verdict builds (slice 02).** Base secret names: `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`. Base container keys of `litellm`: the first four and `DATABASE_URL`.

| Verdict, wiring | `env.example` names | `litellm` keys beyond the base | `litellm/config.yaml` |
|---|---|---|---|
| Build with Claude, W1 | base five and `CLAUDE_CODE_OAUTH_TOKEN` | `CLAUDE_CODE_OAUTH_TOKEN` | three deployments; credential `os.environ/CLAUDE_CODE_OAUTH_TOKEN`; no static header |
| Build with Claude, W2 | the same six | `CLAUDE_UPSTREAM_AUTHORIZATION`, value `Bearer ${CLAUDE_CODE_OAUTH_TOKEN:?…}` | three deployments; exactly two static headers: authorization as `os.environ/CLAUDE_UPSTREAM_AUTHORIZATION`, and the OAuth beta header of row 11 |
| No Claude | base five | none | no model, no `os.environ/` reference |

**Identity rule (ADR 0003).**
- Allowed upstream: the bearer authorization, the API version header, the OAuth beta header, and LiteLLM's own default user agent.
- Forbidden: anything that names Claude Code (system prompt, user agent, client header, beta flag, session or device identifier), and forwarding of client headers.
- A header on neither list is forbidden until the user rules on it.
- No custom code, callback or patched image. No API key and no other Claude provider under any verdict.

**`compose.yaml` rules every slice keeps true.**
- Top-level `name: data-visualization-agent`.
- Services: `litellm` and `db` (slice 01), `sandbox` (slice 03). Named volume `litellm_pgdata`, mounted by `db` only.
- The only published port is `127.0.0.1:4000:4000`, on `litellm`.
- Secrets reach containers only through an explicit `environment:` mapping. Every interpolation has the form `${NAME:?set NAME in .env}`. No `env_file:`, no bare pass-through.
- `litellm`:
  - `command: ["--config", "/app/config.yaml"]`, with `./litellm/config.yaml` mounted read-only at that path;
  - `DATABASE_URL=postgresql://litellm:${POSTGRES_PASSWORD:?…}@db:5432/litellm`;
  - `depends_on: db: condition: service_healthy`.
- `db`: `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm`, a `pg_isready` health check, no ports.
- `sandbox`: `build: ./sandbox`, `network_mode: none`, `init: true`, one volume `./workspace:/workspace`, and no other key.
- No container mounts the repository root, `.env` or the Docker socket.
- The string `ANTHROPIC_API_KEY` is in none of `compose.yaml`, `litellm/config.yaml`, `env.example`.
- The names in `env.example` always equal the names interpolated in `compose.yaml`.
- Generated values use letters, digits, `-` and `_` only.

**Host to proxy.** `POST http://127.0.0.1:4000/v1/chat/completions`, header `Authorization: Bearer <LITELLM_MASTER_KEY>`, body `{"model": "<alias>", "messages": [...]}`. Missing or wrong key: 401. The caller never sends an Anthropic credential. Admin UI: `http://127.0.0.1:4000/ui`.

**Host to sandbox (contract for a later epic).** Docker Engine exec. The container is found by the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. User `sandboxuser`, working directory `/workspace`.

**Test harness.** Helpers are pytest fixtures, so no test module imports another.
```python
# tests/conftest.py  (slice 01; written by the test author, locked, never changed later)
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

# tests/stack/conftest.py  (slice 01; written by the implementer, never changed later)
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
- YAML is parsed with PyYAML, already locked through `langchain-core`. HTTP uses the standard library.
- Every module under `tests/stack/` carries a module-level skip unless `STACK_TESTS=1`. Nothing there touches Docker at import or collection time.

**Stack-suite contract.** A person runs it: `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. The implementer writes these tests under exactly these names; a locked static test checks the names and the default skip.

| Slice | File | Test | Asserts | Done when |
|---|---|---|---|---|
| 01 | `test_proxy.py` | `test_litellm_and_db_are_running` | both containers are in the running state | |
| 01 | | `test_db_is_healthy` | Docker reports `db` healthy | |
| 01 | | `test_proxy_reports_ready` | readiness returns 200 within the timeout | |
| 01 | | `test_missing_key_gets_401` | chat completion with no `Authorization` returns 401 | 5 |
| 01 | | `test_wrong_key_gets_401` | chat completion with a wrong bearer returns 401 | 5 |
| 01 | | `test_master_key_is_not_refused` | the same request with the master key returns a status other than 401 | 5 |
| 01 | | `test_master_key_has_sk_prefix` | the key in `.env` starts with `sk-` | |
| 01 | | `test_ui_page_is_served` | `GET /ui` returns an HTML page | 6 |
| 01 | | `test_proxy_port_is_loopback_only` | Docker reports port 4000 bound to `127.0.0.1` only | |
| 01 | | `test_compose_refuses_an_empty_env` | `docker compose config` with an empty env file and a scrubbed environment exits non-zero and names a missing variable | |
| 02 | `test_claude.py` | `test_claude_setup_matches_the_verdict` | Build: each of `opus`, `sonnet`, `haiku` returns 200 and a non-empty assistant message. No Claude: none of the three returns 200 | 4 |
| 02 | | `test_subscription_token_presence_matches_the_verdict` | W1: `litellm` has `CLAUDE_CODE_OAUTH_TOKEN`. W2: it has `CLAUDE_UPSTREAM_AUTHORIZATION`. No Claude: it has neither, and `.env` does not define the token | 4 |
| 02 | | `test_env_file_defines_no_anthropic_api_key` | `.env` has no such name | 4 |
| 02 | | `test_proxy_container_has_no_anthropic_api_key` | the `litellm` container has no such variable | 4 |
| 03 | `test_sandbox.py` | `test_all_three_services_are_running` | `sandbox`, `litellm` and `db` are running | 1 |
| 03 | | `test_sandbox_is_found_by_compose_labels` | exactly one container carries both labels | |
| 03 | | `test_workspace_lists_the_dataset` | `ls /workspace` lists `consumo_horario_mobilidade_eletrica_01_a_10.parquet` | 2 |
| 03 | | `test_file_written_in_sandbox_appears_on_host` | a uniquely named file created by the default user, who is `sandboxuser`, exists in `workspace/`; removed afterwards, also on failure | 2 |
| 03 | | `test_outbound_connection_to_public_ip_fails` | a TCP connection from Python to a public IP address fails within a short timeout | 3 |
| 03 | | `test_host_name_lookup_fails` | resolving a public host name fails | 3 |
| 03 | | `test_proxy_is_unreachable_from_sandbox` | a connection to `litellm` port 4000 fails | 3 |
| 03 | | `test_sandbox_sees_no_secret_names` | the container's environment has none of the names in `env.example` | |

**Secrecy rules for stack tests.**
- `.env` values exist only inside the test process.
- An `assert` takes only a precomputed boolean, a status code or a name. No secret sits in an assertion expression, a test id, a parameter or a log line.
- Output of `docker compose config` and `docker inspect` is never echoed.
- A person pastes only the pytest summary.

## Slices

### 01 · The proxy, its database and the admin UI start from the env file and refuse callers without the master key
- Capability: With a filled-in `.env`, `docker compose up -d` starts `litellm`, pinned to the tag of the probe verdict, and `db`. The proxy has no model yet. A caller with no key or a wrong key gets 401, the master key is accepted, and the admin UI at `/ui` takes the login from `.env`. `.env` can no longer be committed, and `env.example` documents the five base secret names. The slice is the same under either verdict except for the image tag. The two container images are covered by the design's "New dependencies".
- Covers: Done when 5, 6
- Draft criteria:
  - `git check-ignore -v` names a rule in the committed `.gitignore` for `.env` and for `.env.local`, and `git check-ignore env.example` reports it as not ignored. (test)
  - `compose.yaml` has the top-level name `data-visualization-agent` and defines the services `litellm` and `db`. The test does not pin the full service set, so slice 03 can add `sandbox`. (test)
  - The named volume `litellm_pgdata` is declared, mounted by `db` at the data directory of fact-sheet row 13, and mounted by no other service. (test)
  - Across all services the only published port is `127.0.0.1:4000:4000`, on `litellm`. (test)
  - The `litellm` image is exactly `ghcr.io/berriai/litellm:<Tag>` with the `Tag:` of the newest probe verdict record, and the `db` image is exactly the Postgres tag of row 13. (test)
  - Every `${…}` interpolation in `compose.yaml` has the form `${NAME:?message}`, and no service has `env_file:` or an environment entry with a name and no value. (test)
  - No service mounts the repository root, `.env` or `/var/run/docker.sock`. (test)
  - `litellm` receives at least `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD` and `DATABASE_URL`, the last being `postgresql://litellm:${POSTGRES_PASSWORD:?…}@db:5432/litellm`; `db` receives `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm` and `POSTGRES_PASSWORD`. The test checks "at least", so slice 02 can add one key. (test)
  - `litellm` depends on `db` with `condition: service_healthy`, and `db` declares a health check that uses `pg_isready`. (test)
  - The names defined in `env.example` equal the names interpolated in `compose.yaml` and include the five base names. The test checks "include", so slice 02 can add the token. (test)
  - In `env.example` every name has a placeholder value and a comment line directly above it; the `LITELLM_MASTER_KEY` placeholder starts with `sk-`; the file states the character rule; the comment of `LITELLM_SALT_KEY` says it is generated once and never changed. (test)
  - The string `ANTHROPIC_API_KEY` occurs in none of `compose.yaml`, `litellm/config.yaml`, `env.example`. (test)
  - `./litellm/config.yaml` is mounted read-only at the path that `litellm`'s `command` passes to `--config`, and the file parses as YAML. (test)
  - `litellm/config.yaml` has no key whose name contains `forward`, `system`, `user-agent` or `user_agent`. Apart from the variable name `CLAUDE_CODE_OAUTH_TOKEN`, it contains none of `claude code`, `claude-code`, `claude_code`, `claude-cli` in any letter case. (test)
  - With `STACK_TESTS` unset, pytest run on `tests/stack/test_proxy.py` exits 0, runs no test, and reports as skipped the ten tests the stack-suite contract names for slice 01. (test)
  - With `STACK_TESTS` unset, `uv run --with pytest pytest` exits 0. (command)
- Edge cases:
  - Files: `decisions.md` has no probe verdict record or no rows 10 to 13 when the item starts. Stop with `BLOCKED`; the tag, the Postgres tag and the data directory are not guessed.
  - Files: a `.env` entry in the person's `.git/info/exclude` must not satisfy the first criterion. It asks for the rule in the committed `.gitignore`.
  - Files: `POSTGRES_PASSWORD` sits inside a URL, so the character rule applies to it.
  - Files: `ANTHROPIC_API_KEY` exported in the person's shell must not reach a container. The explicit mapping guarantees it; slice 02 observes it.
  - Live (person): the pinned release does not start with a config that defines no model. Report it as a block; no placeholder model is added.
  - Live (person): the schema is not applied on start-up (row 7 is unconfirmed for `v1.108.18`). Report it as a block; no migration step is added and the pin does not move.
  - Live (person): the proxy answers a keyless request with something other than 401 while no model exists. Report it as a block.
  - Live (person): the first `up` pulls images, so `stack_up` allows 15 minutes.
- Files expected to change: `.gitignore`, `compose.yaml`, `litellm/config.yaml`, `env.example`, `CLAUDE.md`, `tests/conftest.py`, `tests/test_proxy_files.py`, `tests/stack/conftest.py`, `tests/stack/test_proxy.py`
- Existing tests expected to change: none
- Dependencies to add: none
- Docs to update: `CLAUDE.md`
  - The Test line: tests exist; the stack suite runs only with `STACK_TESTS=1` and only a person runs it; the exit-5 tolerance in `.sdlc.json` no longer has an effect and only the user can remove it, on the base branch.
  - Traps: the example file is `env.example` because agents cannot read `.env.*`; `.env` is now git-ignored.
- Manual checks: none
- Type: feature · Size: M · Risk: high · UI: none · Human step:
  - **Before the build: the gate.** Best done before the spec pull request is merged, so both records merge with the spec.
    1. With the session, complete the fact sheet (rows 10 to 13). If the OAuth beta header's value contains a flag that names Claude Code, stop and ask the user before G2a: their ruling and ADR 0003 then disagree.
    2. Run G2a exactly as design.md writes it: a fresh token from `claude setup-token`, no `system` field, no user-agent override, no other header, no verbose or trace flag.
    3. Only if G2a returned 200, run G2b: one throwaway LiteLLM container on `v1.108.18`, published on `127.0.0.1` only, one alias, a throwaway master key, W1 then W2. For W2 use the variable name `CLAUDE_UPSTREAM_AUTHORIZATION`. If both fail for a LiteLLM-side reason, try both once more on `v1.111.0`. Remove the container afterwards.
    4. A 429, a 5xx or an error about the model is not a verdict. Repeat later or with another of the three model identifiers.
    5. Have the session record the verdict in `decisions.md` in the fixed format.
    6. Keep the token and the probe's files outside the repository. `.env` is not git-ignored yet.
  - **After the build, when the item pauses for you**, on a machine with Docker:
    1. Add `.env` to `.git/info/exclude`. The committed rule exists only on branches that contain this slice.
    2. Check out the item's branch, copy `env.example` to `.env` and fill it in: a master key starting with `sk-`, a salt key generated once, the UI user and password, the Postgres password.
    3. Run `docker compose up -d`, then `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`.
    4. Read the `litellm` logs: the schema was applied on start-up with no extra step.
    5. In a browser, `http://127.0.0.1:4000/ui` accepts the login from `.env` and refuses a wrong password (Done when 6).
    6. Run `docker compose down`, then `docker compose up -d`: the login still works and the volume `data-visualization-agent_litellm_pgdata` still exists.
    7. Merge the pull request only if all of that holds. Otherwise tell the session what failed; it becomes a fix round.
  - Never paste `.env` or the output of `docker compose config` or `docker inspect`.

### 02 · The proxy's Claude set-up matches the recorded result of the token test
- Capability: The proxy's Claude set-up is what the newest probe verdict record in `decisions.md` says.
  - "Build with Claude": a caller holding the master key gets a Claude reply from `opus`, `sonnet` and `haiku`. The proxy holds the subscription token and presents it with the wiring that passed the probe.
  - "No Claude": the proxy offers no Claude model and holds no token, and tests guard that state.
  - Either way no `ANTHROPIC_API_KEY` exists anywhere.
- Covers: Done when 4
- Draft criteria: (The first four are `command` criteria. Under "No Claude" they already hold when the slice starts, and a `test` criterion must fail before the build. The test author writes them as tests for the arm the record selects, and quotes the record's `Verdict`, `Tag` and `Wiring` lines and its date in the module docstring. The other arm is not written.)
  - Models match the verdict. Build: `litellm/config.yaml` defines exactly the aliases `opus`, `sonnet` and `haiku`, mapped to `anthropic/claude-opus-5-5`, `anthropic/claude-sonnet-5-5` and `anthropic/claude-haiku-5-5`. No Claude: it defines no model. (command)
  - The secret set matches the verdict. Build: the names in `env.example` are exactly the base five and `CLAUDE_CODE_OAUTH_TOKEN`, and the token's comment names `claude setup-token` and says the token expires. No Claude: the names are exactly the base five, and the file does not mention the token. (command)
  - The `litellm` environment matches the verdict and wiring. W1: exactly the base keys and `CLAUDE_CODE_OAUTH_TOKEN` as `${CLAUDE_CODE_OAUTH_TOKEN:?…}`. W2: exactly the base keys and `CLAUDE_UPSTREAM_AUTHORIZATION` as `Bearer ${CLAUDE_CODE_OAUTH_TOKEN:?…}`. No Claude: exactly the base keys. In every case no other service interpolates the token. (command)
  - The upstream wiring matches the verdict. W1: every deployment's credential, under the key name of row 12, is `os.environ/CLAUDE_CODE_OAUTH_TOKEN`, and no deployment carries a static header. W2: every deployment's static headers are exactly two, the authorization as `os.environ/CLAUDE_UPSTREAM_AUTHORIZATION` and the OAuth beta header with exactly the name and value of row 11. No Claude: the file holds no `os.environ/` reference. (command)
  - With `STACK_TESTS` unset, pytest run on `tests/stack/test_claude.py` exits 0, runs no test, and reports as skipped the four tests the stack-suite contract names for slice 02. (test)
  - With `STACK_TESTS` unset, `uv run --with pytest pytest` exits 0, slice 01's tests included and unchanged. (command)
- Edge cases:
  - Files: no probe verdict record in `decisions.md`. Stop with `BLOCKED`; the arm is never guessed.
  - Files: the recorded passing form needs anything beyond W1's one credential reference or W2's two headers (a third header, a value written into the file, custom code). Stop with `BLOCKED`; there is no third wiring.
  - Files: the token's value never appears in a committed file. Only its name does.
  - Live (person), Build: an alias fails with an upstream authentication error, or an error saying the credential is only for Claude Code. Repeat the G2a request first: it separates an expired token from a block. If G2a now fails on a credential or client ground, report it; the outcome is a new verdict record and a replan. Never add an identity header, a user agent, a system prompt or an API key.
  - Live (person), Build: an alias the subscription plan does not cover fails at request time. Report it as a block; the alias is not deleted silently.
  - Live (person), No Claude: a leftover `CLAUDE_CODE_OAUTH_TOKEN` line in `.env` fails the token-presence check. Remove the line.
- Files expected to change: `tests/test_claude_setup.py`, `tests/stack/test_claude.py`; under "Build with Claude" also `env.example`, `compose.yaml`, `litellm/config.yaml`
- Existing tests expected to change: none
- Dependencies to add: none
- Docs to update: none
- Manual checks: none
- Type: feature · Size: S · Risk: high · UI: none · Human step: When the item pauses for you, on the item's branch:
  1. Build with Claude: add a fresh `CLAUDE_CODE_OAUTH_TOKEN` to `.env`. No Claude: make sure `.env` has no such line.
  2. Run `docker compose up -d`, then `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. Under "Build with Claude" this run is gate G3.
  3. Merge only if every test passes. Otherwise tell the session what failed, pasting only the pytest summary.

### 03 · The sandbox runs beside the proxy with no network and the workspace mounted, and the stack is documented
- Capability: `docker compose up -d` leaves `sandbox`, `litellm` and `db` running. Inside the sandbox, `/workspace` is the host's `workspace/` read-write, no outbound connection works and no secret is visible. A new contributor can bring the stack up from the README, which also states the salt-key rule and, where Claude is configured, the terms risk.
- Covers: Done when 1, 2, 3
- Draft criteria:
  - `sandbox` builds from the context `./sandbox`, has `network_mode: none` and `init: true`, and has none of the keys `ports`, `networks`, `environment`, `env_file`, `user`, `container_name`, `deploy`, `mem_limit`, `cpus`, `cap_drop`, `read_only`. (test)
  - `sandbox` mounts exactly one volume, `./workspace` at `/workspace`, read-write. (test)
  - `README.md` gives the set-up steps in order (copy `env.example` to `.env`, fill it in, `docker compose up -d`), names `env.example` and never `.env.example`, and gives `http://127.0.0.1:4000` and `http://127.0.0.1:4000/ui`. (test)
  - `README.md` names `LITELLM_SALT_KEY` and says it is generated once, never changed, and cannot be rotated in place. (test)
  - `README.md` says what the volume `litellm_pgdata` holds and that `docker compose down -v` deletes it, states the Linux write limitation of the workspace mount, and gives the command `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. (test)
  - `README.md` matches the verdict.
    - Build: the token comes from `claude setup-token`, expires and is not refreshed. It names the aliases `opus`, `sonnet`, `haiku`. It carries the terms note: this use of the subscription login is outside what Anthropic's terms describe; it is for the owner's personal use; the stack stays local and is not shared or deployed; Anthropic may reject the requests at any time; there is no API-key fallback; changing the LiteLLM tag means running the probe of ADR 0007 again.
    - No Claude: the proxy has no Claude model and holds no token, with ADR 0003 and ADR 0007 cited; there is no API-key fallback; the reader is not told to set `CLAUDE_CODE_OAUTH_TOKEN`. (test)
  - With `STACK_TESTS` unset, pytest run on `tests/stack/test_sandbox.py` exits 0, runs no test, and reports as skipped the eight tests the stack-suite contract names for slice 03. (test)
  - With `STACK_TESTS` unset, `uv run --with pytest pytest` exits 0, the tests of slices 01 and 02 included and unchanged. (command)
- Edge cases:
  - Files: the README cites ADR paths, not `decisions.md`, because the epic folder moves to the archive at close.
  - Files: no probe verdict record. Stop with `BLOCKED`; the README arm is not guessed.
  - Files: slice 01's whole-stack tests (single port, no forbidden mount, no `env_file`) must keep passing with `sandbox` added.
  - Live (person): the image has no `curl`. The outbound check runs through Python and connects to an IP address, so it does not rest on DNS alone, and it times out within a few seconds.
  - Live (person): the file created for Done when 2 is deleted even on failure, so `git status` stays clean.
  - Live (person): on a Linux host where the owner of `workspace/` has another user id than `sandboxuser`, the write may fail. That is the documented limitation of ADR 0006, not something to fix with `user:`.
  - Live (person): without `git-lfs` the parquet is a small pointer file but is still listed.
  - Live (person): the image build fails on Python 3.15 (a package with no wheel). Report it as a block; `sandbox/Dockerfile` is not edited.
  - Live (person): two checkouts on one host share one stack (ADR 0002).
- Files expected to change: `compose.yaml`, `README.md`, `CLAUDE.md`, `tests/test_sandbox_files.py`, `tests/test_readme.py`, `tests/stack/test_sandbox.py`
- Existing tests expected to change: none
- Dependencies to add: none
- Docs to update: `README.md` (everything the criteria name) and `CLAUDE.md` (the stack commands). `docs/architecture.md` is not touched here; ship applies the design's change.
- Manual checks: none
- Type: feature · Size: M · Risk: medium · UI: none · Human step: When the item pauses for you, on the item's branch, with pull request #3 (`sandbox/Dockerfile`) already merged:
  1. Run `docker compose up -d`. The first run builds the sandbox image and can take minutes.
  2. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. This runs the tests of all three slices, so all six Done-when checks are observed on the finished stack.
  3. Run `docker compose down`: it returns within a few seconds and leaves no container of the project.
  4. Check that `git status` is clean after the suite.
  5. Follow the README from a state with no `.env`: no step is missing.
  6. Merge only if all of that holds. Otherwise tell the session what failed.

## Test strategy

- **Static tests** are the pipeline's evidence.
  - The default suite is `uv run --with pytest pytest`. The test author writes these tests and they are locked.
  - They read `compose.yaml`, `litellm/config.yaml`, `env.example`, `.gitignore` and `README.md` as files, call `git check-ignore`, and run pytest in a subprocess to prove the stack tests exist under their contract names and are skipped by default.
  - They prove the files say the right thing. They do not prove the stack runs.
- **Stack suite** (`tests/stack/`, `STACK_TESTS=1`) is a person's evidence.
  - The implementer writes it to the stack-suite contract, and it is not locked, so a fault found on the first real run is fixed in a normal fix round.
  - A person runs it at each item's pause, on the item's branch. The run in slice 03 covers all six Done-when checks.
  - Agents never run it: the command does not match their allowed commands, and they cannot read `.env`.
- **Person only**: the probe (G2a, G2b), the browser login, persistence across `down` and `up`, the schema on first start, prompt shutdown, the README walk-through.
- **At ship**: `docs/architecture.md` is updated from the design. The ship stage also has the Done-when checks observed, which needs Docker (see Risks).
- No unit tests of Python code: the epic adds none outside `tests/`. No CI workflow exists and an item cannot add one.

## Risks

- **The verdict may be "No Claude" after one request.** From the planner's memory, unchecked: Anthropic's API has been reported to accept subscription tokens only from requests that identify as Claude Code. Slice 02 then ships guards only, and the epic delivers a proxy with no model.
- **The OAuth beta header may itself name Claude Code.** From the planner's memory, unchecked: Claude Code's own beta header carries a `claude-code-…` flag beside the OAuth flag. If the value LiteLLM adds (row 11) contains one, the user's "treat as protocol" ruling and ADR 0003's ban on such flags disagree. Only the user can settle that, before G2a.
- **Unverified LiteLLM behaviour the slices rest on.**
  - The proxy starts with a config that defines no model. Slice 01 needs this under either verdict.
  - Authentication is checked before model lookup, so a keyless request gets 401 with no model.
  - The config key names for W1 and W2, and `os.environ/` references inside header values.
  - The schema on start-up for `v1.108.18` (row 7).
  - What the salt key protects.
- **The cut changed from two slices to three.** The old slice 01 with the salt key, both verdict arms and the header rules is estimated at 450 to 500 changed lines. ADR 0007 and design.md still say the verdict decides "whether slice 01 configures Claude"; under this plan that is slice 02. The gate stays before slice 01, because the tag and the Postgres facts come from it.
- **Slice 01 is still the largest**, estimated at 330 to 370 changed lines, most of it tests.
- **Live behaviour is not pipeline evidence.** A green pull request proves only the files. All six Done-when checks depend on a person running the stack suite and reporting honestly.
- **Ship may stall.** At ship an agent observes the Done-when checks and must report what it cannot run as failed. Without Docker it can observe none of the six. The user will have to decide at ship how that observation is made.
- **Slice 02's first four criteria are `command` criteria**, so the lock does not prove their tests fail first. The reviewer should check them against the verdict record line by line.
- **The stack tests are written by an agent that cannot run them.** Expect at least one fix round after the first run. Later slices may not change `tests/stack/conftest.py`; a fault found there later needs a replan or a declared change.
- **`.env` is ignored only on branches that contain slice 01.** On `main` it shows as untracked until the epic merges. The `.git/info/exclude` step is the guard.
- **The exit-5 tolerance stays in `.sdlc.json`**, because an item cannot change that file. `CLAUDE.md` will say so.
- **The probe result holds for one tag on one day.** Anthropic may reject the requests after the epic ships, and an expired token looks the same. G2a is the first diagnostic.
- **Terms.** Using the subscription token through the proxy is outside what Anthropic's terms describe. The user accepted the risk to their own account. The README must say the stack stays local and unshared.
- **Stack tests spend subscription quota and can leak secrets if written carelessly.** The secrecy rules are the guard; the reviewer of slices 01 and 02 should check them line by line.
- **PyYAML is present only transitively.** An upgrade of `langchain-core` that drops it would break the static suite.
- **Slice 03 needs pull request #3 merged**, and the sandbox image may not build: Python 3.15 is new, `scipy` or `pandas` may lack wheels, and the brief forbids editing the image.
- **The subscription plan may not cover all three models.** An alias then fails at request time and blocks slice 02.
