# Decisions: Docker Compose stack with sandbox and LiteLLM proxy

<!-- Append-only. Newest entry last. One "## YYYY-MM-DD · kind" heading per entry; kind is one of replan, block-answer, follow-up, test-amendment, retro. -->

## 2026-11-26 · block-answer
Gate G1 (ADR 0003), terms: may the user's Claude subscription token be used through the LiteLLM proxy?
Answer from the user: "use the subscription token". The user made this call themselves. The session did not research or summarise Anthropic's terms first. G2 (capability) and G3 (live) still apply: if the token works only by making the proxy pose as Anthropic's own client, the epic still stops and reports back.

## 2026-11-26 · block-answer
The staged `sandbox/Dockerfile` blocked the design save. The user answered: "you can commit to the branch". It is committed unchanged on the spec branch, so it reaches main with the spec pull request instead of with an item (this refines brief assumption 8).

## 2026-11-26 · block-answer
`sdlc-spec-pr` refused the spec branch because it carried `sandbox/Dockerfile`. The user chose to split it out: the file was removed from the spec branch and added unchanged through its own pull request (#3), which must merge before epic 001 is implemented. This supersedes the earlier entry that committed it on the spec branch. The items still treat the Dockerfile as existing code.

## 2026-11-26 · block-answer
Gate G1 asked again, now with the terms in front of the user. Anthropic's Claude Code legal and compliance page (https://code.claude.com/docs/en/legal-and-compliance) says OAuth authentication "is designed to support ordinary use of Claude Code and other native Anthropic applications". It also says "developers may not collect, store, or intermediate Claude.ai credentials or session tokens", and that developers building products "should use API key authentication".
Answer from the user: "I still want to use the SSO directly in litellm. This is for my own usage". The user accepts the risk to their own account. The no-impersonation rule of ADR 0003 and brief assumption 5 stands: the proxy never presents Claude Code's identity (system prompt, user agent, client headers) to get past a block. If Anthropic rejects the requests, the epic stops.

## 2026-11-26 · block-answer
Gate G2 fact sheet, drafted by the session from primary sources on 2026-11-26:
1. Image: `ghcr.io/berriai/litellm:v1.108.18`, the newest release on the 1.108.x LTS line. `v1.111.0` is GitHub's "Latest" but is not on the LTS line. (https://github.com/BerriAI/litellm/releases)
2. Server-side subscription token: **none documented.** LiteLLM's documented flow has Claude Code send its own OAuth token in `Authorization`, which LiteLLM forwards per request to `anthropic/` deployments and adds the OAuth beta header. (https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription)
3. Claude Code identity: every documented step assumes Claude Code is the client. The docs do not say whether a token held by the proxy is accepted.
4. Model ids: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`. (https://platform.claude.com/docs/en/about-claude/models/overview)
5. UI login: `UI_USERNAME` (default `admin`) and `UI_PASSWORD`. Master key: use an `sk-` prefix (the docs disagree on whether it is required). (https://docs.litellm.ai/docs/proxy/ui)
6. Further secret: `LITELLM_SALT_KEY`, required by the official compose example and not rotatable in place. (https://docs.litellm.ai/docs/proxy/docker_quick_start)
7. Schema on start-up: documented "from v1.109.0"; unconfirmed for 1.108.18. (https://docs.litellm.ai/docs/proxy/database_migrations)
8. Postgres major and data directory: not verified.
9. Readiness: `GET /health/readiness`, no auth, 503 when the database is unreachable. (https://docs.litellm.ai/docs/proxy/health)
Under ADR 0003 as written, row 2 stops the epic. The user chose to continue (entry above), so ADR 0003 goes back to the design stage.

## 2026-11-26 · block-answer
The architect's two questions for the user, after the design revision that introduced the live probe (ADR 0007):
1. Does the OAuth beta header count as protocol or identity? The user answered: "treat as protocol".
2. What happens if Anthropic blocks the requests? The user answered: "if Anthropic blocks the requests do not configure claude in litellm". When asked whether that means stopping the epic or shipping the rest, the user chose "Ship the rest without Claude".
The brief was changed and re-approved by the user ("yes, approve all including 10"): the goal and Done-when 4 are now conditional on the token test, assumption 5 is replaced by constraints, and new assumption 10 treats "LiteLLM cannot present the token" like a block.

## 2026-11-26 · block-answer
G2 fact sheet, continued (rows 10 to 13), drafted by the session from primary sources on 2026-11-26:
10. Messages endpoint: `POST https://api.anthropic.com/v1/messages`. The docs show the path `/v1/messages` (https://platform.claude.com/docs/en/api/messages). Version header `anthropic-version`. LiteLLM v1.108.18 sends `2023-06-01` (`litellm/llms/anthropic/common_utils.py`, `get_anthropic_headers`: `"anthropic-version": anthropic_version or "2023-06-01"`); the versions page lists `2026-10-21` as the newest (https://platform.claude.com/docs/en/api/versioning). G2a sends `2023-06-01`, as LiteLLM does.
11. OAuth headers that LiteLLM v1.108.18 sends when the credential starts with `sk-ant-oat` (`optionally_handle_anthropic_oauth` in `litellm/llms/anthropic/common_utils.py`; constants in `litellm/types/llms/anthropic.py`):
    - `authorization: Bearer <token>`;
    - `anthropic-beta: oauth-2025-04-20`, which contains no Claude Code flag;
    - `anthropic-dangerous-direct-browser-access: true`.
    LiteLLM sets no `user-agent` of its own in that code.
12. Config keys:
    - W1: `litellm_params.api_key`, which accepts `os.environ/NAME` (documented, https://docs.litellm.ai/docs/proxy/configs). The source detects the `sk-ant-oat` prefix; whether a configured key takes that code path is unverified.
    - W2: `litellm_params.extra_headers`, shown in a config example. Whether a header value accepts `os.environ/NAME` is unverified.
13. Postgres: `postgres:16`, with the data volume at `/var/lib/postgresql/data`, as in LiteLLM's official compose files (https://github.com/BerriAI/litellm/blob/f52f26d9c636038c6e3609cc7d17cf625d434c3e/docker/docker-compose.quickstart.yml). From major 18 the image mounts at `/var/lib/postgresql` instead (https://hub.docker.com/_/postgres), so the stack stays on 16.

## 2026-11-26 · block-answer
Question: is `anthropic-dangerous-direct-browser-access: true` protocol or identity? LiteLLM adds it in its OAuth path, it does not name Claude Code, and it was on neither list of ADR 0003. The user answered: "treat it as protocol".
The allowed upstream headers are therefore:
- the bearer authorization;
- `anthropic-version`;
- `anthropic-beta: oauth-2025-04-20`;
- `anthropic-dangerous-direct-browser-access: true`;
- the client's default user agent, provided it does not name Claude Code.

G2a sends exactly these headers. Under wiring W2, the static headers may include this third header, so item 02's "exactly two static headers" reads as "exactly these three" if W2 needs it.

## 2026-11-26 · block-answer
Probe verdict record (ADR 0007), the newest one for this epic:
```
G2a: 429 rate_limit_error
G2b: not run
Verdict: No Claude
Tag: v1.108.18
Wiring: none
```
G2a was run once by the user, with the headers of fact-sheet rows 10 and 11, against `claude-haiku-5-5`. It returned HTTP 429 with the body `{"type":"error","error":{"type":"rate_limit_error","message":"Error"}}`. Under ADR 0007 a 429 alone is not a verdict. The user decided instead, in their words: "do not configure claude for litellm. Let's just deploy litellm and I will investigate".
So item 01 pins `ghcr.io/berriai/litellm:v1.108.18`, item 02 builds the "No Claude" arm (no model, no token, guard tests only), and item 03 writes the README's "No Claude" arm.
Configuring Claude later needs a new verdict record and a replan, or a new epic, after the user's investigation.

## 2026-11-27 · block-answer
<!-- sdlc:entry block-answer 001/01 1 -->
Item 001/01 (pull request #5) stopped on a question from the reviewer:

> The reviewer says a locked test contradicts its criterion: tests/__pycache__/conftest.cpython-315-pytest-9.2.0.pyc: The locked test set, pinned by hash in lock.json, includes two bytecode files written by the test author (tests/__pycache__/conftest...pyc and test_proxy_files...pyc) that pytest regenerates. Should the test author amend the test? Answer yes to amend it, or say what should happen instead.

**Answer from the user:**

> yes

The locked test is to be amended: the test author runs next and a new lock is recorded.


## 2026-11-27 · test-amendment
<!-- sdlc:entry test-amendment 001/01 1 -->
Item 001/01 (pull request #5): a locked test was amended after the user agreed it contradicted its criterion. The lock at `978ba90` was replaced.

## 2026-11-27 · block-answer
<!-- sdlc:entry block-answer 001/02 1 -->
Item 001/02 (pull request #6) stopped on a question from the implementer:

> the implementer stopped without finishing; it may have reached its turn limit. Its last words: Skipped: the stack-suite tests have never run against a live stack. Their wording may need a fix after the person's first `STACK_TESTS=1` run.

**Answer from the user:**

> The No Claude verdict stands. The work is finished; the report only had an extra line after DONE. Continue.


## 2026-11-27 · follow-up
<!-- sdlc:entry follow-up 001/02 1 -->
From item 001/02 (pull request #6): The stack-suite tests have never run against a live stack. Their wording may need a fix after the person's first `STACK_TESTS=1` run.

## 2026-11-27 · retro
<!-- sdlc:entry retro ec6cd3c -->
Every item is merged into `epic/001-docker-compose-stack-with-sandbox-and-li`. What the verifier saw for each "Done when" check, at `ec6cd3c`:

- **D1** Running `docker compose up -d` from the repo root leaves both `sandbox` and `litellm` running.
  - pass: I ran `docker compose up -d` from the repo root. The sandbox, litellm and db containers were already running, so it reported them as Running and the db as Healthy. `docker compose ps` showed sandbox Up, litellm Up on 127.0.0.1:4000->4000, and db Up (healthy). I did not test a cold start from a stopped stack.
- **D2** `ls /workspace` inside the sandbox shows the parquet file, and a file the sandbox user creates in `/workspace` appears in `workspace/` on the host.
  - pass: `docker compose exec sandbox ls -l /workspace` listed consumo_horario_mobilidade_eletrica_01_a_10.parquet (55305706 bytes, the same size as on the host, so it is the real file and not an LFS pointer). `id` showed uid=1000(sandboxuser). As that user, `touch /workspace/obs_test.txt` succeeded, and the file appeared in the host `workspace/` folder. I then deleted it.
- **D3** An outbound network request made from inside the sandbox fails.
  - pass: In the sandbox I ran a Python urllib request to https://example.com with a 5-second timeout. It failed with 'Temporary failure in name resolution'. The compose file sets network_mode: none for the sandbox.
- **D4** The proxy's Claude set-up matches the recorded result of the token test, and no `ANTHROPIC_API_KEY` is set anywhere: if the test passed, a chat-completion request on `localhost` with the master key gets a Claude reply; if Anthropic blocked it, the proxy offers no Claude model and holds no subscription token.
  - pass: The recorded verdict in the epic's decisions.md is 'No Claude'. GET /v1/models with the master key returned {"data":[],"object":"list"}, so no Claude model is offered. A chat completion for model 'sonnet' with the master key returned 400 'Invalid model name'. The string ANTHROPIC appears nowhere in .env, env.example, compose.yaml or litellm/config.yaml, and the litellm container environment has no ANTHROPIC variable. The config is `model_list: []`. I did not read .env for any token value, only grepped it for the count of ANTHROPIC matches, which was 0.
- **D5** The same request without the master key, or with a wrong one, gets a 401.
  - pass: POST /v1/chat/completions on localhost:4000 with no Authorization header returned 401 'No api key passed in'. With 'Bearer sk-wrong' it returned 401 'Invalid API key provided'.
- **D6** The LiteLLM UI on `localhost` accepts a login with the admin credentials from `.env`.
  - pass: GET /ui/ returned 200. POST /v2/login with UI_USERNAME and UI_PASSWORD from .env returned a token and the redirect http://localhost:4000/ui?login=success. A form POST to /login returned 303 to /ui?login=success. The same form POST with a wrong password returned 401. I did not drive a real browser.

| Item | Fix rounds | Questions | Findings (80+) | Test amendments | Paused for you |
| --- | --- | --- | --- | --- | --- |
| 001/01 The proxy, its database and the admin UI start from the env file and refuse callers without the master key | 3 (review 3) | 1 | 12 (4) | 1 | yes |
| 001/02 The proxy's Claude set-up matches the recorded result of the token test | 0 | 1 | 1 (0) | 0 | yes |
| 001/03 The sandbox runs beside the proxy with no network and the workspace mounted, and the stack is documented | 0 | 0 | 1 (0) | 0 | yes |

| Measure | Value |
| --- | --- |
| Items | 3 |
| Items that needed rework | 1 (33%) |
| Fix rounds | 3 |
| Questions that stopped an item | 2 |
| Items you merged yourself | 3 |
| Review findings, of which at confidence 80 or more | 14, 4 |
| Test amendments | 1 |
| Items with no failed check on GitHub | 3 of 3 |
| Items from your review of the epic | 0 |
| Spec pull requests after the first | 0 |
| Worker time: test author, implementer, reviewer, verifier | 19 min, 13.2 min, 52 min, - |
