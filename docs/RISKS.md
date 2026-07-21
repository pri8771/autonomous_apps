---
id: DOC-RISKS
canonicalFor: active-risks
status: active
owners: [product, engineering, security]
readWhen:
  - planning a milestone
  - approving architecture
  - reviewing release readiness
related:
  - docs/ASSUMPTIONS.md
  - docs/DECISIONS.md
  - docs/SECURITY.md
supersedes: []
---

# Risks

| ID | Risk | Probability | Impact | Mitigation | Owner | Status |
|---|---|---:|---:|---|---|---|
| RISK-001 | Public repository later receives proprietary or sensitive material. | medium | high | Resolve DEC-016; never commit secrets; review history. | product | open |
| RISK-002 | Parallel agents create repeated integration conflicts. | high | high | Expected scopes, interfaces, WIP, conflict scoring, integration owners, early rebases. | engineering | open |
| RISK-003 | Prompt injection or model output causes unsafe tool use. | high | critical | Default deny, untrusted-content labels, tool schemas, approvals, adversarial tests. | security | open |
| RISK-004 | Secrets leak into prompts, logs, transcripts, reports, or artifacts. | medium | critical | Keychain, redaction, secret-backed operations, classifications, tests. | security | open |
| RISK-005 | Local-only mode leaks through CLI, telemetry, embeddings, or fallback. | medium | critical | Gateway enforcement, environment sanitization, outbound tests. | security | open |
| RISK-006 | Local models exhaust unified memory. | high | high | Capacity detection, reservations, queueing, warnings, concurrency limits. | engineering | open |
| RISK-007 | CLI versions or output formats break adapters. | high | medium | Version discovery, adapter contract tests, supported-version matrix. | engineering | open |
| RISK-008 | Child processes survive cancellation or restart. | medium | high | Process-tree ownership, reconciliation, grace/force policy, tests. | engineering | open |
| RISK-009 | SQLite contention or corruption affects durability. | low | critical | Short transactions, WAL validation, backups, fixtures, integrity checks. | engineering | open |
| RISK-010 | Custom workflow engine becomes unreliable. | medium | high | Narrow V1 semantics, explicit state machine, events, deterministic tests. | engineering | open |
| RISK-011 | Agents create plausible but incomplete behavior. | high | high | Feature contracts, deterministic tests, independent review, evidence gate. | quality | open |
| RISK-012 | Repair loops consume unbounded time or money. | high | high | Attempt, time, token, cost, hierarchy, and runtime limits. | product | open |
| RISK-013 | Planning or subagents explode in count. | medium | high | Decomposition thresholds, WIP, depth/count limits, compiler, approval. | product | open |
| RISK-014 | Real-time discussion wastes tokens and blocks flow. | medium | medium | Async default, independent first responses, bounded rooms. | product | open |
| RISK-015 | Signing, entitlements, embedded binaries, or notarization fail late. | medium | high | Early distribution spike and clean-account tests. | release | open |
| RISK-016 | Tauri accessibility or packaged-app UI automation is insufficient. | medium | high | Early accessibility/test harness spikes and layered testing. | quality | open |
| RISK-017 | Large logs and event streams make UI sluggish. | high | medium | Pagination, virtualization, bounded retention, load fixtures. | engineering | open |
| RISK-018 | Plan change invalidates work incorrectly. | medium | high | Atomic graph updates, versions, carry-forward rules, tests. | engineering | open |
| RISK-019 | Provider cost metadata is inaccurate. | medium | medium | Capture usage, distinguish estimates from bills, budget margin. | product | open |
| RISK-020 | Development tools vary across machines. | high | medium | Capability probes, version records, worker compatibility, fixtures. | engineering | open |
| RISK-021 | Auto-update damages state or interrupts work. | low | high | Defer updates; signed artifacts, migration backups, critical-work inhibition. | release | open |
| RISK-022 | Final vision delays first useful release. | high | high | Protect V1 golden path and milestone exit criteria. | product | open |
