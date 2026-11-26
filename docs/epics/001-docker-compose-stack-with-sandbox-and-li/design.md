# Design: Docker Compose stack with sandbox and LiteLLM proxy

Read for this round: `docs/epics/001-docker-compose-stack-with-sandbox-and-li/brief.md`, `decisions.md` (the last two entries being the re-answered G1 and the G2 fact sheet), `plan.md` and both items (context only), `docs/architecture.md`, ADR 0001 to 0006 (all `proposed`; none is accepted), `.gitignore`, `.sdlc.json`, `.claude/settings.json`, `main.py`, `README.md`, and `sandbox/Dockerfile` as it stands on branch `chore/sandbox-dockerfile` (pull request #3).

This design had no access to outside documentation. Every statement about LiteLLM or Anthropic below comes from the G2 fact sheet in `decisions.md` and cites its row. Anything else is marked **unverified**.

Five findings shape the design:

1. `.gitignore` contains only `.idea/`. `.env` is **not** ignored today, although CLAUDE.md says it must never be committed. This epic is the first to put real secrets in `.env`, so it must add the ignore rule before anything else.
2. `.claude/settings.json` denies `Read(./.env)` and `Read(./.env.*)`. A committed example file named `.env.example` matches the second rule, so the agents that build and review this epic could not read it. The example file is therefore named `env.example` (ADR 0005).
3. LiteLLM documents no way for the proxy to hold a subscription token server-side (fact sheet row 2). Its only documented subscription flow has Claude Code as the client, sending its own token (rows 2 and 3). This epic's caller is not Claude Code and must not pose as it. So **no documentation covers this epic's caller under any option**, and the capability question can only be settled by a live probe (ADR 0007).
4. Anthropic's legal page says OAuth "is designed to support ordinary use of Claude Code and other native Anthropic applications" and that "developers may not collect, store, or intermediate Claude.ai credentials or session tokens" (`decisions.md`). The user read this and chose to continue for their own account. Read literally, brief assumption 5 ("may block or forbid ... If design finds that, the epic stops") is already triggered by that page. The brief has since been changed and re-approved (`decisions.md`): assumption 5 is replaced by constraints, and if Anthropic blocks the requests, LiteLLM gets no Claude model while the rest of the stack ships. The option table below shows the brief as it stood when the options were weighed.
5. The fact sheet fixes details the earlier design left open: the image tag (row 1), the model identifiers (row 4), the UI variable names and master-key prefix (row 5), a sixth secret `LITELLM_SALT_KEY` (row 6) and the readiness endpoint (row 9). Rows 7 (schema on start-up for the pinned release) and 8 (Postgres major and data directory) are still unverified.

## How the subscription token is handled

Two options were weighed.

- **(a) Proxy-held.** The token is the upstream credential of the proxy's three Anthropic deployments. The caller sends only the master key. LiteLLM does not document this route.
- **(b) Caller-forwarded.** The host caller sends the token itself in `Authorization` on every request; LiteLLM forwards it to `anthropic/` deployments and adds the OAuth beta header (fact sheet row 2). Documented, but only with Claude Code as the client (row 3).

### What each option changes in the brief

| Brief text | (a) proxy-held | (b) caller-forwarded |
|---|---|---|
| In scope: "LiteLLM is set up to send requests to Anthropic using the user's Claude subscription credentials" | Unchanged. | Weakened: LiteLLM holds no credential and only relays the caller's. |
| Done-when 4: "with the master key gets a Claude reply, and no `ANTHROPIC_API_KEY` is set anywhere" | Unchanged. One reading is stated openly: the token sits in the credential field of LiteLLM's config through a variable named `CLAUDE_CODE_OAUTH_TOKEN`; that is not an `ANTHROPIC_API_KEY`. The token is never put in a variable of that name, not even inside the container. | **Changed.** The master key alone no longer gets a reply; the caller must also send the subscription token. The check would have to be reworded by the user. |
| Done-when 5: "The same request without the master key, or with a wrong one, gets a 401" | Unchanged. | **Changed in shape.** `Authorization` carries the subscription token, so the master key must travel in another header (which one is not on the fact sheet: unverified). "The same request" would have to be redefined. |
| Done-when 1, 2, 3, 6 | Unchanged. | Unchanged. |
| Assumption 6: the user pastes the token into `.env` | Unchanged; the `litellm` container reads it. | The token stays in `.env` but no part of this epic's stack reads it. Its only consumer would be the host caller, and wiring Python is out of scope. |
| Assumption 5 | The "forbid" half is already narrowed by the user's G1 answer. The "block" half and "no API-key fallback" stand. | The same. Option (b) also intermediates the token. |
| Out of scope: wiring `main.py` | Unchanged. The later epic gets a standard OpenAI-style client contract: one bearer key. | The later epic inherits a non-standard contract: two credentials, one in a custom header. |
| Constraints | Unchanged. | Unchanged. |

Outside the brief:

- (a) leaves LiteLLM's documented path and keeps the token at rest in the container's environment.
- (b) reverses the plan's rule that the proxy forwards no client headers upstream.
- (b) is documented only for Claude Code on its own route. Whether forwarding applies to `/v1/chat/completions` is not on the fact sheet.

### Decision

**Option (a)** (ADR 0003). The user's steering names it ("use the SSO directly in litellm"), it changes nothing in the brief, and the documentation advantage of (b) does not reach this epic's caller. Both options stand or fall on the same question: does Anthropic accept the token from a client that does not identify as Claude Code? The probe answers that first, with one request and no LiteLLM (ADR 0007).

If the probe shows Anthropic accepts the token but the pinned LiteLLM release cannot present it from config, LiteLLM is configured with no Claude model and the rest of the stack ships (brief assumption 10). Option (b) is then noted as a possible later epic. Taking it is a brief change, so it is the user's decision and is never taken silently.

### What counts as identity

The no-impersonation rule is unchanged. This design draws the line here, for the user to see:

- **Protocol, allowed upstream:** the bearer authorization carrying the token, Anthropic's API version header, and the OAuth beta header that LiteLLM's documented flow itself adds (row 2). LiteLLM's own default user agent is left as it is.
- **Identity, forbidden:** any system prompt that names Claude Code, Claude Code's user agent, any header or beta flag that names Claude Code or its client application, and any session or device identifier of Claude Code.
- A header that fits neither list is treated as forbidden until the user rules on it.

Both options need the OAuth beta header. The user ruled that it counts as protocol (`decisions.md`).

## Components touched or added

| Component | Path | Change |
|---|---|---|
| Compose stack | `compose.yaml` (repo root) | **New.** Three services: `sandbox`, `litellm`, `db`. Top-level `name: data-visualization-agent`. |
| Sandbox image | `sandbox/Dockerfile` | **Existing, unchanged.** Added through pull request #3 (`decisions.md`). Build context is `./sandbox`, never the repo root, so neither `.env` nor the 53 MB parquet enters a build context. |
| LiteLLM proxy config | `litellm/config.yaml` | **New.** Model aliases and upstream credential wiring. Mounted read-only into the `litellm` container. Holds no secret values, only `os.environ/<NAME>` references. |
| LiteLLM database | service `db`, named volume `litellm_pgdata` | **New.** Postgres, owned entirely by LiteLLM. No published port. |
| Example env file | `env.example` (repo root) | **New.** Six secret names with placeholder values and one comment line each; five when the probe gave a no-Claude verdict (no `CLAUDE_CODE_OAUTH_TOKEN`). |
| Ignore rules | `.gitignore` | **Changed.** Gains `.env` and `.env.*`. |
| Readme | `README.md` | **Changed.** Gains the steps: copy `env.example` to `.env`, fill it in, `docker compose up -d`. |
| `main.py`, `pyproject.toml`, `uv.lock` | | **Untouched.** No Python wiring (out of scope). |

The capability probe (ADR 0007) is **not** a component. Its files are throwaway and live outside the repository.

Service shape (schema, not final text):

```yaml
name: data-visualization-agent

services:
  sandbox:
    build: ./sandbox
    network_mode: none            # no interface but loopback; no ports, no networks key
    init: true                    # PID 1 is `tail`; lets `compose down` stop it promptly and reaps exec'd children
    volumes:
      - ./workspace:/workspace    # read-write
    # no environment, no env_file, no docker socket

  litellm:
    image: ghcr.io/berriai/litellm:v1.108.18    # fact sheet row 1; moves only by the probe rule of ADR 0007
    command: ["--config", "/app/config.yaml"]
    ports:
      - "127.0.0.1:4000:4000"     # API and admin UI share this port
    volumes:
      - ./litellm/config.yaml:/app/config.yaml:ro
    environment:                  # explicit mapping, one line per variable
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY:?set LITELLM_MASTER_KEY in .env}
      LITELLM_SALT_KEY: ${LITELLM_SALT_KEY:?set LITELLM_SALT_KEY in .env}
      CLAUDE_CODE_OAUTH_TOKEN: ${CLAUDE_CODE_OAUTH_TOKEN:?set CLAUDE_CODE_OAUTH_TOKEN in .env}
      UI_USERNAME: ${UI_USERNAME:?set UI_USERNAME in .env}
      UI_PASSWORD: ${UI_PASSWORD:?set UI_PASSWORD in .env}
      DATABASE_URL: postgresql://litellm:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}@db:5432/litellm
    depends_on:
      db: { condition: service_healthy }
    # no healthcheck: nothing in the stack waits on litellm

  db:
    image: postgres:<pinned major>               # fact sheet row 8: not verified
    environment:
      POSTGRES_USER: litellm
      POSTGRES_DB: litellm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
    volumes:
      - litellm_pgdata:/var/lib/postgresql/data   # path must match the pinned major's data directory (row 8)
    healthcheck: pg_isready
    # no ports

volumes:
  litellm_pgdata:
```

`litellm/config.yaml` shape (schema, not final text). The key names are LiteLLM's usual config layout as this design recalls it: **unverified**, to be confirmed against the pinned release.

```yaml
model_list:
  - model_name: opus
    litellm_params:
      model: anthropic/claude-opus-5-5              # fact sheet rows 2 and 4
      api_key: os.environ/CLAUDE_CODE_OAUTH_TOKEN   # wiring W1; the form that passed the probe is the one written
  - model_name: sonnet                              # anthropic/claude-sonnet-5-5, same wiring
  - model_name: haiku                               # anthropic/claude-haiku-5-5, same wiring
# No client-header forwarding. No system prompt. No user agent. Nothing that names Claude Code.
```

Rules the compose file and the config must hold to:

- `sandbox` has `network_mode: none` and nothing else network-related. It shares no network with `litellm` or `db`.
- `sandbox` receives no environment variable from `.env` and mounts only `./workspace`. The repo root, `.env` and the Docker socket are never mounted into any container.
- The only published port in the stack is `127.0.0.1:4000`.
- The string `ANTHROPIC_API_KEY` appears in no committed file of the stack (`compose.yaml`, `litellm/config.yaml`, `env.example`), and no container has a variable of that name.
- `litellm/config.yaml` never holds the token's value. A wiring that needs the value written in the file fails the probe.
- `litellm/config.yaml` does not turn on forwarding of client headers to the upstream.
- No custom code, callback or patched image is added to make the token work.
- No CPU or memory limits on `sandbox` (brief assumption 7). No further hardening (capability drops, read-only root) is added in this epic; the brief does not ask for it.

## Interfaces

**Host agent to sandbox (contract for a later epic; nothing is wired now).**
- Transport: the Docker Engine API on the host (`exec`). Exec goes through the Docker daemon, not through the container's network, so it works with `network_mode: none`.
- Lookup: by Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. The container name is not part of the contract.
- Defaults inherited from the image: user `sandboxuser`, working directory `/workspace`.
- Files: `workspace/` on the host is `/workspace` in the container, read-write. This is the only way data moves in or out.

**Host to proxy.**
- `POST http://127.0.0.1:4000/v1/chat/completions` (OpenAI-compatible), header `Authorization: Bearer <LITELLM_MASTER_KEY>`, body `{"model": "<alias>", "messages": [...]}`.
- Aliases: `opus`, `sonnet`, `haiku`, mapping to `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5` (fact sheet row 4). The aliases carry no version, so callers do not change when the models do.
- Missing or wrong key: HTTP 401 (Done-when 5).
- The caller presents only the master key. The subscription token is held by the proxy and never sent by the caller.
- Readiness: `GET http://127.0.0.1:4000/health/readiness`, no authentication; it returns 503 while the database is unreachable (row 9). The stack tests wait on it.

**Admin UI.** `http://127.0.0.1:4000/ui`, login with `UI_USERNAME` / `UI_PASSWORD` (row 5).

**Secret names (`env.example`).**

| Name | Read by | Note |
|---|---|---|
| `LITELLM_MASTER_KEY` | `litellm` | Client-facing key. Must start with `sk-` (row 5; the docs disagree on whether the prefix is required, so the stack always uses it). |
| `LITELLM_SALT_KEY` | `litellm` | Required by LiteLLM's official compose example and cannot be rotated in place (row 6). Generate it once and never change it. What it protects is not on the fact sheet; it is believed to be what LiteLLM stores encrypted in the database (**unverified**). |
| `CLAUDE_CODE_OAUTH_TOKEN` | `litellm` | Subscription token the user generates themselves (brief assumption 6). The name is this stack's own. Present only after a "Build with Claude" verdict; with no Claude, it is in neither `env.example` nor `compose.yaml`. |
| `UI_USERNAME`, `UI_PASSWORD` | `litellm` | Admin UI login (row 5). LiteLLM's default user name is `admin`; the stack still requires both to be set. |
| `POSTGRES_PASSWORD` | `db`, and `litellm` inside `DATABASE_URL` | Letters, digits, `-` and `_` only, because it is placed in a URL and Compose interpolates `$`. |

`env.example` states that character rule for every generated value, the `sk-` prefix for the master key, and "set once" for the salt key. A missing variable makes `docker compose up` fail at once with the `:?` message, instead of starting a half-configured proxy.

**The subscription-token gate (ADR 0003, ADR 0007).** Steps run in this order. The probe runs before slice 01 is built, and its verdict decides whether slice 01 configures Claude. Slice 01 is built either way.

- **G1, terms.** Answered by the user twice, the second time with the legal page in front of them (`decisions.md`). No agent can give this answer.
- **Fact-sheet completion.** The session adds, from primary sources, the facts the probe needs and the sheet lacks:
  - Anthropic's Messages endpoint and API version header;
  - the exact name and value of the OAuth beta header that LiteLLM adds (the page of row 2);
  - the config key names for wirings W1 and W2 in the pinned release;
  - row 8 (Postgres major and data directory).
- **G2a, control.** One request from the host straight to Anthropic, with no LiteLLM and no Docker. It answers: does Anthropic accept this token from a client that does not identify as Claude Code?
- **G2b, proxy.** One throwaway LiteLLM container at the pinned tag, one alias, one request with a throwaway master key. It answers: can this release present the token from config?
- **G3, live.** On the built stack, a chat completion returns a Claude reply for each of the three aliases while no `ANTHROPIC_API_KEY` exists in `.env`, in the compose file or in the container's environment. This is Done-when 4.

G2a request (protocol):

```
POST <Anthropic Messages endpoint>
Authorization: Bearer <subscription token>
<API version header>
<OAuth beta header, exactly as LiteLLM adds it>
content-type: application/json

{"model": "claude-haiku-5-5", "max_tokens": 16,
 "messages": [{"role": "user", "content": "Reply with the word ok."}]}
```

No `system` field, no user-agent override, no other header. The token must be fresh (just generated), so an authentication error cannot be blamed on expiry.

G2b candidate wirings, tried in this order; both are **unverified**:

- **W1.** The deployment's `api_key` references the token. It passes only if the release recognises a subscription token there and sends it as a bearer credential with the OAuth beta header.
- **W2.** The deployment carries two static upstream headers: the bearer authorization and the OAuth beta header. The authorization value is built by Compose from `CLAUDE_CODE_OAUTH_TOKEN` into a container variable and referenced with `os.environ/`. That variable is not named `ANTHROPIC_API_KEY`.

If both fail for a LiteLLM-side reason on `v1.108.18`, the two may be tried once more on `v1.111.0`, the only other release the fact sheet names (row 1). There is no third wiring and no third release.

Verdicts:

| G2a | G2b | Verdict |
|---|---|---|
| Not 200 on a credential or client ground | Not run | **No Claude.** Anthropic does not accept the token from a client that is not Claude Code. Neither option (a) nor (b) can work inside the no-impersonation rule. LiteLLM gets no Claude model and no token; the rest of the stack ships. |
| 200 | 200 with W1 or W2 | **Build with Claude.** The wiring and the tag that passed are recorded and written into the stack. |
| 200 | No candidate passes | **No Claude** (brief assumption 10). The release cannot present the token from config. LiteLLM gets no Claude model and no token; the rest ships. The report says that option (b) is the remaining route, for a possible later epic, and which Done-when checks it would change. |

- G2b is never run after a failed G2a. A pass through the proxy after a failed control would mean LiteLLM adds something Anthropic takes for identity, which is the forbidden case.
- A 429, a 5xx or an error about the model is not a verdict. Repeat later, or with another of the three model identifiers.
- In every no-Claude verdict, no API key is used, no other Claude provider is configured and no workaround is added.

Probe hygiene:

- The probe's config file and the token stay outside the repository. `.env` is not yet git-ignored when the probe runs.
- The token reaches the request and the container from the person's shell session only. No verbose or trace flag is used, because those print the authorization header.
- The probe container publishes its port on `127.0.0.1` only and is removed afterwards.
- The probe is believed to need no database (**unverified**). If the release will not start without one, a throwaway Postgres container is added, still outside the repository.
- Evidence goes into `decisions.md` as a `block-answer`: for each step the HTTP status and, on failure, the error type; the wiring and the tag that passed. Never the token, never response headers.

**Verification notes for the plan.**
- Done-when 1 to 3 need only Docker. The sandbox image has no `curl`; the outbound check runs through Python inside the container and should not depend on DNS alone (connect to an IP address).
- Done-when 2 creates a file in `workspace/`; the check must delete it afterwards so it is not left untracked in git.
- Done-when 4 to 6 need the user's real `.env`. Agents cannot read `.env` (deny rule), and `docker` is not in `.sdlc.json` `allowed_bash`. Whether these three are run by the user by hand, or `docker` is allowed for the build, is the user's decision, not this design's.
- G2a and G2b are run by a person for the same two reasons.

## Data model changes

None in the application. The `db` service holds LiteLLM's own schema, which LiteLLM creates and migrates; no code in this repository reads or writes it. Its data lives in the named volume `litellm_pgdata` and survives `docker compose down` (it is removed only with `down -v`).

Applying the schema on start-up with no extra step is documented "from v1.109.0" and is unconfirmed for the pinned `v1.108.18` (fact sheet row 7). It is checked at the first `up` of slice 01. If the schema is not applied, that is a block reported to the user. The stack does not gain a migration step, and the pin does not move, without the user's answer.

## New dependencies

- **Docker Engine with Compose v2** on the host (brief assumption 9).
- **LiteLLM proxy image** `ghcr.io/berriai/litellm:v1.108.18`, the newest release on the 1.108.x LTS line (row 1). It is pinned to one release tag, not a moving tag: the container holds the subscription token and relies on undocumented behaviour, so what runs in it must not change unannounced. `v1.111.0` is GitHub's "Latest" but is not on the LTS line; the pin moves to it only by the probe rule of ADR 0007. Any later change of the pin re-runs G2a and G2b.
- **Postgres image**, pinned to a major version. The major and its data directory are not verified (row 8). They are taken from LiteLLM's official compose example (the page of row 6) and the Postgres image's documentation, and recorded before slice 01 is built.
- No Python dependency is added. `pyproject.toml` and `uv.lock` do not change.

## Decisions

- The sandbox runs with `network_mode: none`; the host agent reaches it only through Docker Engine exec and the `workspace/` mount (ADR 0001)
- The Compose project name is fixed to `data-visualization-agent`, and the sandbox is found by Compose labels, not by container name (ADR 0002)
- The proxy holds the Claude subscription token as the upstream credential of its Anthropic deployments, a route LiteLLM does not document; the caller sends only the master key; the proxy never presents Claude Code's identity; a failed gate leaves LiteLLM with no Claude model while the rest of the stack ships, with no API-key fallback and no workaround (ADR 0003)
- LiteLLM gets a Postgres database as a third service, `db`, with the named volume `litellm_pgdata`, and a sixth secret, `LITELLM_SALT_KEY` (ADR 0004)
- One root `.env` serves Compose and `python-dotenv`; the committed example is `env.example`; secrets reach containers by explicit `environment:` mapping; `.env` is added to `.gitignore` (ADR 0005)
- The sandbox runs as the image's `sandboxuser` with no user remapping; bind-mount write access on Linux hosts is a documented limitation (ADR 0006)
- The capability check is a live probe run before the build: a direct control request to Anthropic, then one throwaway proxy container; documentation cannot settle it (ADR 0007)

## Change to the architecture document

Apply to `docs/architecture.md` once the epic is built.

**Components table: add these rows.**

```
| Compose stack | `compose.yaml` | Implemented: services `sandbox`, `litellm`, `db` |
| Sandbox image | `sandbox/Dockerfile` | Implemented; started by the stack, nothing execs into it yet |
| LiteLLM proxy config | `litellm/config.yaml` | Implemented; no code calls the proxy yet |
| Example env file | `env.example` | Implemented (names only, no values) |
```

**Components: add a subsection after `### workspace/`.**

```
### Compose stack

`docker compose up -d` from the repository root starts three containers under the fixed project name `data-visualization-agent`.

- `sandbox`: built from `sandbox/Dockerfile` (Python 3.15-slim, pandas, seaborn, matplotlib, scipy, Excel readers, non-root `sandboxuser`). It idles on `tail -f /dev/null`. It has no network (`network_mode: none`), no secrets and one mount: `workspace/` at `/workspace`, read-write.
- `litellm`: the LiteLLM proxy, pinned to one release tag. It listens on `127.0.0.1:4000` only, serving an OpenAI-compatible API, the admin UI at `/ui` and an unauthenticated readiness check at `/health/readiness`. After a "Build with Claude" verdict, it exposes the aliases `opus`, `sonnet` and `haiku`, holds the user's Claude subscription token and presents it as the upstream credential of its three Anthropic deployments. LiteLLM does not document this route; it was proven by a live probe on the pinned tag (ADR 0007). After a "No Claude" verdict, it has no Claude model and no token. No Anthropic API key is configured anywhere.
- `db`: Postgres for LiteLLM's own records, with no published port. Its data is in the named volume `litellm_pgdata`.

The agent (`main.py`) is not a container. It runs on the host.
```

**Boundaries: replace the whole section with this.**

```
`main.py` still calls nothing. The stack sets these boundaries for the code that will:

- The host may call the proxy at `http://127.0.0.1:4000` with the master key. The proxy is not reachable from the LAN.
- The host caller never sends an Anthropic credential to the proxy. The proxy forwards no client headers to Anthropic.
- The host may control `sandbox` through the Docker Engine API (exec). The container is found by the Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`.
- `sandbox` may call nothing: not the internet, not the proxy, not the database, not the host. Data enters and leaves it only through `workspace/`.
- Only `litellm` talks to Anthropic and to `db`.
- The proxy never presents Claude Code's identity to Anthropic: no Claude Code system prompt, user agent, client header or identity header (ADR 0003).
- No container mounts the repository root, `.env` or the Docker socket.
```

**Data model: replace "None. There is no schema, database, state object or persisted output." with this.**

```
The application has no schema, state object or persisted output. The stack's Postgres database belongs to LiteLLM, which creates and migrates its schema; no code in this repository reads or writes it.
```

**Dependencies: add after the runtime line.**

```
The stack needs Docker Engine with Compose v2, the LiteLLM proxy image (`ghcr.io/berriai/litellm`) and the Postgres image, each pinned in `compose.yaml`. Changing the LiteLLM tag means running the capability probe of ADR 0007 again first.
```

**Dependencies: replace the `docker` intent bullet with this.**

```
- `docker`: controlling the `sandbox` container from the host (exec). The container exists; no code uses the library yet.
```

**Dependencies, gaps: replace the "No LLM provider integration" bullet with these two.**

```
- A proxy that reaches Claude exists, but no client library is installed to call it (no `langchain-openai`, `langchain-anthropic` or similar).
- The sandbox image installs `pandas` but no parquet engine (`pyarrow` or `fastparquet`), so code run in the sandbox cannot read the dataset yet.
```

**Configuration and secrets: replace the section body with this.**

```
- `.env` at the repository root is read by Docker Compose (variable substitution) and by `load_dotenv()` in `main.py`. It is git-ignored.
- `env.example` lists the names: `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` (only after a "Build with Claude" verdict), `UI_USERNAME`, `UI_PASSWORD`, `POSTGRES_PASSWORD`. It is not named `.env.example` because the project's permission rules deny reading `.env.*`.
- Each container receives only the variables it is given by name in `compose.yaml`. `sandbox` receives none.
- `LITELLM_SALT_KEY` is set once. LiteLLM cannot rotate it in place.
- The subscription token is generated by the user and expires; the stack does not refresh it.
- Using the subscription token through the proxy is outside what Anthropic's documentation says OAuth is designed for. The user accepted that risk for their own account and their own use (`decisions.md`, ADR 0003). The stack is personal and local: it must not be shared or deployed. Anthropic may reject the requests at any time; there is no API-key fallback.
- No Python code reads any of these variables yet.
```

**Decision records: replace "None. `docs/adr/` does not exist yet." with the list of ADR 0001 to 0007 by title.**
