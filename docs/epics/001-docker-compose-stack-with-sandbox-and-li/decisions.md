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
