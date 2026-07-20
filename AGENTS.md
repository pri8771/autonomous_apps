# Agent Instructions

<!-- APP-FACTORY:BEGIN -->
This repository is registered with the iOS App Factory Rules repository.

Use this context path before editing:

1. `AGENTS.md`
2. `.factory/repository-map.json`
3. `.factory/project-context.json`
4. `.factory/standard-lock.json`
5. `docs/README.md`
6. Only task-relevant canonical documents and feature contracts

Do not recursively read the entire repository by default. Use the repository map and documentation index to retrieve the smallest authoritative context set.

The `projectType` in `.factory/project-context.json` is authoritative. Before implementing cross-cutting infrastructure, read `.factory/library-catalog.json` and `docs/REUSABLE_COMPONENTS.md`.

Do not create duplicate sources of truth. Separate facts, decisions, assumptions, and proposals. Do not mark work `done` unless required evidence exists; use `code_complete` or `verification_pending` while checks remain.
<!-- APP-FACTORY:END -->
