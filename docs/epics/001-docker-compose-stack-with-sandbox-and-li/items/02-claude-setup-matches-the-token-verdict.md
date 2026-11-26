---
id: 001/02
title: The proxy's Claude set-up matches the recorded result of the token test
type: feature         # feature | bug | task | skeleton
size: S               # XS | S | M ; L must be split
risk: high            # low | medium | high ; high pauses for your approval
ui: none              # none | web | cli
hitl: true            # true if a person must do part of it; pauses for you
---
## Context
This item delivers the brief's Done-when 4 under either outcome of the token test. The newest probe verdict record in `decisions.md` (its lines `Verdict`, `Tag` and `Wiring`) selects the arm; the arm is never guessed.

**Build with Claude**
- The proxy holds the subscription token and presents it with the wiring that passed the probe:
  - W1: the token is the deployment's credential;
  - W2: two static upstream headers, the bearer authorization and the OAuth beta header.
- A caller holding the master key gets a Claude reply from `opus`, `sonnet` and `haiku`.

**No Claude**
- The proxy offers no Claude model and holds no token.
- Tests guard that state.

**Either way**, no `ANTHROPIC_API_KEY` exists anywhere, and the proxy never presents Claude Code's identity (ADR 0003). The user ruled that the OAuth beta header is protocol, not identity (`decisions.md`).

AC1 to AC4 have the kind `command`, because under "No Claude" they already hold when the item starts. The test author:
- writes them as tests for the arm the record selects;
- quotes the record's `Verdict`, `Tag` and `Wiring` lines, and its date, in the module docstring;
- does not write the other arm.

## Acceptance criteria
- AC1: Given the newest verdict record When `litellm/config.yaml` is parsed Then its models match the verdict. Build with Claude: exactly the aliases `opus`, `sonnet` and `haiku`, mapped to `anthropic/claude-opus-5-5`, `anthropic/claude-sonnet-5-5` and `anthropic/claude-haiku-5-5`. No Claude: no model  — check: command
- AC2: Given the newest verdict record When the names in `env.example` are read Then they match the verdict. Build with Claude: exactly `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD` and `CLAUDE_CODE_OAUTH_TOKEN`, and the token's comment names `claude setup-token` and says the token expires. No Claude: exactly the first five, and the file does not mention the token  — check: command
- AC3: Given the newest verdict record When the `litellm` environment in `compose.yaml` is read Then it matches the verdict and wiring, and no other service interpolates the token. W1: exactly `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `DATABASE_URL`, and `CLAUDE_CODE_OAUTH_TOKEN` as `${CLAUDE_CODE_OAUTH_TOKEN:?...}`. W2: exactly the five base keys and `CLAUDE_UPSTREAM_AUTHORIZATION` as `Bearer ${CLAUDE_CODE_OAUTH_TOKEN:?...}`. No Claude: exactly the five base keys  — check: command
- AC4: Given the newest verdict record When the deployments in `litellm/config.yaml` are read Then the upstream wiring matches the verdict. W1: every deployment's credential, under the key name of fact-sheet row 12, is `os.environ/CLAUDE_CODE_OAUTH_TOKEN`, and no deployment carries a static header. W2: every deployment has exactly two static headers, the authorization as `os.environ/CLAUDE_UPSTREAM_AUTHORIZATION` and the OAuth beta header with exactly the name and value of fact-sheet row 11. No Claude: the file holds no `os.environ/` reference  — check: command
- AC5: Given `STACK_TESTS` is not set When pytest runs `tests/stack/test_claude.py` Then it exits 0, runs no test, and reports these as skipped: `test_claude_setup_matches_the_verdict`, `test_subscription_token_presence_matches_the_verdict`, `test_env_file_defines_no_anthropic_api_key`, `test_proxy_container_has_no_anthropic_api_key`  — check: test
- AC6: Given `STACK_TESTS` is not set When `uv run --with pytest pytest` runs Then it exits 0, with item 01's tests included and unchanged  — check: command

## Edge cases
- Files: there is no probe verdict record in `decisions.md`. Stop with `BLOCKED`; the arm is never guessed.
- Files: the recorded passing form needs anything beyond W1's one credential reference or W2's two headers (a third header, a value written into the file, custom code). Stop with `BLOCKED`; there is no third wiring.
- Files: the token's value never appears in a committed file. Only its name does.
- Live (person), Build with Claude: an alias fails with an upstream authentication error, or with an error saying the credential is only for Claude Code.
  - Repeat the G2a request first: it separates an expired token from a block.
  - If G2a now fails on a credential or client ground, report it. The outcome is a new verdict record and a replan.
  - Never add an identity header, a user agent, a system prompt or an API key.
- Live (person), Build with Claude: an alias the subscription plan does not cover fails at request time. Report it as a block; the alias is not deleted silently.
- Live (person), No Claude: a leftover `CLAUDE_CODE_OAUTH_TOKEN` line in `.env` fails the token-presence check. Remove the line.

## Out of scope
- Any change to the `db` service, the ports, the image tags or the UI variables: item 01 owns them.
- The sandbox and the README: item 03.
- Per-request forwarding of a caller's token: a possible later epic, and a brief change.
- Any API-key, Bedrock or Vertex provider, or any fallback to one.
- Any edit to `tests/conftest.py`, `tests/test_proxy_files.py`, `tests/stack/conftest.py` or `tests/stack/test_proxy.py`.

## Technical notes
Interfaces/contracts:
- The table "What the verdict builds" in plan.md fixes:
  - the `env.example` names;
  - the extra `litellm` keys;
  - the shape of `litellm/config.yaml` for each of the three outcomes: W1, W2 and No Claude.
- Model mapping: `opus` → `anthropic/claude-opus-5-5`, `sonnet` → `anthropic/claude-sonnet-5-5`, `haiku` → `anthropic/claude-haiku-5-5`.
- Allowed upstream: the bearer authorization, the API version header, the OAuth beta header, and LiteLLM's own default user agent.
- Forbidden: anything that names Claude Code, and any forwarding of client headers. No custom code, callback or patched image.
- The stack-suite tests in `tests/stack/test_claude.py` use the item 01 fixtures `docker_compose`, `secrets`, `stack_up`, `chat` and `container_env_names`. Their assertions:
  - `test_claude_setup_matches_the_verdict`. Build: each alias returns 200 with a non-empty assistant message. No Claude: none of the three returns 200.
  - `test_subscription_token_presence_matches_the_verdict`. W1: `litellm` has `CLAUDE_CODE_OAUTH_TOKEN`. W2: it has `CLAUDE_UPSTREAM_AUTHORIZATION`. No Claude: it has neither, and `.env` does not define the token.
  - `test_env_file_defines_no_anthropic_api_key`: `.env` has no such name.
  - `test_proxy_container_has_no_anthropic_api_key`: the `litellm` container has no such variable.

Files expected to change: `tests/test_claude_setup.py`, `tests/stack/test_claude.py`; under "Build with Claude" also `env.example`, `compose.yaml`, `litellm/config.yaml`
Existing tests expected to change: none
Dependencies to add: none
Docs to update: none

## Manual checks
none

## Human step
When the item pauses for you, on the item's branch:
1. Under "Build with Claude", add a fresh `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` to `.env`. Under "No Claude", make sure `.env` has no such line.
2. Run `docker compose up -d`, then `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`. Under "Build with Claude", this run is gate G3.
3. Merge only if every test passes. Otherwise tell the session what failed, pasting only the pytest summary.

Never paste `.env`, or the output of `docker compose config` or `docker inspect`.
