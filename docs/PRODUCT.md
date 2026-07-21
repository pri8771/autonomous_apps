---
id: DOC-PRODUCT
canonicalFor: product-scope
status: active
owners: [product]
readWhen:
  - changing product scope
  - planning a release
  - creating feature contracts
related:
  - docs/FEATURES.md
  - docs/ROADMAP.md
  - planning/PROJECT_GRAPH.yaml
supersedes: []
---

# Product Definition

## Purpose

Define the approved product, user, boundaries, success criteria, and release sequence for Autonomous Apps.

## Authority and scope

This document owns product scope. Architecture details belong in `docs/ARCHITECTURE.md`; feature-specific behavior belongs in `quality/feature-contracts/`.

## Current summary

Autonomous Apps is a private, desktop-first macOS application that acts as a local software-development control plane. It plans, builds, reviews, tests, repairs, integrates, and prepares releases for iOS and web products using multiple cloud models, local models, and CLI coding agents.

The app is not a generic chat interface. It is an evidence-based production system whose authoritative state is a versioned project graph, workflow history, source-control evidence, and verification results.

## Primary users

### Initial user

A technical solo builder operating several iOS and web products from a Mac.

### Later users

Small engineering teams that want configurable agent roles, model policies, parallel execution, reproducible reviews, and controlled release promotion.

Multi-user collaboration and enterprise tenancy are not V1 requirements.

## Jobs to be done

The user must be able to:

1. Register a new or existing software project.
2. Define a product goal or feature request.
3. Receive a complete, dependency-aware implementation plan.
4. Inspect assumptions, risks, acceptance criteria, and likely file conflicts before execution.
5. Select cloud, local, CLI, or local-only execution policies.
6. Run many independent tasks concurrently without synchronized rounds.
7. Observe live agent activity, questions, resource use, and blockers.
8. Require independent reviews and deterministic checks.
9. Allow bounded repair without permitting endless loops.
10. Accept or reject changes to the approved plan.
11. Produce an evidence-backed pull request or release candidate.
12. Learn why the original plan, estimates, or execution failed and improve future planning.

## Product form

### Approved V1 form

A macOS desktop application built with:

- Tauri 2 as the native shell
- Rust as the local control plane and privileged system layer
- React, TypeScript, and Vite as the user interface
- SQLite as the embedded system of record

The application runs without a required hosted backend. Cloud services are integrations, not prerequisites.

### Future form

A browser companion may connect to the local or remote control plane and reuse the web interface. It is not required for V1 and must not weaken local-only guarantees.

## Product principles

1. **Evidence over claims.** An agent saying “done” is not completion.
2. **Asynchronous flow over rounds.** Fast workers continue while long tasks and reviews remain in progress.
3. **Plans are versioned graphs.** Tasks, dependencies, decisions, and changes are auditable.
4. **Local-first control.** Source code, prompts, credentials, task state, and artifacts stay local unless a configured integration requires otherwise.
5. **Explicit authority.** Agents receive task-scoped tools and cannot silently expand permissions.
6. **Independent verification.** Authors cannot be the only reviewers of consequential work.
7. **Bounded autonomy.** Budgets, retries, hierarchy depth, and approval policies constrain execution.
8. **Continuous learning.** Planning omissions and execution errors become structured data and reusable rules.
9. **Reuse before reinvention.** Existing approved libraries and product modules are considered before new cross-cutting infrastructure.
10. **Truthful UX.** The interface exposes actual status, uncertainty, failures, and unverified behavior.

## Final capability scope

### Project intake and registration

- Create or onboard projects.
- Connect local repositories and GitHub repositories.
- Classify projects as new or existing.
- Configure target platforms, repository paths, branch strategy, environments, budgets, privacy mode, models, and approval rules.
- Generate and maintain required project documentation.

### Product and technical planning

- Capture goals, requirements, user journeys, non-functional requirements, interfaces, data models, tests, security needs, operational work, and release work.
- Use several planners independently, followed by critique and synthesis.
- Compile the plan before approval.
- Reject missing requirements, cycles, missing verification, unsupported assumptions, and unresolved ownership.

### Project graph and task lifecycle

- Store requirements, features, tasks, dependencies, expected scopes, acceptance criteria, estimates, confidence, owners, reviews, and evidence requirements.
- Calculate ready, blocked, invalidated, review-pending, verification-pending, and completed work deterministically.
- Preserve every plan version.

### Agent roles and teams

- Create reusable roles with instructions, responsibilities, inputs, outputs, tool permissions, model policies, review duties, and escalation behavior.
- Configure team size and collaboration pattern per workflow step.
- Allow parent agents to create real subagents within explicit limits.
- Track every parent-child relationship, purpose, cost, result, and acceptance decision.

### Model and CLI execution

- Support cloud model APIs, OpenAI-compatible endpoints, local runtimes, and CLI coding agents.
- Allow per-role and per-task model, effort, context, timeout, fallback, and budget selection.
- Enforce project-level local-only mode at the gateway.
- Stream output and preserve structured run histories.

### Local model center

- Detect supported runtimes.
- List installed and available models.
- Pull, update, stop, benchmark, and remove models with user approval.
- Display memory, storage, context, capability, and measured performance.
- Schedule local inference according to machine capacity.
- Begin with Ollama; add generic OpenAI-compatible local endpoints and other runtimes later.

### Git and workspace isolation

- Create one task branch and worktree per coding task.
- Prevent direct writes to `dev`, `qa`, and `main`.
- Estimate write footprints and conflict risk.
- Rebase or merge current base state into long-lived task branches.
- Integrate related tasks through temporary integration branches when needed.

### Parallel scheduling

- Claim tasks atomically.
- Use leases, heartbeats, retries, priorities, worker compatibility, critical-path impact, conflict risk, and work-in-progress limits.
- Let workers claim new ready work immediately after completion.
- Schedule reviews as soon as evidence becomes available.
- Avoid global barriers.

### Agent communication

- Shared blackboard for durable facts and findings.
- Direct asynchronous messages for focused questions.
- Bounded deliberation rooms for consequential uncertainty.
- Independent first responses before debate to reduce anchoring.
- A canonical decision, dissent record, confidence, and follow-up tasks.

### Review, testing, and evidence

- Fan completed work out to code review, specification review, tests, security review, accessibility review, visual review, and integration review as applicable.
- Require deterministic checks where software can decide.
- Store completion reports with commits, diffs, tests, reviews, screenshots, risks, costs, and run metadata.

### Repair and escalation

- Classify failures.
- Generate bounded repair tasks.
- Preserve diagnostics and previous attempts.
- Stop at configured limits and create a human-readable escalation package.

### Change requests and replanning

- Require formal change requests for newly discovered work, scope changes, architecture corrections, external changes, and planning omissions.
- Analyze cost, schedule, risk, dependency, and completed-work impact.
- Update the plan atomically after approval.
- Pause only affected work.

### iOS delivery support

- Swift and SwiftUI repositories.
- Xcode and Swift Package Manager.
- Native macOS build workers.
- Simulator builds, unit tests, UI tests, accessibility checks, screenshots, archive validation, signing preparation, and TestFlight preparation.
- Human approval for signing-sensitive and App Store actions.

### Web delivery support

- Frontend, backend, API, database, and authenticated application repositories.
- Containers, migrations, browser tests, accessibility, visual checks, previews, staging, health checks, deployment preparation, and rollback verification.
- Human approval for production release initially.

### Approvals and release promotion

- Central approval inbox.
- Policy-driven approval requirements for plans, architecture, costs, secrets, destructive actions, merges, environment promotion, production deployment, and App Store submission.
- Default branch flow: task branch → `dev` → `qa` → `main`.

### Learning and optimization

- Record unplanned tasks, bad estimates, missed dependencies, rework, repair attempts, review escapes, model outcomes, cost, latency, and human intervention.
- Convert repeated evidence into project-local, template-level, or factory-wide planning rules.
- Improve model routing, task decomposition, review requirements, and scheduling.

## V1 boundary

V1 is complete when the macOS app can execute this benchmark:

1. Register a repository.
2. Capture one feature specification.
3. Generate and approve a dependency-aware plan.
4. Run at least three independent implementation tasks concurrently.
5. Let an early-finishing worker continue to new work without waiting.
6. Trigger independent reviews and tests as each task completes.
7. Detect one deliberately introduced failure and repair it within limits.
8. Detect one deliberately omitted task and create a formal change request.
9. Update the graph without stopping unrelated work.
10. Integrate accepted branches and create an evidence-backed pull request.
11. Show complete run, cost, decision, and planning-error history.

## Post-V1 scope

- Visual workflow designer.
- Rich role and team editors.
- Multi-machine workers.
- Managed local model runtime installation.
- Complete iOS release pipelines.
- Complete web staging and deployment pipelines.
- Product portfolio analytics.
- Feedback ingestion and autonomous iteration.
- Optional browser companion.
- Small-team collaboration.

## Explicit non-goals

- Public plugin ecosystem or marketplace.
- General-purpose AI chat.
- Training a foundation model.
- Unlimited recursive swarms.
- Uncontrolled production credentials.
- Fully autonomous destructive operations.
- Kubernetes-first architecture.
- Multi-tenant SaaS billing.
- Marketing and social-media automation.
- Silent use of cloud services in local-only mode.
- Mac App Store distribution in V1.

## Supported environment decision

V1 targets Apple Silicon Macs running macOS 14 or later. Intel support is not planned for V1. This is a product constraint and may be revisited through a change request.

## Success metrics

- Planning coverage.
- First-pass task acceptance.
- Repair success.
- Merge-conflict rate.
- Review escape rate.
- Cost per accepted task.
- Time spent blocked.
- Human interventions per feature.
- Local versus cloud model outcome by task type.
- Recovery success after app or worker interruption.
- Percentage of accepted tasks with complete evidence.

## Human-controlled actions in V1

- Final plan approval.
- Major scope or architecture changes.
- New paid services.
- Production deployments.
- Destructive data operations.
- Signing and notarization credentials.
- TestFlight and App Store submission.
- Promotion from `qa` to `main`.
