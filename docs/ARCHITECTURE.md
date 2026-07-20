# Architecture

## Approach

Start as a private modular monolith. Preserve clear internal contracts without building a public plugin system.

```text
Dashboard
  ↓
Control-plane API
  ↓
Project graph + policy engine
  ↓
Event-driven scheduler
  ↓
Agent runtime + model gateway
  ↓
Git worktrees + CLI/model workers
  ↓
Build, test, review, evidence, and learning
```

## Initial components

### Dashboard
Projects, plans, task graph, runs, reviews, models, approvals, costs, and learning records.

### Control-plane API
Project configuration, workflow commands, policies, approvals, and audit access.

### Project graph
Requirements, tasks, dependencies, readiness calculation, plan versions, and change application.

### Scheduler
Atomic task claims, leases, worker heartbeats, priorities, resource matching, conflict risk, and WIP limits.

### Agent runtime
Role instructions, context assembly, parent/subagent limits, tool permissions, messages, and run lifecycle.

### Model gateway
Cloud providers, OpenAI-compatible endpoints, local runtimes, model capability metadata, effort, budgets, and local-only enforcement.

### Execution layer
Git worktrees, task branches, subprocess/PTY management, Docker workers, macOS workers, browsers, simulators, and artifact capture.

### Verification
Builds, automated tests, independent reviews, visual checks, security checks, acceptance evidence, and repair loops.

### Learning
Change requests, planning errors, estimates, rework, repeated patterns, and planning rules.

## Initial technology direction

- Dashboard: Next.js and TypeScript.
- API: TypeScript/NestJS or Python/FastAPI; final choice requires an ADR.
- Database: PostgreSQL.
- Events and queues: Redis Streams initially.
- Agent runtime: Python.
- Live updates: WebSockets.
- Isolation: Git worktrees and Docker where supported.
- Local models: Ollama first, then generic OpenAI-compatible local endpoints.
- iOS execution: native macOS worker.

## Core invariants

- No agent writes directly to `main`.
- No task is accepted without required evidence.
- No global worker rounds.
- Plans and change requests are versioned and auditable.
- Local-only mode is enforced by the gateway, not by prompts.
