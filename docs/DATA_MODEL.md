---
id: DOC-DATA-MODEL
canonicalFor: persisted-domain-model
status: active
owners: [engineering]
readWhen:
  - creating database migrations
  - changing task or workflow persistence
  - implementing recovery or analytics
related:
  - docs/ARCHITECTURE.md
  - docs/WORKFLOW_ENGINE.md
  - docs/CONCURRENCY_MODEL.md
  - docs/SECURITY.md
supersedes: []
---

# Data Model

## Purpose

Define the persistent entities, ownership boundaries, event history, artifact references, and retention rules for Autonomous Apps.

## Current summary

SQLite is the local system of record. Domain state and immutable audit events are persisted transactionally. Repositories, worktrees, large logs, screenshots, test bundles, and model files remain outside the database and are referenced by stable artifact records.

## Storage principles

- Versioned migrations, foreign keys, and UTC timestamps.
- Stable opaque IDs.
- SQLite WAL after validation.
- No raw secrets.
- Append-only event and audit records.
- Immutable plan and workflow history.
- Idempotent retryable writes.
- Backup before destructive migration.
- Large binaries outside SQLite.

## Core entities

### Projects and repositories

Project identity, lifecycle, paths, remotes, target platforms, branch policy, environments, privacy, budgets, access, and synchronization.

### Requirements, features, plans, tasks, and dependencies

Requirement source and priority; feature contract and release; immutable plan versions; task lifecycle, estimates, confidence, expected scope, criteria, review policy, inputs/outputs, invalidation; dependency rules and task facets.

### Claims, leases, workers, workspaces, and worktrees

Worker capabilities and health; atomic claims; resources; heartbeats; expiration; process/run/worktree ownership; cleanup state.

### Workflow definitions, versions, runs, and steps

Versioned graph, schemas, input/output references, attempts, timers, failure classification, and terminal state.

### Roles, teams, agent runs, and relationships

Versioned role instructions and policies; teams and hierarchy; parent/child purpose, depth, budget, model, context manifest, tools, timing, cost, and result.

### Messages and deliberations

Sender, recipient/topic, task/run, message type, blocking state, resolution, room facts, participants, independent positions, rounds, synthesis, and decision.

### Models, installations, runtimes, benchmarks, and cost

Provider/runtime, model identity, capabilities, limits, source/license, host installation, health, loaded state, resources, benchmark configuration/results, usage, and cost.

### Git, builds, tests, reviews, evidence, and artifacts

Branches, commits, pull requests, command definitions, environments, logs, results, findings, resolutions, criterion evidence, completion reports, checksums, sensitivity, retention, and artifact locations.

### Changes, decisions, approvals, risks, assumptions, and learning

Change classification and graph patch; accepted decisions; scoped approvals; risks and assumptions; planning errors; learning-rule proposals; operational metrics.

### Domain and audit events

Immutable transition and actor-action history.

## Event envelope

Every event has ID, schema version, type, project, correlation/causation IDs, actor, subject, UTC timestamp, payload, and sensitivity.

## State and event transaction

1. Validate policy and invariants.
2. Load current state.
3. Apply domain transition.
4. Persist state changes.
5. Append event.
6. Commit.
7. Publish committed event to live subscribers.

Live delivery may retry; the persisted event is authoritative.

## Idempotency

Claims, heartbeats, run completion, test/review result, change application, promotion, and model-download completion use idempotency keys.

## Artifact storage

```text
~/Library/Application Support/Autonomous Apps/
  factory.sqlite
  artifacts/<project>/<type>/<id>/
  logs/<date>/
  workspaces/<project>/
```

User repositories may remain in selected locations.

## Sensitive data

Classify public, internal, source-sensitive, credential, user-private, and security-sensitive data. Credential values belong in Keychain; the database stores identifiers and safe metadata.

## Retention

Retain domain, audit, plan, and completion history. Bound large raw logs and artifacts by policy. PTY transcripts and screenshots are configurable. Failed downloads and orphaned worktrees require safe reconciliation before cleanup.

## Recovery

Detect migration state, back up before irreversible migration, refuse unsupported future schemas, recover failed migration, test prior-version fixtures, and provide redacted diagnostics.

## Analytics

Metrics derive from immutable events and accepted results. Distinguish planned versus added work, planning omission versus requested scope, implementation defect versus infrastructure failure, attempted versus accepted output, local versus cloud execution, and human versus automated decisions.
