---
id: 001/03
title: The sandbox runs beside the proxy with no network and the workspace mounted, and the stack is documented
type: feature         # feature | bug | task | skeleton
size: M               # XS | S | M ; L must be split
risk: medium          # low | medium | high ; high pauses for your approval
ui: none              # none | web | cli
hitl: true            # true if a person must do part of it; pauses for you
---
## Context
This item adds the `sandbox` service to `compose.yaml`, so one `docker compose up -d` leaves `sandbox`, `litellm` and `db` running.

The sandbox will later run code an LLM generates, so it has:
- no network (`network_mode: none`, ADR 0001);
- no secrets (ADR 0005);
- one read-write mount, `workspace/` at `/workspace`;
- the image's own user, `sandboxuser` (ADR 0006).

A later epic finds it by its Compose labels (ADR 0002). The image is `sandbox/Dockerfile` from pull request #3, never edited here.

The item also writes the README:
- the set-up steps;
- the salt-key rule;
- the arm that matches the newest probe verdict record in `decisions.md`: the terms note when Claude is configured, or the statement that no Claude model is configured.

`docs/architecture.md` is not changed by this item. Ship applies the design's change, including the ADR list 0001 to 0007.

## Acceptance criteria
- AC1: Given `compose.yaml` When the `sandbox` service is read Then its build context is `./sandbox`  — check: test
- AC2: Given `compose.yaml` When the `sandbox` service is read Then it has `network_mode: none`  — check: test
- AC3: Given `compose.yaml` When the `sandbox` service is read Then it has `init: true`  — check: test
- AC4: Given `compose.yaml` When the `sandbox` service is read Then it has none of the keys `ports`, `networks`, `environment`, `env_file`, `user`, `container_name`, `deploy`, `mem_limit`, `cpus`, `cap_drop`, `read_only`  — check: test
- AC5: Given `compose.yaml` When the volumes of `sandbox` are read Then it mounts exactly one, `./workspace` at `/workspace`, read-write  — check: test
- AC6: Given `README.md` When it is read Then it gives the set-up steps in this order: copy `env.example` to `.env`, fill it in, run `docker compose up -d`  — check: test
- AC7: Given `README.md` When it is read Then it names `env.example` and never `.env.example`  — check: test
- AC8: Given `README.md` When it is read Then it gives `http://127.0.0.1:4000` and `http://127.0.0.1:4000/ui`  — check: test
- AC9: Given `README.md` When it is read Then it names `LITELLM_SALT_KEY` and says the key is generated once, never changed, and cannot be rotated in place  — check: test
- AC10: Given `README.md` When it is read Then it says what the volume `litellm_pgdata` holds and that `docker compose down -v` deletes it  — check: test
- AC11: Given `README.md` When it is read Then it states the Linux write limitation of the workspace mount (ADR 0006)  — check: test
- AC12: Given `README.md` When it is read Then it gives the command `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`  — check: test
- AC13: Given the newest verdict record When `README.md` is read Then it matches the verdict. Build with Claude: it says the token comes from `claude setup-token`, expires and is not refreshed; it names the aliases `opus`, `sonnet` and `haiku`; and it carries the terms note (this use of the subscription login is outside what Anthropic's terms describe; it is for the owner's personal use; the stack stays local and is not shared or deployed; Anthropic may reject the requests at any time; there is no API-key fallback; changing the LiteLLM tag means running the probe of ADR 0007 again). No Claude: it says the proxy has no Claude model and holds no token, cites ADR 0003 and ADR 0007, says there is no API-key fallback, and does not tell the reader to set `CLAUDE_CODE_OAUTH_TOKEN`  — check: test
- AC14: Given `STACK_TESTS` is not set When pytest runs `tests/stack/test_sandbox.py` Then it exits 0, runs no test, and reports these as skipped: `test_all_three_services_are_running`, `test_sandbox_is_found_by_compose_labels`, `test_workspace_lists_the_dataset`, `test_file_written_in_sandbox_appears_on_host`, `test_outbound_connection_to_public_ip_fails`, `test_host_name_lookup_fails`, `test_proxy_is_unreachable_from_sandbox`, `test_sandbox_sees_no_secret_names`  — check: test
- AC15: Given `STACK_TESTS` is not set When `uv run --with pytest pytest` runs Then it exits 0, with the tests of items 01 and 02 included and unchanged  — check: command

## Edge cases
- Files: the README cites ADR paths, not `decisions.md`, because the epic folder moves to the archive at close.
- Files: there is no probe verdict record in `decisions.md`. Stop with `BLOCKED`; the README arm is not guessed.
- Files: item 01's whole-stack tests (a single published port, no forbidden mount, no `env_file`) must keep passing with `sandbox` added.
- Live (person): the image has no `curl`. The outbound check runs through Python and connects to an IP address, so it does not rest on DNS alone, and it times out within a few seconds.
- Live (person): the file created for Done when 2 is deleted even on failure, so `git status` stays clean.
- Live (person): on a Linux host where the owner of `workspace/` has another user id than `sandboxuser`, the write may fail. That is the documented limitation of ADR 0006, not something to fix with `user:`.
- Live (person): without `git-lfs`, the parquet file is a small pointer file but is still listed.
- Live (person): the image build fails on Python 3.15 (a package with no wheel). Report it as a block; `sandbox/Dockerfile` is not edited.
- Live (person): two checkouts of the repository on one host share one stack (ADR 0002).

## Out of scope
- Any edit to `sandbox/Dockerfile`, including adding a parquet engine.
- Resource limits, capability drops, a read-only root filesystem or user remapping.
- Wiring `main.py` to the sandbox or the proxy.
- Any change to the `litellm` or `db` services.
- `docs/architecture.md`, `docs/adr/` and `.sdlc.json`.
- Any edit to the test files of items 01 and 02.

## Technical notes
Interfaces/contracts:
- The `sandbox` service: `build: ./sandbox`, `network_mode: none`, `init: true`, `volumes: ["./workspace:/workspace"]`, and no other key.
- The host reaches the sandbox only through Docker Engine exec. It finds the container by the labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. User `sandboxuser`, working directory `/workspace`.
- `tests/stack/test_sandbox.py` uses the item 01 fixtures `docker_compose`, `stack_up` and `container_env_names`. The names and assertions of its eight tests are in plan.md, "Stack-suite contract".

Files expected to change: `compose.yaml`, `README.md`, `CLAUDE.md`, `tests/test_sandbox_files.py`, `tests/test_readme.py`, `tests/stack/test_sandbox.py`
Existing tests expected to change: none
Dependencies to add: none
Docs to update:
- `README.md`: everything the criteria name.
- `CLAUDE.md`: the stack commands.

## Manual checks
none

## Human step
When the item pauses for you, you need the item's branch, a machine with Docker, the `.env` from the earlier items, and pull request #3 (`sandbox/Dockerfile`) already merged. Then:
1. Run `docker compose up -d`. The first run builds the sandbox image and can take minutes.
2. Run `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. This runs the tests of all three items, so all six Done-when checks are observed on the finished stack.
3. Run `docker compose down`. It should return within a few seconds and leave no container of the project.
4. Check that `git status` is clean after the suite.
5. Follow the README from a state with no `.env`, and check that no step is missing.
6. Merge only if all of that holds. Otherwise tell the session what failed.

Never paste `.env`, or the output of `docker compose config` or `docker inspect`.
