---
id: 0007
title: The capability gate is a live probe with a direct control request, run before the build
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
ADR 0003 holds the subscription token in the proxy. Its capability check, G2, was to be settled from LiteLLM's documentation. The fact sheet shows the documentation cannot settle it: no server-side route is documented, and every documented step assumes Claude Code is the client.

Two questions are open, and they are separate:
- Does Anthropic accept the token from a client that does not identify as Claude Code?
- Can the pinned LiteLLM release present a token held in its config?

A request that succeeds through LiteLLM answers neither cleanly, because it does not show what LiteLLM sent upstream. The plan's risk list also records an unchecked recollection that Anthropic accepts subscription tokens only from requests that identify as Claude Code. If that is right, the probe ends at the first question, and LiteLLM gets no Claude model.
## Decision
G2 is a probe that a person runs before slice 01 is built. Its verdict decides whether slice 02 configures Claude; slices 01 and 03 are the same either way, apart from slice 01's image tag and slice 03's README. Its files and the token stay outside the repository.

- **G2a, control.** One request from the host straight to Anthropic's Messages API: bearer authorization with a fresh token, the API version header, the OAuth beta header exactly as LiteLLM adds it, one short user message to `claude-haiku-5-5`, no system prompt, no user-agent override, no other header.
- **G2b, proxy.** One throwaway LiteLLM container at the pinned tag, with one alias and a throwaway master key, and one chat-completion request. Two config-only wirings are tried in order: the token as the deployment's credential (W1), then static bearer and OAuth beta headers on the deployment (W2). If both fail for a LiteLLM-side reason, they may be tried once more on `v1.111.0`, the only other release the fact sheet names. Nothing else is tried.

Verdicts:
- G2a does not return 200 on a credential or client ground: **No Claude.** G2b is not run. No option can work without presenting Claude Code's identity. LiteLLM gets no Claude model and no token; the rest ships.
- G2a and G2b return 200: **Build with Claude**, with the wiring and the tag that passed.
- G2a returns 200 and no candidate passes G2b: **No Claude** (brief assumption 10). The report says the release cannot present the token, and that per-request forwarding is the remaining route, for a possible later epic that would change the brief.
- A 429, a 5xx or an error about the model is not a verdict.

The result goes into `decisions.md` as a `block-answer`: status codes, error types, the wiring and the tag. Never the token. No verbose or trace output is used, because it prints the authorization header.
## Alternative rejected
Build the whole stack first and let Done-when 4 reveal whether the token works. It needs no separate step and tests the real stack. It lost because it builds the Claude wiring of slice 02 before the one question that decides it is answered, and a late failure creates pressure to "just use an API key", which the brief forbids. It also cannot show that the proxy sent no identity: only a control request that bypasses the proxy can. The probe costs one direct request, one `docker run` and at most a handful of proxy requests.

A proxy probe without the control request was also considered. It is one step fewer, but a failure would not say whether Anthropic or LiteLLM refused, and a pass would not prove the no-impersonation rule.
## Consequences
- A single request can decide that the proxy ships with no Claude model.
- The probe is a human step. Agents cannot run `docker` or read the token.
- It spends a few requests of the user's subscription quota, and G2a is itself a use of the token outside Anthropic's own applications. That is the use the user accepted in G1, minus the proxy.
- The fact sheet must first gain what the probe needs and lacks: the Messages endpoint and version header, the exact OAuth beta header, and the config key names for W1 and W2 in the pinned release.
- The result holds for one tag on one day. A change of the LiteLLM pin re-runs G2a and G2b.
- If the pin moves to `v1.111.0`, the stack leaves the LTS line; the move is recorded in `decisions.md`.
- The probe is not in the repository, so no test guards it. G3 and the stack tests guard the built stack.
- G2a's request is the first diagnostic when proxy calls fail later: it separates an expired token or a change on Anthropic's side from a proxy fault.
