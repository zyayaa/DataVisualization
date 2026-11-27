---
id: 0001
title: The sandbox has no network and is controlled through Docker exec
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
The sandbox will run code an LLM generates. The brief requires that it has "no network at all", yet the agent, running on the host, must later run commands in it and exchange files with it.
## Decision
The `sandbox` service uses `network_mode: none`. It publishes no port and joins no Compose network. The host controls it through the Docker Engine API (`exec`), which goes through the Docker daemon and does not use the container's network. Files move only through the `workspace/` bind mount. The Docker socket is not mounted into any container. The service sets `init: true` so the idle container stops promptly and exec'd child processes are reaped.
## Alternative rejected
A Compose network marked `internal: true`. It blocks the route to the internet, but the container still has a network interface and DNS and can reach any other container placed on that network, including the proxy that holds the subscription token. The brief says no network at all, and `none` is the setting that means exactly that.
## Consequences
- The sandbox cannot install packages at run time; everything it needs must be in the image.
- The sandbox cannot call the proxy. Any LLM call is made by the agent on the host.
- The agent needs access to the host's Docker daemon, which is a powerful permission on the host side.
- Isolation in this epic is: no network, a non-root user, one mount. No resource limits or capability drops; a later epic may add them.
