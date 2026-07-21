---
id: DOC-CONCURRENCY
canonicalFor: parallel-scheduling
status: active
owners: [engineering]
readWhen:
  - implementing the scheduler
  - changing worker capacity
  - debugging blocked or duplicate work
related:
  - docs/WORKFLOW_ENGINE.md
  - docs/DATA_MODEL.md
  - docs/TEST_PLAN.md
supersedes: []
---

# Concurrency Model

## Purpose

Define how Autonomous Apps runs many agents, reviews, tests, local models, CLIs, and builds concurrently without global rounds or uncontrolled conflicts.

## Current summary

The scheduler is event-driven. Workers independently claim compatible ready work. A worker that finishes early immediately becomes eligible for new work. Reviews begin as soon as an implementation produces sufficient evidence. Global synchronization is forbidden unless a workflow explicitly defines a fan-in barrier.

## Scheduling goals

Optimize accepted throughput, critical-path reduction, blocker removal, low conflict, balanced review capacity, bounded WIP, hardware safety, budget safety, and fairness. Do not optimize only for maximum utilization.

## Scheduling loop

```text
persisted event or timer
  → reconcile state
  → recalculate ready work
  → rank tasks
  → find compatible capacity
  → atomically claim task and resources
  → start execution
  → react to individual events
```

The loop never waits for all current workers to finish.

## Priority factors

Explicit product priority, critical path, work unblocked, age, blocking review/integration, deadline, reviewer availability, resource availability, conflict risk, uncertainty, expected duration, and budget. The formula must be observable and testable.

## Worker pools

Planning, architecture, control-plane implementation, UI, iOS, web, review, tests, security, accessibility/visual, integration, release, local inference, cloud requests, CLI processes, Xcode builds, and browser tests.

## Atomic claims

A database transaction verifies current readiness, no conflicting claim, worker eligibility, resource availability, WIP, active plan, and policy; then creates the lease and state transition.

## Leases and heartbeats

A lease contains task, worker, run, worktree, reserved resources, timestamps, expiration, and cancellation. Expiry triggers process/worktree/commit reconciliation before another run starts.

## No global rounds

Forbidden:

```text
A, B, C start
A finishes
A waits for B and C
all roles switch together
```

Required:

```text
A finishes
A's reviews start
A claims another task
B and C continue
reviewers claim work when available
```

## Review parallelism

After implementation, build, tests, code review, specification review, security, accessibility, visual, and integration checks fan out independently. The gate waits only for required checks.

## Work-in-progress limits

Apply by project, subsystem, repository, file/symbol hotspot, workflow phase, worker pool, local model runtime, Xcode runner, and browser runner. Core schemas and migrations have lower concurrency than isolated edge work.

## Expected write scopes and conflicts

Tasks declare expected repository, module, directory, files, symbols, tables, migrations, and interfaces. Actual changes are compared with the prediction.

- Low overlap: run concurrently.
- Moderate overlap: run against accepted interfaces with early rebases.
- High overlap: sequence or assign an integration owner.
- Architectural hotspot: block dependent work until a contract is accepted.

## Interface-first parallelism

Lock applicable protocols, API schemas, database schemas, events, component interfaces, error types, and state ownership before high-overlap implementation.

## Resource reservations

CPU, memory, GPU/unified memory, disk, model slots, loaded model state, PTY/process slots, Xcode slots, simulators, browsers, network/provider limits, and monetary budget.

## Local model scheduling

Consider model size, memory, context, loaded state, measured speed, active inference, thermal/memory pressure, and user concurrency. The scheduler may queue, reuse, unload, or choose an allowed alternative, but may not violate exact-model or local-only policy.

## Backpressure

When review queues, disk, memory, runners, rate limits, error rate, repair rate, or budget burn exceed thresholds, reduce new implementation and prioritize review, repair, integration, or cleanup.

## Fairness and starvation

Aging raises priority. Every waiting task exposes a reason: dependency, policy, worker, resource, WIP, conflict, budget, approval, or lower priority.

## Cancellation

Mark requested; signal process; stop descendants after grace; preserve logs and changes; reconcile worktree; release resources; mark terminal or recoverable state.

## Sleep and wake

Sleep does not immediately duplicate work. On wake, reconcile processes and leases. Cloud requests with unknown outcomes require idempotent recovery.

## Deterministic concurrency tests

- Two workers race for one task.
- One worker completes many short tasks while others run long tasks.
- Review starts before sibling implementation finishes.
- Lease expiry and late heartbeat.
- App restart during claims.
- Duplicate completion.
- WIP and resource conflicts.
- Scope conflict escalation.
- Review backpressure.
- Local-model memory limits.
- Process-tree cancellation.
- Plan changes invalidating work.

## Required observability

Ready queue, priorities and reasons, active leases, worker/resource capacity, review age, WIP, backpressure, conflict holds, retries, throughput, blocked time, and scheduling explanations.
