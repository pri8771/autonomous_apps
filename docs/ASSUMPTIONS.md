---
id: DOC-ASSUMPTIONS
canonicalFor: active-assumptions
status: active
owners: [product, engineering]
readWhen:
  - planning work
  - validating an uncertain dependency
  - creating a change request
related:
  - docs/DECISIONS.md
  - docs/RISKS.md
  - planning/PROJECT_GRAPH.yaml
supersedes: []
---

# Assumptions

Assumptions are not facts. Each must be validated, accepted as a constraint, or replaced by a decision before dependent production work is accepted.

| ID | Assumption | Evidence | Validation plan | Status |
|---|---|---|---|---|
| ASM-001 | Initial operator uses Apple Silicon macOS 14+. | Product direction. | Confirm development and QA machines. | active |
| ASM-002 | Single-user local operation is sufficient for V1. | Approved scope. | Validate benchmark without shared accounts. | active |
| ASM-003 | Tauri webview supports required dashboards, graphs, and live consoles. | Architecture direction. | Early UI shell and load spike. | active |
| ASM-004 | Rust can provide Git, PTY, SQLite, streaming HTTP, and process-tree control without mandatory Python. | Ecosystem assumption. | Technical spikes before crate lock. | active |
| ASM-005 | SQLite is sufficient for one local control plane. | Bounded V1 scale. | Load and concurrent-claim tests. | active |
| ASM-006 | Ollama can be installed separately for the first local-model milestone. | Runtime decision. | Detection and guided-install test. | active |
| ASM-007 | Local models can perform planning, review, and bounded coding on target hardware. | Not yet project evidence. | Benchmark on actual Mac. | unverified |
| ASM-008 | GitHub is the initial remote source-control provider. | Current repository. | Validate branch, PR, and CI integration. | active |
| ASM-009 | Coding CLIs expose stable enough non-interactive or PTY behavior. | Product requirement. | Adapter contract tests per version. | unverified |
| ASM-010 | Xcode is installed on Macs assigned iOS work. | iOS requirement. | Capability detection and missing-tool UX. | active |
| ASM-011 | Direct Developer ID distribution is acceptable. | Private desktop direction. | Signed/notarized QA build on clean account. | active |
| ASM-012 | Future browser companion can reuse UI without hosted V1 architecture. | React boundary. | Revisit after V1 benchmark. | active |
| ASM-013 | Repository can be made private before sensitive work if desired. | User created it public temporarily. | User decision. | pending |
| ASM-014 | Managed projects may contain hostile prompt injection or scripts. | Threat model. | Adversarial fixtures and policy tests. | active |
| ASM-015 | V1 may require the app to remain running during work. | No daemon in V1. | Validate quit/recovery expectations. | active |
