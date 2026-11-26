---
id: 001
title: "Docker Compose stack with sandbox and LiteLLM proxy"
ui: none              # none | web | cli
architecture: change    # none | change
source_issue:         # optional inbox issue number
---
**Goal:** One `docker compose up` starts the code sandbox and a LiteLLM proxy that reaches Claude through the user's Claude subscription login.

**Why now / problem:** The agent will need two things that don't exist yet: an isolated place to run the analysis code it generates, and a way to call Claude. The sandbox image exists (`sandbox/Dockerfile`), but nothing builds or runs it. No LLM provider is set up anywhere in the repo.

**In scope:**
- A compose file at the repo root with two services: `sandbox` and `litellm`
- The sandbox is built from the existing `sandbox/Dockerfile`, with `workspace/` mounted at `/workspace`
- The sandbox gets no network access
- LiteLLM is set up to send requests to Anthropic using the user's Claude subscription credentials
- The LiteLLM admin UI can be reached from the host
- The secret names it needs are documented (a committed example env file); the real values stay in `.env`

**Out of scope:**
- Containerising the agent (`main.py`): it keeps running on the host with `uv run`
- Wiring `main.py` or any Python code to the proxy or the sandbox
- Any configuration done inside the LiteLLM UI (teams, budgets, virtual keys)
- Anthropic API key, Bedrock or Vertex providers
- Changes to the sandbox image's contents (packages, user, base image)
- Production deployment, TLS, remote access

**Done when:** <!-- 3-6 checks, each observable -->
1. Running `docker compose up -d` from the repo root leaves both `sandbox` and `litellm` running.
2. `ls /workspace` inside the sandbox shows the parquet file, and a file the sandbox user creates in `/workspace` appears in `workspace/` on the host.
3. An outbound network request made from inside the sandbox fails.
4. A chat-completion request to the proxy on `localhost` with the master key gets a Claude reply, and no `ANTHROPIC_API_KEY` is set anywhere.
5. The same request without the master key, or with a wrong one, gets a 401.
6. The LiteLLM UI on `localhost` accepts a login with the admin credentials from `.env`.

**Constraints:**
- Upstream auth comes from the Claude subscription (OAuth) login, not a paid API key
- Secrets live only in `.env`, which is never committed (CLAUDE.md)
- The sandbox runs generated code and has no network at all
- The sandbox image is `sandbox/Dockerfile` as it is today (Python 3.15-slim, non-root `sandboxuser`)

**Assumptions:** <!-- what Claude assumed after the interview. Tick one to keep it, strike it through and tick it to reject it, or write "none". An unticked assumption fails sdlc-lint. -->
- [x] Workspace mount: `workspace/` is mounted read-write so the agent can save charts and outputs there later.
- [x] Local only: the proxy's port is bound to `127.0.0.1` and can't be reached from the LAN.
- [x] Database: if the LiteLLM UI login needs a database, the stack adds one as a third service, with its data in a named volume.
- [x] Models: the proxy exposes the current Claude models (Opus 5.5, Sonnet 5.5, Haiku 5.5) under short aliases.
- [x] Terms of service: Anthropic may block or forbid using a subscription token outside its own apps. If design finds that, the epic stops and reports back. It does not quietly switch to an API key.
- [x] Getting the token: the user generates the subscription token themselves (for example with `claude setup-token`) and pastes it into `.env`. The stack doesn't run the OAuth login flow.
- [x] Resource limits: the sandbox gets no CPU or memory limits in this epic.
- [x] Staged Dockerfile: the currently staged, uncommitted `sandbox/Dockerfile` is committed as part of this epic.
- [x] Compose version: Docker Compose v2 (`docker compose`) is the supported tool.
