---
id: 0005
title: One root .env, an example named env.example, secrets mapped by name
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
CLAUDE.md says secrets come from `.env` and are never committed, yet `.gitignore` does not list `.env`. The brief asks for a committed example env file. `.claude/settings.json` denies `Read(./.env)` and `Read(./.env.*)`, so the agents that build and review the epic cannot read a file named `.env.example`. The sandbox runs generated code and must not see any secret.
## Decision
- `.gitignore` gains `.env` and `.env.*`, as the first change of the epic.
- One `.env` at the repository root serves both Docker Compose (variable substitution) and `python-dotenv`.
- The committed example is `env.example`, with no leading dot.
- `compose.yaml` passes secrets with an explicit `environment:` entry per variable, each using `${NAME:?message}`. No service uses `env_file:`. `sandbox` gets no variables.
## Alternative rejected
The conventional `.env.example`, with the deny rule loosened to allow it. It is the name people expect. It lost because it needs a change to the project's permission settings, which no agent may make or authorise, and because a rule that denies every `.env.*` except one is easier to get wrong than a file that never matches the rule.
## Consequences
- `env.example` is a slightly unusual name; the README must point to it.
- An `ANTHROPIC_API_KEY` exported in the user's shell does not reach any container, because nothing is passed implicitly.
- A missing secret stops `docker compose up` with a clear message.
- `main.py` loads the same file, so the stack's secrets are also in the agent's process environment. That is what the later wiring epic will want for the master key.
- Adding a secret means editing two places: `env.example` and the `environment:` block.
