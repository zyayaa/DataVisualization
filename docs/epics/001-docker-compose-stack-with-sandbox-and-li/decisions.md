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
