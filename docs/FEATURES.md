---
id: DOC-FEATURES
canonicalFor: feature-inventory
status: active
owners: [product]
readWhen:
  - planning features
  - locating feature contracts
  - defining release scope
related:
  - docs/PRODUCT.md
  - docs/ROADMAP.md
  - quality/feature-contracts/
supersedes: []
---

# Features

## Product outcome

A user can direct a local macOS software factory that turns approved product work into verified pull requests and controlled releases using parallel cloud, local, and CLI agents.

## Release boundaries

### V1

The complete golden path from project registration through evidence-backed pull request, including planning, concurrent implementation, independent review, repair, change requests, configurable models, approvals, and learning.

### Post-V1

Visual workflow editing, complete iOS and web release automation, remote workers, browser access, and continuous product operation.

## Feature inventory

| ID | Feature | Release | Status | Contract |
|---|---|---|---|---|
| FEAT-001 | Project registration and repository onboarding | V1 | planned | `quality/feature-contracts/FEAT-001.json` |
| FEAT-002 | Product and feature intake | V1 | planned | `quality/feature-contracts/FEAT-002.json` |
| FEAT-003 | Plan generation, critique, compilation, and approval | V1 | planned | `quality/feature-contracts/FEAT-003.json` |
| FEAT-004 | Project graph and task lifecycle | V1 | planned | `quality/feature-contracts/FEAT-004.json` |
| FEAT-005 | Parallel scheduling and worker management | V1 | planned | `quality/feature-contracts/FEAT-005.json` |
| FEAT-006 | Isolated Git and CLI agent execution | V1 | planned | `quality/feature-contracts/FEAT-006.json` |
| FEAT-007 | Parallel review, testing, and evidence | V1 | planned | `quality/feature-contracts/FEAT-007.json` |
| FEAT-008 | Bounded repair and escalation | V1 | planned | `quality/feature-contracts/FEAT-008.json` |
| FEAT-009 | Agent messaging and deliberation | V1 | planned | `quality/feature-contracts/FEAT-009.json` |
| FEAT-010 | Change requests and plan versioning | V1 | planned | `quality/feature-contracts/FEAT-010.json` |
| FEAT-011 | Roles, teams, subagents, and model policies | V1 | planned | `quality/feature-contracts/FEAT-011.json` |
| FEAT-012 | Local and cloud model center | V1 | planned | `quality/feature-contracts/FEAT-012.json` |
| FEAT-013 | Approvals and branch promotion | V1 | planned | `quality/feature-contracts/FEAT-013.json` |
| FEAT-014 | Learning, metrics, and planning-error ledger | V1 | planned | `quality/feature-contracts/FEAT-014.json` |
| FEAT-015 | Visual workflow designer | Post-V1 | planned | `quality/feature-contracts/FEAT-015.json` |
| FEAT-016 | iOS build, simulator, and release workflows | Post-V1 | planned | `quality/feature-contracts/FEAT-016.json` |
| FEAT-017 | Web build, preview, and deployment workflows | Post-V1 | planned | `quality/feature-contracts/FEAT-017.json` |
| FEAT-018 | Remote workers and optional browser companion | Post-V1 | planned | `quality/feature-contracts/FEAT-018.json` |

## Dependency summary

```text
FEAT-001 onboarding
  └── FEAT-002 intake
        └── FEAT-003 planning
              └── FEAT-004 graph
                    ├── FEAT-005 scheduler
                    │     └── FEAT-006 execution
                    │           ├── FEAT-007 review/evidence
                    │           │     └── FEAT-008 repair
                    │           ├── FEAT-009 communication
                    │           └── FEAT-010 changes
                    ├── FEAT-011 roles/teams
                    ├── FEAT-012 model center
                    └── FEAT-013 approvals
FEAT-014 consumes events across V1
```

## Feature completion rule

A feature moves from `planned` only when its contract is approved, architecture decisions exist, tasks are in the active graph, tests/evidence are identified, and no unresolved blocker prevents safe work. A screen or placeholder control is not an implemented feature.
