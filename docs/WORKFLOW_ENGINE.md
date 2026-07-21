---
id: DOC-WORKFLOW-ENGINE
canonicalFor: workflow-task-agent-semantics
status: active
owners: [engineering, product]
readWhen:
  - changing workflow behavior
  - adding task states
  - implementing agent collaboration
related:
  - docs/CONCURRENCY_MODEL.md
  - docs/DATA_MODEL.md
  - docs/APP_FACTORY_RULES.md
  - planning/PROJECT_GRAPH.yaml
supersedes: []
---

# Workflow Engine

## Purpose

Define the durable workflow, task, agent, review, repair, deliberation, and change-request semantics used by Autonomous Apps.

## Current summary

A project is a versioned dependency graph plus durable workflow runs. Agents are independently scheduled workers. Conversations are supporting artifacts, not the source of truth.

## Core objects

Project, requirement, feature, plan version, task, dependency, workflow definition/run/step, role, agent instance/run, message, deliberation, review, test run, evidence, change request, decision, approval, planning error, and learning rule.

## Plan creation protocol

1. Capture scope, constraints, assumptions, and target outcome.
2. Run independent planning passes in parallel.
3. Reveal proposals only after independent responses finish.
4. Run an adversarial planning review.
5. Synthesize a proposed plan.
6. Compile the plan against structural rules.
7. Resolve errors and required decisions.
8. Present impact, uncertainty, risks, and low-confidence work.
9. Obtain required approval.
10. Create an immutable approved plan version.

## Plan compiler checks

- Every requirement maps to tasks.
- Every task has acceptance criteria, inputs, outputs, dependencies, expected scope, reviews, estimate, confidence, and owner.
- Every implementation task has verification.
- UI features include applicable initial, loading, content, empty, error, offline, permission, disabled, and cancellation states.
- Persisted-data changes consider migration and recovery.
- External integrations include timeout, retry, quota, privacy, and credentials.
- Sensitive capabilities have security review.
- Dependency references exist and no cycles exist.
- Outputs have consumers or explicit terminal purpose.
- Unresolved decisions block dependent work.
- Write conflicts are identified.
- Release and rollback work is represented.

## Task lifecycle

```text
draft
planning_review
ready
claimed
in_progress
blocked
discussion_required
change_proposed
implementation_complete
review_queued
under_review
changes_requested
verification_queued
under_verification
integration_queued
integrated
accepted
released
invalidated
cancelled
```

Tasks may expose parallel implementation, review, test, security, integration, and release facets. Aggregate state is derived, not hand-edited.

## Readiness

A task is ready only when its plan is active, dependencies and decisions are satisfied, required inputs exist, no policy hold exists, a compatible worker can eventually execute it, and it has not been invalidated.

## Claims and leases

Claims are atomic. A task has one active execution claim unless redundant independent solutions are explicitly requested. Leases identify worker, run, worktree, resources, and expiration. Expiry triggers reconciliation before retry. Duplicate completion events are idempotent.

## Task completion

Acceptance requires expected outputs, deterministic checks, independent reviews, criterion evidence, resolved blocking findings, required integration, and a valid completion report.

## Agent run protocol

Resolve role and model policy; assemble the smallest relevant context; grant scoped tools; create or attach worktree; start model or CLI; stream events; validate output; collect changes; release resources; trigger next transitions.

## Context package

May include factory rules, project context, assigned task, requirements, feature contract, accepted decisions, interfaces, relevant code/tests, recent failures, tools, budgets, and deadlines. It excludes unrelated repository contents and raw secrets.

## Parent and subagent protocol

Child requests declare purpose, role, task, capabilities, tools, model policy, limits, and expected output. Policy limits depth, children, concurrency, roles, providers, runtime, and cost. Children are independent runs with attributable evidence.

## Collaboration patterns

Supervisor, pipeline, parallel experts, bounded debate, blackboard, swarm, and review fan-out. Each workflow chooses explicitly.

## Direct messages

Messages include sender, recipient/topic, task, type, blocking status, requested response, urgency, and canonical resolution. One task facet may block without stopping unrelated work.

## Deliberation rooms

Use for architecture conflict, requirement contradiction, platform constraint, major debugging uncertainty, high-impact changes, and security/release decisions.

1. Create a fact package.
2. Collect independent positions in parallel.
3. Reveal them together.
4. Run one or two bounded response rounds.
5. Record options, tradeoffs, dissent, confidence, and recommendation.
6. Apply approval policy.
7. Update decisions and tasks.

Rooms have participant, round, token, time, and cost limits.

## Failure classification

Known issue, known unknown, unknown unknown, implementation defect, planning omission, scope change, architecture correction, external change, infrastructure failure, policy denial, budget exhaustion, or human input required.

## Repair protocol

Preserve failure evidence; diagnose; decide repair versus change; create bounded repair work; rerun affected checks; increment limits; accept or escalate. Repairs may not silently alter scope or acceptance criteria.

## Change-request protocol

A request declares source, classification, facts, uncertainty, proposed task and dependency changes, cost/schedule/risk impact, affected completed work, root cause, and approval policy. Approval applies the graph patch transactionally and creates a new plan version.

## Plan versions

Approved versions are immutable. New versions reference predecessors and accepted changes. Tasks retain origin version. Invalidated work and sunk cost remain visible.

## Integration

Task branches do not merge directly to protected branches. Integration work collects accepted branches, classifies conflicts, runs combined tests, and creates repair or change work as needed. Evidence-backed integration branches may target `dev`.

## Workflow terminal states

`succeeded`, `succeeded_with_warning`, `failed_retryable`, `failed_needs_specification`, `failed_needs_human`, `blocked_by_policy`, `budget_exhausted`, or `cancelled`. Every terminal state records evidence and the next recommended action.
