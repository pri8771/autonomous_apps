---
id: DOC-TEST-PLAN
canonicalFor: test-and-verification-strategy
status: active
owners: [quality, engineering]
readWhen:
  - implementing a feature
  - adding a runner or integration
  - preparing QA or release
related:
  - quality/quality-manifest.json
  - docs/FEATURES.md
  - docs/RELEASE_CHECKLIST.md
  - docs/SECURITY.md
supersedes: []
---

# Test Plan

## Purpose

Define verification for the macOS application, Rust control plane, React UI, workflow engine, integrations, generated product work, and releases.

## Quality principle

A feature is complete only when real behavior, states, recovery, accessibility, and required evidence are verified. Agent statements and screenshots alone are insufficient.

## Test layers

### Contracts and schemas

Validate Tauri commands/events, project graph, workflows, roles, teams, model policies, feature contracts, agent outputs, evidence, completion reports, change requests, planning errors, and migrations.

### Rust unit tests

Task readiness, cycles, plan versions, claims, leases, policy, budgets, failure classification, completion gates, graph patches, and learning metrics.

### Storage tests

SQLite migrations, foreign keys, transactions, idempotency, concurrent claims, event/state atomicity, backup/recovery, prior-version fixtures, and interruption integrity.

### Integration tests

UI command → transaction → event; scheduler → agent runtime; runtime → model; scheduler → Git/process; implementation → review fan-out; failed check → repair; change → graph update; approval → action; restart reconciliation.

### Frontend tests

Navigation, forms, validation, task/review states, graph/table alternatives, log virtualization, empty/loading/error/offline/permission/cancellation states, keyboard flow, dark mode, compact/expanded layouts, and approval consequences.

### Packaged macOS tests

Launch, restoration, pickers, Keychain, menus, shortcuts, notifications, child processes, quit with active work, restart recovery, Application Support paths, signing/notarization, and clean-account install. An early spike must prove the automation/smoke approach.

### Process and PTY tests

Streaming, interactive input, large output, partial/invalid text, timeout, cancellation, process trees, crash, resume, environment sanitization, workdir, and output limits.

### Git tests

Registration, branches, worktrees, concurrency, dirty state, rebase, diff/commit evidence, conflicts, integration, protected-branch denial, and safe cleanup.

### Model gateway tests

Streaming, structured output, tools, timeout, rate limit, invalid response, refusal, cancellation, fallback, cost, local-only, context manifests, and secret redaction. Live-provider tests remain separate from deterministic CI.

### Ollama tests

Health, installed models, pull progress, cancellation, removal confirmation, generation streaming, compatible endpoint behavior, missing model, unavailable runtime, storage failure, and benchmark metadata. Tests must not unexpectedly pull large models.

### Scheduler tests

Claim race; short versus long tasks; immediate new claim; early review; lease expiry; late heartbeat; restart; duplicate completion; WIP; resource conflict; review backpressure; plan invalidation; cancellation; local-model pressure.

### Workflow tests

Independent planning, critique, synthesis, compiler rejection, approval, subagent limits, messages, deliberation, repair/change classification, graph update, integration, and every terminal state.

### Security tests

Capability denial, traversal, symlink escape, secret redaction, environment leakage, prompt injection, protected branches, local-only outbound denial, approval invalidation, process-tree termination, and tampered artifact/update.

### Accessibility tests

VoiceOver labels/order, keyboard-only golden path, visible focus, reduced motion, non-color status, contrast, text scaling, graph alternative, and background announcements.

### Performance tests

10,000 tasks, large event history, simultaneous logs, many findings, scheduler throughput, SQLite contention, UI responsiveness, model download progress, and cleanup. Thresholds are established by the baseline task.

### Recovery tests

Force quit, sleep/wake, network loss, Git failure, SQLite interruption, runtime restart, CLI crash, failed model download, corrupt artifact reference, orphan worktree, and failed migration.

## Generated-project benchmarks

- **A:** simple web feedback feature with real persistence and errors.
- **B:** iOS local favorites with persistence and UI tests.
- **C:** parallel UI, service, persistence, and tests.
- **D:** deliberately omitted migration task.
- **E:** deliberately overlapping tasks.
- **F:** unknown platform constraint requiring deliberation.

## Required states

Applicable initial, loading, content, empty, stale/partial, error, offline, permission, disabled, cancellation, repeated action, relaunch, smallest layout, large text, dark mode, keyboard, and assistive-technology states.

## Environments

### Development

Unsigned local app, fixture repositories, fake providers, optional Ollama.

### QA

`qa` branch, signed QA build when available, clean account, GitHub test repo, approved provider accounts, simulator/browser fixtures.

### Release

`main` candidate, release configuration, Developer ID signed and notarized, clean install, prior database migration, benchmark subset.

## Evidence

Every check records feature/task, revision, environment/tool versions, command/scenario, timing, result, verifier, and artifact reference. Large raw artifacts stay outside Git; Git stores durable indexes.

## Required commands before feature coding

The scaffold must define exact commands for formatting, linting, schema validation, frontend tests, Rust tests, integration tests, development launch, and production build. Do not invent commands before manifests exist.

## Failure policy

A failed required check blocks acceptance. A missing environment produces `verification_pending`, not pass. Waivers follow `quality/waivers/README.md`.

## Test-readiness exit

Fixture CLI, fake provider, temp Git harness, SQLite migrations, frontend test, packaged-app smoke, deterministic CI, and evidence format must be demonstrated.
