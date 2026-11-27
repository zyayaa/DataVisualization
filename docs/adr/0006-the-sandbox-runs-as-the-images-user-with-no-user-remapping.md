---
id: 0006
title: The sandbox runs as the image's user, with no user remapping
status: accepted      # proposed | accepted | superseded
epic: 001
supersedes:           # ADR id, when this replaces an accepted decision
---
## Context
`workspace/` is bind-mounted read-write, and Done-when 2 requires that a file created by the sandbox user appears on the host. The bind mount hides the `chown` done in the image, so write access depends on the host. On Docker Desktop for macOS, the user's platform, file ownership is translated and writes work. On a Linux host, writes work only if the host owner of `workspace/` has the same numeric user id as `sandboxuser`. The brief fixes the image as it is, including its non-root user.
## Decision
Compose does not set `user:` for `sandbox`. It runs as `sandboxuser` as the image defines. The Linux limitation is written in the README.
## Alternative rejected
Setting `user: "${UID}:${GID}"` in `compose.yaml` so the container runs as the host user. It makes writes work on any Linux host. It lost because the container would no longer run as the `sandboxuser` the brief names, it would run with no home directory or passwd entry, and it would need two more variables that Compose does not supply by itself, all for a platform nobody on the project is known to use.
## Consequences
- Done-when 2 is expected to pass on macOS with Docker Desktop.
- On Linux with a differing user id, the sandbox can read `workspace/` but may not be able to write to it. Fixing that needs a new decision record.
- Files the sandbox writes land in `workspace/` as untracked files in git.
