---
id: DOC-INDEX
canonicalFor: documentation-navigation
status: active
owners: [product, engineering]
readWhen:
  - starting any task
  - locating authoritative project information
related:
  - ../AGENTS.md
  - ../.factory/repository-map.json
supersedes: []
---

# Documentation Index

## Purpose

This is the canonical navigation index for Autonomous Apps. Use it to retrieve the smallest authoritative context set for the current task. Do not scan the repository recursively by default.

## Current summary

- **Lifecycle:** `planned`
- **Product form:** desktop-first macOS app with a React/Vite interface inside Tauri
- **Primary outcome:** turn an approved feature into a verified pull request through asynchronous multi-agent execution
- **Current objective:** finish and approve the pre-coding documentation and task graph
- **Coding gate:** `planning/READINESS_GATE.md`

## Canonical documents

| Topic | Canonical owner | Status |
|---|---|---|
| Product identity and lifecycle | `.factory/project-context.json` | active |
| Standards version | `.factory/standard-lock.json` | active |
| Repository navigation | `.factory/repository-map.json` | active |
| Product scope | `docs/PRODUCT.md` | active |
| Feature inventory | `docs/FEATURES.md` | active |
| Current status | `docs/STATUS.md` | active |
| Architecture | `docs/ARCHITECTURE.md` | active |
| macOS product behavior | `docs/MACOS_APP.md` | active |
| Workflow and task semantics | `docs/WORKFLOW_ENGINE.md` | active |
| Parallel scheduling | `docs/CONCURRENCY_MODEL.md` | active |
| Models and local runtimes | `docs/MODEL_SYSTEM.md` | active |
| Persistent entities and events | `docs/DATA_MODEL.md` | active |
| Security and permissions | `docs/SECURITY.md` | active |
| Engineering rules | `docs/APP_FACTORY_RULES.md` | active |
| Decisions | `docs/DECISIONS.md` | active |
| Risks | `docs/RISKS.md` | active |
| Assumptions | `docs/ASSUMPTIONS.md` | active |
| Bugs | `docs/BUGS.md` | active |
| Test strategy | `docs/TEST_PLAN.md` | active |
| Roadmap | `docs/ROADMAP.md` | active |
| Release readiness | `docs/RELEASE_CHECKLIST.md` | active |
| Reusable components | `docs/REUSABLE_COMPONENTS.md` | active |
| Handoff | `docs/HANDOFF.md` | active |
| Master task graph | `planning/PROJECT_GRAPH.yaml` | active |
| Pre-coding gate | `planning/READINESS_GATE.md` | active |
| Feature contracts | `quality/feature-contracts/` | active |
| Completion reports | `quality/completion-reports/` | active |
| Quality evidence | `quality/evidence/` | active |

## Task-specific reading routes

### Product or scope change

1. `docs/PRODUCT.md`
2. `docs/FEATURES.md`
3. `docs/ASSUMPTIONS.md`
4. `docs/RISKS.md`
5. `planning/PROJECT_GRAPH.yaml`

### Architecture work

1. `docs/ARCHITECTURE.md`
2. The relevant subsystem document
3. `docs/DECISIONS.md`
4. `docs/SECURITY.md`
5. `docs/TEST_PLAN.md`

### Feature implementation

1. `docs/STATUS.md`
2. `docs/ARCHITECTURE.md`
3. The matching `quality/feature-contracts/FEAT-*.json`
4. The assigned task in `planning/PROJECT_GRAPH.yaml`
5. Only the subsystem documents referenced by that task

### Bug fix

1. `docs/BUGS.md`
2. The affected feature contract
3. `docs/ARCHITECTURE.md`
4. `docs/TEST_PLAN.md`

### Release work

1. `docs/STATUS.md`
2. `docs/TEST_PLAN.md`
3. `docs/RELEASE_CHECKLIST.md`
4. Required completion reports and evidence

### Reusable infrastructure

1. `.factory/library-catalog.json`
2. `docs/REUSABLE_COMPONENTS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DECISIONS.md`

## Current versus historical truth

Current truth lives only in the canonical documents above. Superseded plans, completed change requests, old completion reports, and release history must remain clearly marked as historical and must not override current documents.

## Known documentation gaps

No product code exists yet, so exact build commands, bundle identifiers, signing identities, database migration commands, and CI artifact locations remain `planned`. Their owner tasks are listed in `planning/PROJECT_GRAPH.yaml`; they must be populated during the repository-scaffolding milestone before feature implementation begins.
