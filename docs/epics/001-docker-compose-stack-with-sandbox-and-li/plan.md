# Plan: Docker Compose stack with sandbox and LiteLLM proxy

## Interfaces and contracts

**Files of the stack.** `compose.yaml` (repo root), `litellm/config.yaml`, `env.example` (repo root), `.gitignore`, `sandbox/Dockerfile` (already committed, never edited by an item). `main.py`, `pyproject.toml` and `uv.lock` are not touched by any slice.

**`compose.yaml` (shape fixed by design.md; rules every slice keeps true).**
- Top-level `name: data-visualization-agent`.
- Services: `litellm` and `db` (slice 01), `sandbox` (slice 02). Named volume `litellm_pgdata`, mounted by `db` only.
- The only published port in the stack is `127.0.0.1:4000:4000`, on `litellm`.
- Secrets reach containers only through an explicit `environment:` mapping, each value of the form `${NAME:?set NAME in .env}`. No service uses `env_file:`. No variable is passed through by bare name.
- `litellm`: image pinned to one release tag; `command: ["--config", "/app/config.yaml"]`; `./litellm/config.yaml` mounted read-only at that path; `depends_on: db: condition: service_healthy`.
- `db`: Postgres pinned to a major version; `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm`; health check with `pg_isready`; no ports; volume mounted at the data directory of the pinned major.
- `sandbox`: `build: ./sandbox`, `network_mode: none`, `init: true`, one volume `./workspace:/workspace` (read-write). No `ports`, `networks`, `environment`, `env_file`, `user`, `container_name`, resource limits, capability drops or read-only root.
- No container mounts the repository root, `.env` or the Docker socket.
- The string `ANTHROPIC_API_KEY` appears in none of `compose.yaml`, `litellm/config.yaml`, `env.example`.

**Secret names (`env.example`; real values only in `.env`).**

| Name | Read by |
|---|---|
| `LITELLM_MASTER_KEY` | `litellm` |
| `CLAUDE_CODE_OAUTH_TOKEN` | `litellm` (the `environment:` mapping may rename it inside the container to what the proxy expects) |
| `UI_USERNAME`, `UI_PASSWORD` | `litellm` |
| `POSTGRES_PASSWORD` | `db`, and `litellm` inside `DATABASE_URL` |

- The set of names in `env.example` always equals the set of names interpolated in `compose.yaml`. If G2 finds a further secret the pinned release needs, it is added to both (ADR 0004).
- Every generated value uses letters, digits, `-` and `_` only; `env.example` says so.

**Host to proxy.**
- `POST http://127.0.0.1:4000/v1/chat/completions`, header `Authorization: Bearer <LITELLM_MASTER_KEY>`, body `{"model": "<alias>", "messages": [...]}`.
- Aliases: `opus`, `sonnet`, `haiku`.
- Missing or wrong key: HTTP 401.
- Admin UI: `http://127.0.0.1:4000/ui`, login with `UI_USERNAME` / `UI_PASSWORD`.
- The caller never sends an Anthropic credential.

**Host to sandbox (contract for a later epic; nothing is wired).**
- Docker Engine exec.
- The container is found by the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`.
- User `sandboxuser`, working directory `/workspace`.

**Subscription-token gate (ADR 0003).**
- G1 is answered ("use the subscription token", `decisions.md`).
- G2 is the human step that opens slice 01; nothing is built before it.
- G3 is the live stack test of slice 01 (Done when 4).
- Stop rule: if G2 finds no documented server-side route, or G2 or G3 work only when the proxy presents Anthropic's own client identity (system prompt, user agent, client headers), the epic stops and reports back. No API key, no workaround.

**G2 fact sheet.** The person hands this to the build, and the session records it in `decisions.md` as a `block-answer`. The implementer builds from it, not from memory.
1. LiteLLM image reference and the release tag to pin.
2. The documented `config.yaml` setting by which the proxy holds a subscription token server-side and sends it upstream with no API key, and the environment variable name the proxy expects, if any.
3. Whether that route makes the proxy present Claude Code's identity to Anthropic (yes means stop).
4. The three upstream model identifiers for Opus 5.5, Sonnet 5.5 and Haiku 5.5 from Anthropic's published model list.
5. Confirmation of the `UI_USERNAME` / `UI_PASSWORD` names and of the master-key format (`sk-` prefix or not).
6. Any further secret the release needs when a database is present.
7. Whether the image applies its database schema on start-up with no extra step.
8. The Postgres major to pin and its data directory.
9. The proxy's readiness endpoint.

**Test harness (shared by both slices).**
- Default suite: `uv run --with pytest pytest`. Static only: no Docker, no `.env`, no network. YAML is parsed with `yaml.safe_load` (PyYAML is already locked through `langchain-core`; nothing is added to `pyproject.toml`).
- Stack suite: everything under `tests/stack/`, marked `stack`, skipped unless the environment variable `STACK_TESTS=1` is set. A person runs it: `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`.
- The switch is an environment variable on purpose: agents' allowed commands do not cover it. Agents never run the stack suite and never read `.env`.
- Secrecy rules for stack tests:
  - `.env` values are read only inside the test process, through `dotenv_values`.
  - No secret value appears in an assertion expression, a test id, a parameter, a log line or captured output that pytest would print.
  - Output of `docker compose config` is never echoed, because it contains resolved secrets.
  - Assertions compare status codes, booleans and names.

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
def secrets() -> Mapping[str, str]                       # values of .env; never printed
@pytest.fixture(scope="session")
def stack_up(secrets) -> None                            # `docker compose up -d`, waits for readiness, leaves the stack running
def chat(alias: str, bearer: str | None) -> tuple[int, dict]  # status and parsed body of a chat-completion call
```

## Slices

### 01 · The proxy answers as Claude through the subscription token, and only for the master key
- Capability: With a filled-in `.env`, `docker compose up -d` starts `litellm` and `db`. A caller on the host holding the master key gets a Claude reply from the aliases `opus`, `sonnet` and `haiku`; a caller with no key or a wrong key gets 401; the admin UI at `/ui` accepts the login from `.env`. The secret names are documented in `env.example` and `.env` can no longer be committed.
- Covers: Done when 4, 5, 6
- Draft criteria:
  - `.env` and `.env.local` are ignored by git and `env.example` is not (`git check-ignore`). (test)
  - `compose.yaml` has the top-level name `data-visualization-agent`, the services `litellm` and `db`, and the named volume `litellm_pgdata` mounted by `db` only. The test does not pin the full service set, so slice 02 can add `sandbox`. (test)
  - Across all services the only published port is `127.0.0.1:4000:4000` on `litellm`; `db` publishes none. (test)
  - The `litellm` image tag is one release version (not absent, not `latest`, not a moving `main-*` tag) and the Postgres tag starts with a major version number. (test)
  - Every secret in `litellm` and `db` arrives through an `environment:` mapping value of the form `${NAME:?message}`; no service has `env_file:` or a bare pass-through variable; no service mounts the repository root, `.env` or the Docker socket. (test)
  - The names defined in `env.example` equal the names interpolated in `compose.yaml`; each has an obvious placeholder value and one comment line; the file states the character rule (letters, digits, `-`, `_`). (test)
  - The string `ANTHROPIC_API_KEY` is in none of `compose.yaml`, `litellm/config.yaml`, `env.example`. (test)
  - `litellm/config.yaml` defines exactly the aliases `opus`, `sonnet` and `haiku`, each mapped to an Anthropic model of the matching family; every credential value in it is an `os.environ/<NAME>` reference; the file is mounted read-only at the path the service's `command` names. (test)
  - `litellm/config.yaml` does not turn on forwarding of client headers to the upstream, and sets no system prompt, user-agent or client-identity header. (test)
  - `litellm` waits for `db` with `condition: service_healthy` and `db` declares a health check. (test)
  - The test check in `.sdlc.json` no longer tolerates exit code 5, and `uv run --with pytest pytest` exits 0 with the stack tests reported as skipped. (command)
  - Stack: with an empty env file and a scrubbed environment, `docker compose config` exits non-zero and its error names a missing variable. (test)
  - Stack: after `docker compose up -d`, `litellm` and `db` are running, `db` is healthy and the proxy answers its readiness endpoint within the timeout. (test)
  - Stack (G3, Done when 4): a chat completion with the master key returns 200 and a non-empty assistant message for each of `opus`, `sonnet`, `haiku`. (test)
  - Stack (Done when 4): `.env` defines no `ANTHROPIC_API_KEY` and the `litellm` container's environment, as Docker reports it, has no variable of that name. (test)
  - Stack (Done when 5): the same request with no `Authorization` header returns 401, and with a wrong bearer value returns 401. (test)
  - Stack (Done when 6): `GET /ui` on `127.0.0.1:4000` returns an HTML page, and Docker reports the published port bound to host address `127.0.0.1` only. (test)
- Edge cases:
  - G2 finds no server-side route, or only the client-forwarding route, or a route that needs Claude Code's identity: stop before building and report.
  - G3 returns an upstream authentication or "credential only authorised for Claude Code" error: stop and report; do not add identity headers or a system prompt.
  - An alias the user's plan does not cover fails at request time: report it as a block; do not delete the alias silently.
  - An expired token gives an upstream authentication error that looks like a regression; the test failure message says to check the token first.
  - `ANTHROPIC_API_KEY` exported in the person's shell must not reach any container.
  - The first `up` pulls images, so the readiness wait needs a generous timeout.
  - The Postgres data directory differs by major version; the volume path must match the pinned major.
  - A further secret required by the pinned release (for example a salt key) goes in both `env.example` and `compose.yaml`.
  - `POSTGRES_PASSWORD` sits inside a URL, so the character rule applies.
  - pytest prints compared values on failure, so no secret may sit in an assertion.
- Files expected to change: `.gitignore`, `compose.yaml`, `litellm/config.yaml`, `env.example`, `tests/conftest.py`, `tests/test_proxy_stack_files.py`, `tests/stack/conftest.py`, `tests/stack/test_proxy.py`, `.sdlc.json` (test check command only), `CLAUDE.md`
- Existing tests expected to change: none (there are no tests yet)
- Dependencies to add: none in Python. Container images, both covered by the design: the LiteLLM proxy image pinned to the release tag from the G2 fact sheet, and Postgres pinned to a major version.
- Docs to update: `CLAUDE.md` (the Test line: tests now exist, tolerance removed, how the stack suite is switched on and that agents do not run it)
- Manual checks:
  - In a browser, `http://127.0.0.1:4000/ui` accepts `UI_USERNAME` / `UI_PASSWORD` from `.env` and refuses a wrong password (Done when 6).
  - After `docker compose down` and `docker compose up -d`, the login still works and the volume `data-visualization-agent_litellm_pgdata` still exists.
  - The `litellm` logs show the schema applied on start-up with no extra step.
- Type: feature · Size: M · Risk: high · UI: none · Human step:
  - Before the build (gate G2): read the documentation of the LiteLLM release to be pinned and Anthropic's published model list, and fill in the G2 fact sheet from "Interfaces and contracts". If there is no documented way for the proxy to hold the subscription token server-side with no API key, or the way makes the proxy present Claude Code's identity, the epic stops here. The session records the answer in `decisions.md` as a `block-answer`.
  - After the build (gate G3 and Done when 4 to 6), on a machine with Docker:
    1. Copy `env.example` to `.env`.
    2. Fill it with real values, including a token from `claude setup-token`.
    3. Run `docker compose up -d`.
    4. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`.
    5. Do the manual checks.
    6. Report the pytest summary and the result of the browser login.
  - Never paste `.env` or the output of `docker compose config`.
  - If `.sdlc.json` cannot be edited from an item branch, make the one-line change to the test check by hand.

### 02 · The sandbox runs beside the proxy with no network and the workspace mounted, and the stack is documented
- Capability: `docker compose up -d` leaves `sandbox`, `litellm` and `db` running. Inside the sandbox, `/workspace` is the host's `workspace/` read-write, no outbound connection works, and no secret is visible. A new contributor can bring the stack up from the README, and the architecture document describes the stack as built.
- Covers: Done when 1, 2, 3
- Draft criteria:
  - `sandbox` builds from the context `./sandbox`, has `network_mode: none` and `init: true`, and has none of `ports`, `networks`, `environment`, `env_file`, `user`, `container_name`, resource limits, capability drops or read-only root. (test)
  - `sandbox` mounts exactly one volume, `./workspace` at `/workspace`, read-write. (test)
  - With `sandbox` added, the only published port in the stack is still `127.0.0.1:4000:4000`, and no service mounts the repository root, `.env` or the Docker socket. (test)
  - `README.md` gives the set-up steps in order (copy `env.example` to `.env`, fill it in, `docker compose up -d`), names `env.example` and never `.env.example`, and gives the proxy and UI address. (test)
  - `docs/architecture.md` lists `compose.yaml`, the services `sandbox`, `litellm` and `db`, and ADR 0001 to 0006, and no longer says that `docs/adr/` does not exist or that no tests exist. (test)
  - `uv run --with pytest pytest` exits 0 with the stack tests skipped. (command)
  - Stack (Done when 1): after `docker compose up -d` from the repository root, `sandbox`, `litellm` and `db` are all in the running state. (test)
  - Stack: exactly one container carries the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. (test)
  - Stack (Done when 2): `ls /workspace` in the sandbox lists `consumo_horario_mobilidade_eletrica_01_a_10.parquet`. (test)
  - Stack (Done when 2): a uniquely named file created in `/workspace` by the default user, who is `sandboxuser`, exists in `workspace/` on the host; the test removes it afterwards, also when it fails. (test)
  - Stack (Done when 3): from Python inside the sandbox, a TCP connection to a public IP address fails within a short timeout, a host-name lookup fails, and a connection to `litellm` on port 4000 fails. (test)
  - Stack: the sandbox's environment, as Docker reports it, contains none of the names in `env.example`. (test)
- Edge cases:
  - The image has no `curl`; the outbound check runs through Python and connects to an IP address so it does not rest on DNS alone.
  - The connection attempt must time out quickly and not hang the suite.
  - The file created for Done when 2 must be deleted even on failure, so `git status` stays clean.
  - On a Linux host whose owner of `workspace/` has a different user id from `sandboxuser`, the write may fail; this is a documented limitation (ADR 0006), not something to fix with `user:`.
  - Without `git-lfs` the parquet is a small pointer file but still listed.
  - The first `up` builds the image and can take minutes.
  - If the image build fails on Python 3.15 (a package with no wheel), stop and report; `sandbox/Dockerfile` is not edited.
  - `docker compose down` should stop the idle container promptly because of `init: true`.
  - Two checkouts on one host share one stack (ADR 0002).
- Files expected to change: `compose.yaml`, `tests/test_sandbox_stack_files.py`, `tests/test_docs.py`, `tests/stack/test_sandbox.py`, `README.md`, `docs/architecture.md`, `CLAUDE.md`
- Existing tests expected to change: none. The slice 01 tests iterate over all services and do not pin the service set, so they keep passing unchanged; `tests/conftest.py` and `tests/stack/conftest.py` are reused as they are.
- Dependencies to add: none
- Docs to update:
  - `README.md`: set-up steps; where the token comes from (`claude setup-token`) and that it expires and is not refreshed; aliases and addresses; what LiteLLM stores in the `litellm_pgdata` volume and that `down -v` deletes it; the Linux write limitation; how a person runs the stack suite.
  - `docs/architecture.md`: every change listed under "Change to the architecture document" in design.md, plus the "Tests and checks" section.
  - `CLAUDE.md`: the stack commands; the trap that the example file is `env.example` because `.env.*` is unreadable to agents.
- Manual checks:
  - `docker compose down` returns within a few seconds and leaves no container of the project.
  - `git status` is clean after the stack suite.
  - Following the README from a state with no `.env` brings the stack up with no step missing.
- Type: feature · Size: M · Risk: medium · UI: none · Human step: After the build, on macOS with Docker Desktop and the `.env` from slice 01:
  1. Run `docker compose up -d`.
  2. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. This runs the proxy tests of slice 01 again together with the sandbox tests, so all six Done-when checks are observed on the finished stack.
  3. Do the manual checks.
  4. Report the pytest summary.

## Test strategy

- **Static tests** (default suite, run by agents and by the `test` check): pytest reads `compose.yaml`, `litellm/config.yaml`, `env.example`, `.gitignore`, `README.md` and `docs/architecture.md` as files and asserts the rules of the design: isolation of `sandbox`, the single loopback port, explicit secret mapping, no `ANTHROPIC_API_KEY`, pinned images, aliases, example names matching interpolated names. Tooling: `uv run --with pytest pytest`, PyYAML as already locked, `git check-ignore` through `subprocess`. These tests prove the files say the right thing; they do not prove the stack runs.
- **Stack tests** (`tests/stack/`, `STACK_TESTS=1`, run by a person): pytest drives `docker compose` through `subprocess` and the proxy through the standard library's HTTP client, with `.env` values read by `python-dotenv`. They are the only automated proof of Done when 1 to 5 and of the reachability half of Done when 6. Agents cannot run them: `docker` is not in `allowed_bash` and `.env` is unreadable to them. Each slice's human step is where they run.
- **Manual**: the browser login (Done when 6), persistence across `down` / `up`, prompt shutdown, and a read-through of the README.
- No unit tests of Python code: the epic adds none outside `tests/`.
- No CI workflow exists and none is added.

## Risks

- **The gate may stop the epic at slice 01.** From the planner's memory, not checked against any source in this session: Anthropic's API has been reported to accept subscription tokens only from requests that identify as Claude Code, and the LiteLLM route for subscription log-ins that the planner recalls is the one where the client forwards its own credential, which the design rules out. If either holds for the pinned release, G2 or G3 fails under the stop rule and nothing ships but the report.
- **Nothing about LiteLLM is verified in the repository**: image name, release tag, credential setting, `UI_USERNAME` / `UI_PASSWORD`, master-key format, readiness endpoint, need for a further secret, schema applied on start-up. The plan rests on the G2 fact sheet; a wrong sheet makes slice 01's files wrong.
- **The model identifiers for Opus 5.5, Sonnet 5.5 and Haiku 5.5 are not known to the plan**; they come from the fact sheet. The user's plan may not cover all three.
- **A green default suite does not prove the stack works.** All six Done-when checks depend on a person running the stack suite and reporting honestly. A skipped human step leaves the epic unverified.
- **The stack tests are written by an agent that cannot run them.** Expect at least one fix round after the first human run.
- **Removing the exit-5 tolerance edits `.sdlc.json`.** If the workflow protects that file from item branches, a person makes the change, or it is deferred and `CLAUDE.md` keeps its note.
- **PyYAML is used by tests but only present transitively**; an upgrade of `langchain-core` that drops it would break the static suite.
- **The sandbox image may not build**: Python 3.15 is new and `scipy` or `pandas` may lack wheels for it, and the image has no compiler. The brief forbids editing the image, so that would be a block.
- **Slice 01 is close to the ceiling** (estimated 330 to 370 changed lines, most of it tests). If it runs over, the admin-UI criteria (Done when 6) are the part to move into their own slice by a replan.
- **Stack tests spend subscription quota and can leak secrets if written carelessly.** The secrecy rules in "Interfaces and contracts" are the guard; the reviewer of slice 01 should check them line by line.
