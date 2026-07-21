---
id: DOC-ARCHITECTURE
canonicalFor: current-architecture
status: active
owners: [engineering]
readWhen:
  - changing architecture
  - onboarding an implementation agent
  - defining subsystem contracts
related:
  - docs/MACOS_APP.md
  - docs/WORKFLOW_ENGINE.md
  - docs/CONCURRENCY_MODEL.md
  - docs/MODEL_SYSTEM.md
  - docs/DATA_MODEL.md
  - docs/SECURITY.md
  - docs/DECISIONS.md
  - docs/TEST_PLAN.md
supersedes: []
---

# Architecture

## Purpose

Define the approved architecture and component boundaries for the Autonomous Apps product.

## Authority and scope

This document owns system-wide component boundaries and data flow. Detailed task semantics, scheduler behavior, model behavior, security, and persistence belong to their focused canonical documents.

## Current summary

Autonomous Apps is a local-first macOS desktop application. It uses a React/Vite user interface inside a Tauri 2 shell. A Rust control plane owns project state, scheduling, permissions, subprocesses, Git worktrees, model connections, verification, and audit history. SQLite is the embedded system of record.

The app requires no hosted backend for V1. External services are optional integrations.

## Architectural style

Start as a modular monolith with explicit internal boundaries:

```text
┌──────────────────────────────────────────────────────────────┐
│                    macOS Desktop Application                 │
├──────────────────────────────────────────────────────────────┤
│ React + TypeScript + Vite UI                                │
│ Projects · Graph · Runs · Reviews · Models · Approvals       │
├──────────────────────────────────────────────────────────────┤
│ Tauri command/event boundary                                │
├──────────────────────────────────────────────────────────────┤
│ Rust Control Plane                                           │
│ Project graph · workflow engine · scheduler · policy          │
│ agent runtime · model gateway · Git/PTY · evidence · learning │
├──────────────────────────────────────────────────────────────┤
│ Local Infrastructure                                         │
│ SQLite · Keychain · application support · Git worktrees       │
│ Ollama/local endpoints · Xcode · Docker · browsers · CLIs     │
└──────────────────────────────────────────────────────────────┘
```

A later remote-worker protocol may connect additional Macs or Linux hosts, but the first release must work on one Mac.

## Approved technology baseline

| Area | Decision |
|---|---|
| Desktop shell | Tauri 2 |
| UI | React + TypeScript + Vite |
| Privileged/control-plane code | Rust |
| Async runtime | Tokio-compatible Rust runtime |
| Local database | SQLite with migrations, foreign keys, and WAL |
| UI/control-plane communication | Typed Tauri commands and events |
| Long-running task state | Persisted workflow state in SQLite |
| Live event delivery | In-process channels plus persisted event log |
| Secrets | macOS Keychain references |
| Repository isolation | Git branches and worktrees |
| CLI interaction | Child processes and PTYs managed by Rust |
| Local models | Ollama first; generic OpenAI-compatible endpoints next |
| macOS distribution | Developer ID signing, hardened runtime, notarization |
| Hosted backend | Not required for V1 |

## Monorepo direction

```text
apps/
  desktop/                 # Tauri configuration and app shell
  ui/                      # React/Vite interface

crates/
  factory-core/            # application services and shared domain errors
  contracts/               # serialized commands, events, and versioned schemas
  storage/                 # SQLite migrations and repositories
  project-graph/           # requirements, tasks, dependencies, plan versions
  workflow-engine/         # durable workflow and step transitions
  scheduler/               # claims, leases, priorities, WIP, resources
  policy-engine/           # permissions, approvals, budgets, local-only rules
  agent-runtime/           # role execution, context, messages, subagents
  model-gateway/           # provider adapters, streaming, routing, accounting
  git-runtime/             # repositories, branches, worktrees, integration
  process-runtime/         # subprocesses, PTYs, cancellation, resource limits
  evidence-engine/         # tests, reviews, artifacts, completion gates
  learning-engine/         # planning errors, metrics, reusable rules
  worker-protocol/         # future local/remote worker contract

roles/
prompts/
workflows/
planning/
quality/
docs/
```

Names may change during scaffolding, but component ownership may not be collapsed without an accepted architecture decision.

## Core components

### Desktop shell

Owns window lifecycle, native menus, notifications, file and folder pickers, application data locations, Keychain integration, packaging, and Tauri capabilities. It must not contain project-domain logic.

### User interface

Owns portfolio and project navigation, task graph visualization, run consoles, reviews, evidence, model center, workflow and role configuration, approvals, and settings. The UI is a projection of control-plane state and must not invent completion.

### Project graph

Owns requirements, features, tasks, dependencies, readiness, expected write scope, acceptance criteria, required reviews, plan versions, and atomic change application.

### Workflow engine

Owns durable planning, implementation, review, verification, repair, deliberation, change-request, integration, and promotion workflows.

### Scheduler

Owns ready-task selection, atomic claims, leases, heartbeats, priorities, worker matching, resource reservations, WIP limits, conflict risk, and backpressure.

### Agent runtime

Owns roles, context assembly, parent/subagent limits, tools, model assignment, messages, cancellation, retry, and structured outputs.

### Model gateway

Owns provider and local-runtime adapters, streaming, capabilities, routing, accounting, limits, fallback, and local-only enforcement.

### Git and process runtimes

Own repositories, branches, worktrees, commits, diffs, integration, executable allowlists, PTYs, timeouts, process trees, and cleanup.

### Evidence and policy engines

Own builds, tests, reviews, artifacts, completion gates, permissions, approvals, budgets, branches, secrets, networks, and destructive-action rules.

### Learning engine

Owns planning omissions, scope changes, estimates, rework, repairs, review escapes, model performance, and planning-rule proposals.

## Local data flow

```text
User action
  → typed UI command
  → policy validation
  → domain transaction
  → SQLite state + append-only event
  → committed projection
  → live event to UI
  → background work scheduled when applicable
```

## Agent execution flow

```text
Ready task
  → scheduler claim and lease
  → isolated worktree
  → context package
  → selected model or CLI adapter
  → streamed run events
  → output validation
  → build/test/review fan-out
  → evidence gate
  → accepted, repair, change request, or escalation
```

## Persistence and artifacts

SQLite is authoritative for control-plane state. Repositories, worktrees, model files, and large artifacts remain on disk.

```text
~/Library/Application Support/Autonomous Apps/
  factory.sqlite
  artifacts/
  logs/
  model-cache/
  workspaces/
```

Raw credentials do not belong in SQLite. Store Keychain identifiers and safe metadata only.

## Event model

Every meaningful transition creates an immutable event record, including project creation, plan versions, claims, agent runs, messages, reviews, tests, repairs, changes, acceptance, and promotion. Current state is stored for efficient reads, but audit and recovery rely on persisted history.

## Failure recovery

The app must recover after UI restart, control-plane restart, process crash, model timeout, lost heartbeat, interrupted Git operation, test crash, network loss, and machine sleep or wake. Startup reconciliation occurs before new work is scheduled.

## Concurrency boundary

Task and review execution are asynchronous. State mutation remains transactional. No global worker rounds are permitted. Fan-in occurs only where a workflow explicitly requires all prerequisite outputs.

## Security boundary

The Tauri/Rust layer is the privileged boundary. The webview receives typed, capability-scoped commands. Agents receive task-scoped tools and never raw credentials by default.

## Initial deployment model

V1 is distributed directly as a signed and notarized macOS application. Mac App Store distribution is excluded because the application must manage user-selected repositories and external development tools.

## Future browser companion

The React UI may later connect to a local or remote control-plane service. This is a future extension, not permission to build a hosted backend before the desktop golden path is verified.

## Core invariants

- No agent writes directly to `dev`, `qa`, or `main`.
- No task is accepted without required evidence.
- No global worker rounds.
- No raw secret values in prompts, logs, or ordinary artifacts.
- No local-only project sends model content to external endpoints.
- No change silently mutates an approved plan.
- No background process survives cancellation without reconciliation.
- No destructive action bypasses policy.
- No UI status is more optimistic than persisted state.
