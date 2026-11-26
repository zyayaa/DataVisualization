---
id: 0003
title: The proxy holds the Claude subscription token, behind a gate that can stop the epic
status: proposed      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
The brief requires upstream authentication with the user's Claude subscription (OAuth) token, not an API key, and Done-when 4 requires that a caller holding only the master key gets a Claude reply. Brief assumption 5 says that if Anthropic blocks or forbids this use, the epic stops and does not quietly switch to an API key.

Two things could not be verified from the repository, and this design had no access to outside documentation:
- whether Anthropic's current terms allow a subscription token to be used by a third-party proxy;
- whether the LiteLLM release to be pinned can present such a token as its upstream credential, and whether Anthropic's API accepts it from a client that is not Anthropic's own.
## Decision
The token is stored in `.env` as `CLAUDE_CODE_OAUTH_TOKEN`, passed to the `litellm` container by name and referenced from `litellm/config.yaml` as `os.environ/CLAUDE_CODE_OAUTH_TOKEN`. The caller never sends it. No `ANTHROPIC_API_KEY` is defined anywhere.

A gate with three checks decides whether the epic is built:
- **G1, terms:** the current Anthropic terms and credential-use documentation are read, and the user decides. The answer is recorded in the epic's `decisions.md`.
- **G2, capability:** the pinned LiteLLM release documents a way to hold and present a subscription token server-side.
- **G3, live:** one request through the proxy gets a Claude reply (Done-when 4).

G1 and G2 are done before any other work item. If G1 fails, or if G2 or G3 can pass only by making the proxy pose as Anthropic's own client, the epic stops and reports back. Posing as the client to get past a block counts as blocked.
## Alternative rejected
Build the whole stack first and let Done-when 4 reveal whether the token works. It is less ceremony, but it spends the build before the one question that can cancel the epic is answered, and a late failure creates pressure to "just use an API key", which the brief forbids. It also treats a terms question as a technical one: a request that happens to succeed does not show the use is allowed.
## Consequences
- The epic may end at the gate with nothing shipped but the report.
- G1 needs the user; no agent can answer it.
- The token expires and the stack does not refresh it. When it does, proxy calls fail with an upstream authentication error until the user pastes a new one and restarts `litellm`.
- Access to all three models depends on the user's subscription plan; an alias the plan does not cover fails at request time.
- The exact credential wiring in `litellm/config.yaml` is set by what G2 finds, so it is not fixed in this record.
