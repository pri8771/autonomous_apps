---
id: DOC-REUSABLE-COMPONENTS
canonicalFor: reusable-component-decisions
status: active
owners: [engineering]
readWhen:
  - implementing cross-cutting infrastructure
  - evaluating a shared module
related:
  - .factory/library-catalog.json
  - docs/ARCHITECTURE.md
supersedes: []
---

# Reusable Components

## Policy

Before cross-cutting infrastructure, inspect `.factory/library-catalog.json` and the central catalog. Use an approved library through a thin adapter when it fits. Otherwise build a narrow app-local module and promote only after real reuse evidence.

## Adopted central libraries

None. The locked catalog has no approved reusable libraries.

## Planned third-party foundations

Tauri 2, React, TypeScript, Vite, Rust ecosystem crates selected through ADRs, SQLite, and Ollama integration. Exact versions are selected during scaffold and spikes. Nothing is adopted until license, maintenance, security, API fit, and testability are reviewed.

## Planned app-local modules

| Candidate | Boundary | Initial location | Status |
|---|---|---|---|
| Project graph | Requirements, tasks, dependencies, plan versions | `crates/project-graph` | planned |
| Workflow engine | Durable workflows and transitions | `crates/workflow-engine` | planned |
| Scheduler | Claims, leases, WIP, resources | `crates/scheduler` | planned |
| Model gateway | Provider/runtime abstraction | `crates/model-gateway` | planned |
| Git runtime | Worktrees and integration | `crates/git-runtime` | planned |
| Evidence engine | Build/test/review gates | `crates/evidence-engine` | planned |
| Worker protocol | Future local/remote contract | `crates/worker-protocol` | planned |

## Promotion candidates

No code exists, so no candidate is proven. When one appears, record owner, API, tests, consumers, versioning, security, criteria, and duplication evidence. Do not extract code solely because it sounds generic.
