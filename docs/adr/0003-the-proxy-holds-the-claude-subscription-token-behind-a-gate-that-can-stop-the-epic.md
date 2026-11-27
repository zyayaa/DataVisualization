---
id: 0003
title: The proxy holds the Claude subscription token, behind a gate that can stop the epic
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
The brief requires upstream authentication with the user's Claude subscription (OAuth) token, not an API key. Done-when 4 requires that a caller holding only the master key gets a Claude reply. Brief assumption 5 says that if Anthropic blocks or forbids this use, the epic stops and does not quietly switch to an API key.

Two things are now known from primary sources (`decisions.md`, 2026-11-26):
- Anthropic's legal page says OAuth "is designed to support ordinary use of Claude Code and other native Anthropic applications", and that "developers may not collect, store, or intermediate Claude.ai credentials or session tokens".
- LiteLLM documents no way for the proxy to hold a subscription token. Its only documented flow has Claude Code, as the client, send its own token in `Authorization`; LiteLLM forwards it to `anthropic/` deployments and adds the OAuth beta header. Every documented step assumes Claude Code is the client.

With the legal page in front of them, the user answered: "I still want to use the SSO directly in litellm. This is for my own usage". The user accepts the risk to their own account. The user then changed the brief: if Anthropic blocks the requests, Claude is not configured in LiteLLM and the rest of the stack still ships (`decisions.md`). The user also ruled that the OAuth beta header counts as protocol.

This epic's caller is not Claude Code and must not pose as it. So neither the proxy-held route nor the documented forwarding route is covered by documentation for this caller.
## Decision
The proxy holds the token.
- It is stored in `.env` as `CLAUDE_CODE_OAUTH_TOKEN`, passed to the `litellm` container by name, and referenced from `litellm/config.yaml` with `os.environ/` as the upstream credential of the three Anthropic deployments.
- The caller sends only the master key and never an Anthropic credential.
- The proxy forwards no client headers upstream.
- No `ANTHROPIC_API_KEY` is defined anywhere, and the token is never placed in a variable of that name.
- The exact wiring is the one that passes the probe of ADR 0007. No custom code, callback or patched image is added to make it work.

The proxy never presents Claude Code's identity.
- Allowed upstream: the bearer authorization carrying the token, the API version header, the OAuth beta header that LiteLLM's documented flow itself adds, and LiteLLM's own default user agent.
- Forbidden: a system prompt that names Claude Code, Claude Code's user agent, any header or beta flag that names Claude Code or its client application, and any session or device identifier of Claude Code.
- A header that fits neither list is forbidden until the user rules on it.

A gate decides whether the epic is built:
- **G1, terms:** answered by the user, as quoted above.
- **G2, capability:** the live probe of ADR 0007, run before anything is built.
- **G3, live:** on the built stack, each alias returns a Claude reply (Done-when 4).

If Anthropic rejects the requests, or if they pass only when the proxy presents Claude Code's identity, LiteLLM is configured with no Claude model and no token, and the rest of the stack ships. The same holds if the pinned release cannot present the token from config (brief assumption 10). Posing as the client to get past a block counts as blocked. There is no API-key fallback and no other Claude provider.
## Alternative rejected
LiteLLM's documented per-request forwarding: the host caller sends the subscription token itself, and the proxy relays it. It is the only route LiteLLM documents, and the proxy would store no token. It lost for four reasons.
- It changes the brief. Done-when 4 would no longer hold as written, because the master key alone would not get a reply. Done-when 5 would need redefining, because `Authorization` would carry the token and the master key would move to another header.
- Its documentation assumes Claude Code is the client. For this epic's caller it is as undocumented as the chosen route.
- It does not help with the question that can cancel the epic: whether Anthropic accepts the token from a client that is not Claude Code.
- It hands the later wiring epic a non-standard client contract with two credentials, and it turns on client-header forwarding, which the stack otherwise forbids.

It stays available as a possible later epic, and a brief change, if the probe shows Anthropic accepts the token and LiteLLM cannot present it from config. That is the user's decision.
## Consequences
- Done-when 4 is read as: the token sits in LiteLLM's credential field under the name `CLAUDE_CODE_OAUTH_TOKEN`, which is not an `ANTHROPIC_API_KEY`.
- The stack rests on behaviour LiteLLM does not document. It can break on any upgrade, so the image is pinned and a change of pin re-runs the probe.
- The token is at rest in `.env` and in the `litellm` container's environment, where anyone with Docker access on the host can read it. The legal page names storing and intermediating; the user accepted this for their own account.
- The acceptance covers the user's own use only. The stack stays bound to loopback and single-user. Sharing it, deploying it or giving it to another person needs a new decision.
- Anthropic may reject the requests at any time, also after the epic ships. The Claude aliases then fail until a new decision is made.
- The epic may ship a proxy with no Claude model. The sandbox, the database and the UI are delivered either way.
- The token expires and the stack does not refresh it. Proxy calls then fail with an upstream authentication error until the user pastes a new one and restarts `litellm`.
- Access to all three models depends on the user's subscription plan; an alias the plan does not cover fails at request time.
