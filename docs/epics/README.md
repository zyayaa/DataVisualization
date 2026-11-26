# Epics

Each epic is a numbered folder here. The repository is the only store: nothing in these files records a status, which is derived from branches and pull requests (`sdlc-status --explain`).

```
docs/epics/
├── 001-<slug>/
│   ├── brief.md        goal, scope, Done-when checks, constraints, assumptions
│   ├── design.md       only when the epic changes the architecture
│   ├── plan.md         ordered slice list, interfaces, test strategy
│   ├── decisions.md    append-only: replans, answers to blocks, follow-ups, retro
│   ├── mockups/        UI epics only: sources, manifest.json, previews/
│   └── items/          one numbered file per work item; the number is the build order
├── quick/              single-item changes that skip the plan
└── archive/            closed epics
```

Specs change only through a spec pull request into the base branch. Code never changes in the same pull request, except in the quick lane.
