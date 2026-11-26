# Decisions: Docker Compose stack with sandbox and LiteLLM proxy

<!-- Append-only. Newest entry last. One "## YYYY-MM-DD · kind" heading per entry; kind is one of replan, block-answer, follow-up, test-amendment, retro. -->

## 2026-11-26 · block-answer
Gate G1 (ADR 0003), terms: may the user's Claude subscription token be used through the LiteLLM proxy?
Answer from the user: "use the subscription token". The user made this call themselves. The session did not research or summarise Anthropic's terms first. G2 (capability) and G3 (live) still apply: if the token works only by making the proxy pose as Anthropic's own client, the epic still stops and reports back.

## 2026-11-26 · block-answer
The staged `sandbox/Dockerfile` blocked the design save. The user answered: "you can commit to the branch". It is committed unchanged on the spec branch, so it reaches main with the spec pull request instead of with an item (this refines brief assumption 8).

## 2026-11-26 · block-answer
`sdlc-spec-pr` refused the spec branch because it carried `sandbox/Dockerfile`. The user chose to split it out: the file was removed from the spec branch and added unchanged through its own pull request (#3), which must merge before epic 001 is implemented. This supersedes the earlier entry that committed it on the spec branch. The items still treat the Dockerfile as existing code.
