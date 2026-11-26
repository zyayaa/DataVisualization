---
id: 001/02
title: The sandbox runs beside the proxy with no network and the workspace mounted, and the stack is documented
type: feature         # feature | bug | task | skeleton
size: M               # XS | S | M ; L must be split
risk: medium          # low | medium | high ; high pauses for your approval
ui: none              # none | web | cli
hitl: true            # true if a person must do part of it; pauses for you
---
## Context
This item adds the `sandbox` service to the `compose.yaml` from item 01, so one `docker compose up -d` leaves `sandbox`, `litellm` and `db` running. In a later epic the sandbox will run code an LLM generates. So it has:
- no network at all (`network_mode: none`, ADR 0001);
- no secrets (ADR 0005);
- one read-write mount, `workspace/` at `/workspace`;
- the image's own user, `sandboxuser` (ADR 0006).

A later epic finds it by its Compose labels, not by container name (ADR 0002). The image is `sandbox/Dockerfile`, already committed and never edited by this item.

The item also writes the README set-up steps and applies design.md's "Change to the architecture document" to `docs/architecture.md`, because the stack is complete only here. Agents cannot run `docker`, so Done when 1 to 3 are opt-in stack tests under `tests/stack/`, which a person runs with `STACK_TESTS=1`.

## Acceptance criteria
- AC1: Given `compose.yaml` When the `sandbox` service is read Then its build context is `./sandbox`  — check: test
- AC2: Given `compose.yaml` When the `sandbox` service is read Then it has `network_mode: none`  — check: test
- AC3: Given `compose.yaml` When the `sandbox` service is read Then it has `init: true`  — check: test
- AC4: Given `compose.yaml` When the `sandbox` service is read Then it has none of the keys `ports`, `networks`, `environment`, `env_file`, `user`, `container_name`, `deploy`, `mem_limit`, `cpus`, `cap_drop` or `read_only`  — check: test
- AC5: Given `compose.yaml` When the volumes of `sandbox` are read Then it mounts exactly one, `./workspace` at `/workspace`, read-write  — check: test
- AC6: Given `compose.yaml` with `sandbox` added When the `ports` of every service are collected Then the only published port is still `127.0.0.1:4000:4000`  — check: test
- AC7: Given `compose.yaml` with `sandbox` added When the volumes of every service are read Then none mounts the repository root, `.env` or `/var/run/docker.sock`  — check: test
- AC8: Given `README.md` When it is read Then it gives the set-up steps in this order: copy `env.example` to `.env`, fill it in, run `docker compose up -d`  — check: test
- AC9: Given `README.md` When it is read Then it names `env.example` and never `.env.example`  — check: test
- AC10: Given `README.md` When it is read Then it gives the proxy address `http://127.0.0.1:4000` and the UI address `http://127.0.0.1:4000/ui`  — check: test
- AC11: Given `docs/architecture.md` When it is read Then it lists `compose.yaml` and the services `sandbox`, `litellm` and `db`  — check: test
- AC12: Given `docs/architecture.md` When it is read Then it lists ADR 0001 to 0006  — check: test
- AC13: Given `docs/architecture.md` When it is read Then it no longer says that `docs/adr/` does not exist or that no tests exist  — check: test
- AC14: Given `STACK_TESTS` is not set When `uv run --with pytest pytest` runs Then it exits 0  — check: command
- AC15: Given a filled-in `.env` When `docker compose up -d` has run from the repository root Then the `sandbox`, `litellm` and `db` containers are all running (stack test, run by a person; Done when 1)  — check: test
- AC16: Given the stack is up When containers are listed by the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox` Then exactly one container matches (stack test, run by a person)  — check: test
- AC17: Given the stack is up When `ls /workspace` runs in the sandbox Then the output lists `consumo_horario_mobilidade_eletrica_01_a_10.parquet` (stack test, run by a person; Done when 2)  — check: test
- AC18: Given the stack is up When the sandbox's default user creates a uniquely named file in `/workspace` Then that file exists in `workspace/` on the host (stack test, run by a person; Done when 2)  — check: test
- AC19: Given the stack is up When Python inside the sandbox opens a TCP connection to a public IP address with a short timeout Then the connection fails (stack test, run by a person; Done when 3)  — check: test
- AC20: Given the stack is up When Python inside the sandbox resolves a public host name Then the lookup fails (stack test, run by a person; Done when 3)  — check: test
- AC21: Given the stack is up When Python inside the sandbox opens a TCP connection to `litellm` on port 4000 Then the connection fails (stack test, run by a person; Done when 3)  — check: test
- AC22: Given the stack is up When Docker reports the sandbox container's environment Then it contains none of the names defined in `env.example` (stack test, run by a person)  — check: test

## Edge cases
- The image has no `curl`. The outbound check runs through Python and connects to an IP address, so it does not depend on DNS alone.
- The connection attempts must time out within a few seconds and must not hang the suite.
- The file created for AC18 must be deleted even when the test fails, so `git status` stays clean.
- On a Linux host where the owner of `workspace/` has a different user id from `sandboxuser`, the write may fail. That is a documented limitation (ADR 0006), not something to fix with `user:`.
- Without `git-lfs`, the parquet file is a small pointer file, but it is still listed (AC17).
- The first `up` builds the image and can take minutes, so the stack fixture's timeout allows for it.
- If the image build fails on Python 3.15 (a package with no wheel), stop and report. `sandbox/Dockerfile` is not edited.
- `docker compose down` stops the idle container promptly because of `init: true`.
- Two checkouts of the repository on one host share one stack (ADR 0002).

## Out of scope
- Any edit to `sandbox/Dockerfile`, including adding a parquet engine.
- Resource limits, capability drops, a read-only root filesystem or user remapping for the sandbox.
- Wiring `main.py` to the sandbox or to the proxy.
- Any change to the `litellm` or `db` services beyond what adding `sandbox` requires (item 01 owns them).
- Any change to `.claude/settings.json` or to `allowed_bash` in `.sdlc.json`.

## Technical notes
Interfaces/contracts:
- `sandbox` service: `build: ./sandbox`, `network_mode: none`, `init: true`, `volumes: ["./workspace:/workspace"]`. No other keys.
- The host reaches the sandbox only through Docker Engine exec, finding it by the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. The defaults come from the image: user `sandboxuser`, working directory `/workspace`.
- Item 01 provides, and this item reuses unchanged:
  - `tests/conftest.py`: `REPO_ROOT`, `load_compose()`, `interpolated_names()`, `example_env_names()`, and the `stack` skip unless `STACK_TESTS=1`.
  - `tests/stack/conftest.py`: `PROXY_URL`, `PROJECT`, `docker_compose(*args, timeout=...)`, and the `secrets` and `stack_up` fixtures.
  - The signatures are in item 01's Technical notes.
- Item 01's static tests iterate over all services without pinning the service set, so adding `sandbox` keeps them passing.

Files expected to change: `compose.yaml`, `tests/test_sandbox_stack_files.py`, `tests/test_docs.py`, `tests/stack/test_sandbox.py`, `README.md`, `docs/architecture.md`, `CLAUDE.md`
Existing tests expected to change: none. Item 01's tests in `tests/test_proxy_stack_files.py` and `tests/stack/test_proxy.py` keep passing unchanged, and `tests/conftest.py` and `tests/stack/conftest.py` are reused as they are.
Dependencies to add: none
Docs to update:
- `README.md`:
  - the set-up steps;
  - where the token comes from (`claude setup-token`), and that it expires and is not refreshed;
  - the aliases `opus`, `sonnet`, `haiku` and the addresses;
  - what LiteLLM stores in the `litellm_pgdata` volume, and that `docker compose down -v` deletes it;
  - the Linux write limitation (ADR 0006);
  - how a person runs the stack suite.
- `docs/architecture.md`: every change listed under "Change to the architecture document" in design.md, plus the "Tests and checks" section.
- `CLAUDE.md`:
  - the stack commands;
  - the trap that the example file is `env.example` because `.env.*` is unreadable to agents.

## Manual checks
- `docker compose down` returns within a few seconds and leaves no container of the project.
- `git status` is clean after the stack suite has run.
- Following the README from a checkout with no `.env` brings the stack up with no step missing.

## Human step
After the build, on macOS with Docker Desktop and the `.env` from item 01:
1. Run `docker compose up -d`.
2. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. This reruns item 01's proxy tests together with the sandbox tests, so all six Done-when checks are observed on the finished stack.
3. Do the manual checks.
4. Report the pytest summary.

Never paste `.env` or the output of `docker compose config`.
