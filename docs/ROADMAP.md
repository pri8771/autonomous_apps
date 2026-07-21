---
id: DOC-ROADMAP
canonicalFor: delivery-roadmap
status: active
owners: [product, engineering]
readWhen:
  - planning a milestone
  - assessing scope
  - approving promotion
related:
  - docs/PRODUCT.md
  - docs/STATUS.md
  - planning/PROJECT_GRAPH.yaml
supersedes: []
---

# Delivery Roadmap

## Stage 0 — Pre-coding readiness

Finalize and approve product scope, macOS form, architecture, workflow and concurrency semantics, model/data/security decisions, feature contracts, tests, risks, assumptions, master graph, repository visibility, and the human plan gate.

**Exit:** every mandatory item in `planning/READINESS_GATE.md` is satisfied or explicitly waived.

## Stage 1 — Repository and desktop scaffold

Create the Tauri macOS app, React/Vite UI, Rust workspace, SQLite migrations, typed contracts, redacted logging, settings/Keychain baseline, development commands, CI, and packaged-app smoke test.

**Demonstration:** the app opens, persists a project record, emits a typed event, restarts, and restores state.

## Stage 2 — Project graph foundation

Implement projects, repositories, requirements, features, tasks, dependencies, plan versions, cycle detection, readiness, task facets, graph/table UI, and plan compiler.

**Demonstration:** a large fixture project persists, validates, visualizes, and produces deterministic ready and blocked states.

## Stage 3 — Agent and model run lifecycle

Implement roles, model policies, context manifests, fake and OpenAI-compatible adapters, structured outputs, logs, cancellation, retry, restart recovery, and local-only enforcement.

## Stage 4 — Git, worktrees, and CLI execution

Implement repository registration, task branches, worktrees, PTYs, generic CLI adapters, environment sanitization, commits, diffs, artifacts, cleanup, and recovery.

## Stage 5 — True parallel scheduler

Implement worker capabilities, atomic claims, leases, heartbeats, priorities, WIP limits, resource reservations, conflict policy, backpressure, and scheduling explanations.

**Demonstration:** a fast worker completes multiple tasks while long workers continue; reviews can begin before sibling implementation finishes.

## Stage 6 — Parallel review and evidence

Implement review fan-out, deterministic commands, code/spec/security/accessibility/visual checks, evidence storage, completion reports, and acceptance gates.

## Stage 7 — Repair, communication, and change management

Implement failure classification, bounded repair, blackboard, direct messages, deliberation, change requests, impact analysis, atomic graph updates, and escalation.

## Stage 8 — Roles, teams, models, approvals, and learning

Implement role/team/workflow configuration, subagent policies, Ollama discovery and model management, approval inbox, budgets, planning-error ledger, metrics, and model evaluation.

## V1 release — Evidence-backed pull request factory

The full benchmark must register a repository, plan a feature, run tasks concurrently, let a fast worker continue, fan out reviews, repair a failure, add an omitted task through a change request, update the graph without stopping unrelated work, integrate branches, and open an evidence-backed pull request with costs and learning history.

## Post-V1 stages

1. Visual workflow designer.
2. Complete iOS/Xcode/simulator/TestFlight preparation.
3. Complete web preview/staging/deployment/rollback preparation.
4. Trusted remote workers and optional browser companion.
5. Feedback, maintenance, incident, experiment, and autonomous iteration workflows.

## Scope protection

The following do not enter V1 without an approved product change:

- Public plugin system or marketplace.
- Multi-tenant SaaS.
- Marketing automation.
- Unbounded swarms.
- Fully autonomous production deployment.
- Mac App Store distribution.
- Kubernetes.
