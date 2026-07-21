---
id: DOC-STATUS
canonicalFor: current-status
status: active
owners: [product, engineering]
readWhen:
  - starting work
  - preparing a handoff
  - reviewing milestone readiness
related:
  - planning/READINESS_GATE.md
  - planning/PROJECT_GRAPH.yaml
  - docs/RISKS.md
supersedes: []
---

# Project Status

## Lifecycle status

`planned`

## Current objective

Complete and approve the documentation, architecture, feature contracts, quality plan, and dependency-aware task graph required before product code begins.

## Current product decision

Autonomous Apps will be a desktop-first macOS application with a React/Vite interface inside Tauri and a Rust local control plane. It targets Apple Silicon Macs running macOS 14 or later. A browser companion is post-V1.

## Verified

- Repository is registered against iOS App Factory Rules standard `0.4.0`.
- `dev` and `qa` branches exist.
- Branch promotion policy is task branch → `dev` → `qa` → `main`.
- The product is classified as a new project.
- No production code has been implemented.

## Verification pending

- Human approval of final product scope and architecture.
- Repository visibility decision before sensitive implementation.
- Validation of feature contracts and master graph.
- Confirmation of development and QA Mac environments.
- Technical spikes for Tauri, SQLite, PTY/process control, packaged-app testing, Git worktrees, Ollama, and distribution.
- Exact build, lint, test, signing, and packaging commands.

## Blockers

- Coding is blocked by `planning/READINESS_GATE.md`.
- Sensitive implementation is blocked while DEC-016 is unresolved.

## Active work

- Branch: `agent/document-final-scope`.
- Target: `dev`.
- Work type: planning and architecture only.

## Next action

Review the documentation pull request, resolve repository visibility, approve the pre-coding scope, and begin the repository-scaffolding milestone from `dev`.

## Completion vocabulary

Until executable checks exist, work remains `planned` or `verification_pending`. Do not mark architecture or features `verified` based only on documentation review.
