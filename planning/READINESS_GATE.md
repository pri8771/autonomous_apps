---
id: PLAN-READINESS-GATE
canonicalFor: pre-coding-readiness
status: verification_pending
owners: [product, engineering, quality, security]
readWhen:
  - deciding whether coding may begin
  - approving PLAN-001
related:
  - planning/PROJECT_GRAPH.yaml
  - docs/STATUS.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
---

# Pre-Coding Readiness Gate

## Rule

No product code begins until PLAN-001 is approved. Documentation may be merged while items remain `verification_pending`, but the scaffold cannot start until every mandatory item is satisfied or an explicit waiver is approved.

## Product

- [ ] Final scope, V1/post-V1 boundary, and non-goals approved.
- [ ] Desktop-first macOS form approved.
- [ ] Apple Silicon and macOS 14+ approved.
- [ ] Single-user V1 model approved.
- [ ] Repository visibility intentionally resolved.

## Features

- [ ] `docs/FEATURES.md` approved.
- [ ] FEAT-001 through FEAT-014 contracts approved.
- [ ] Every V1 contract defines real sources, states, recovery, accessibility, prohibited behavior, and tests.
- [ ] Post-V1 scope remains excluded from V1.
- [ ] V1 benchmark approved.

## Architecture

- [ ] Tauri, React, TypeScript, Vite, Rust, and SQLite decisions approved.
- [ ] Component boundaries, macOS lifecycle, workflows, concurrency, models, data, and security approved.
- [ ] No proposal is presented as accepted behavior.

## Planning

- [ ] `planning/PROJECT_GRAPH.yaml` parses.
- [ ] Requirements map to features and tasks.
- [ ] Every task has owner, dependencies, inputs, outputs, criteria, scope, reviews, effort, and confidence.
- [ ] All dependency references exist and no cycles exist.
- [ ] Coding tasks depend on PLAN-001.
- [ ] Change requests, tests, docs, security, migration, and release work are represented.
- [ ] Low-confidence tasks are visible.

## Quality

- [ ] Test plan and quality manifest approved.
- [ ] Packaged-app test strategy has an owner task.
- [ ] Accessibility, performance, recovery, and security matrices are explicit.
- [ ] Release checklist includes signing, Hardened Runtime, notarization, Gatekeeper, and clean-account testing.

## Security

- [ ] No credentials in repository.
- [ ] Keychain, local-only, capability, process, filesystem, Git, model, network, destructive-action, injection, redaction, and approval policies approved.
- [ ] Public/private repository decision complete.

## Environment

- [ ] Development Mac baseline recorded.
- [ ] QA clean-account or machine strategy recorded.
- [ ] Storage/memory, Git, Xcode, signing/notarization availability, and Ollama path recorded.

## Governance

- [ ] `dev` and `qa` exist.
- [ ] Task branches start from `dev`.
- [ ] Agent entry files and canonical index are current.
- [ ] Completion report, evidence, and waiver locations exist.
- [ ] Obsolete bootstrap PR to `main` is closed or clearly superseded.

## Approval record

Record plan version, documentation PR/commit, approver, date, V1 boundary, first coding work package, accepted risks, and waivers. Until then, PLAN-001 remains `blocked`.
