---
id: 0002
title: Fixed Compose project name; the sandbox is found by labels
status: proposed      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
Compose derives the project name from the folder name, which here is `TP` and differs on every checkout. Container names follow from it. A later epic must find the sandbox container from Python without guessing.
## Decision
`compose.yaml` sets the top-level `name: data-visualization-agent`. The contract for finding the sandbox is the pair of Compose labels `com.docker.compose.project=data-visualization-agent` and `com.docker.compose.service=sandbox`. The container name is not part of the contract.
## Alternative rejected
`container_name: sandbox` on the service. It gives a short, stable name, but the name is global on the Docker host, so it collides with any other project that uses the same name and with a second checkout of this one. Labels give the same stability without that collision.
## Consequences
- Volumes and the default network are prefixed `data-visualization-agent_` on every machine.
- Two checkouts of this repository on one host share one stack; they cannot run side by side.
- The later wiring epic looks the container up by labels.
