---
id: DOC-HANDOFF
canonicalFor: project-handoff
status: active
owners: [product, engineering]
readWhen:
  - resuming work
  - handing work to another agent or developer
related:
  - docs/STATUS.md
  - docs/README.md
  - planning/PROJECT_GRAPH.yaml
supersedes: []
---

# Handoff

## What the project is

Autonomous Apps is a desktop-first macOS software factory. It coordinates cloud models, local models, and CLI coding agents to plan and execute iOS and web software work in parallel with independent verification, bounded repair, formal change requests, approvals, and learning.

## Current state

- **Lifecycle:** `planned`
- **Implementation:** none
- **Documentation:** comprehensive planning package under review
- **Verification:** documentation review pending
- **Active branch:** `agent/document-final-scope`
- **Target:** `dev`
- **Coding gate:** `planning/READINESS_GATE.md`

## Approved platform direction

Apple Silicon macOS 14+, Tauri 2, React/TypeScript/Vite, Rust, SQLite, direct Developer ID distribution/notarization, no required hosted backend, browser companion after V1.

## Repository workflow

```text
task branch from dev
→ pull request to dev
→ promotion dev to qa
→ promotion qa to main
```

No agent writes directly to protected branches.

## Build and run

No executable scaffold exists. Exact commands remain `planned`. The scaffold must create commands for development launch, formatting, linting, schemas, frontend tests, Rust tests, integration tests, and production build. Do not invent commands before manifests exist.

## Important constraints

- Follow `AGENTS.md` and the repository map.
- No coding before the readiness gate.
- Resolve repository visibility before sensitive implementation.
- Never place secrets in Git.
- Enforce local-only outside prompts.
- Completion requires evidence.
- Public plugin architecture is out of scope.
- Single-user local operation is V1.

## Known issues

No confirmed product bugs. See `docs/BUGS.md`.

## Active risks

See `docs/RISKS.md`; highest-impact early risks include repository visibility, injection, secret leakage, process cleanup, resource pressure, and late signing/notarization failure.

## Next recommended task

Review and approve the documentation pull request. Then start the repository-scaffold work package in `planning/PROJECT_GRAPH.yaml`.

## Do not start with

Workflow designer, complete iOS release automation, complete web deployment automation, remote workers, browser companion, plugin system, or production deployment.
