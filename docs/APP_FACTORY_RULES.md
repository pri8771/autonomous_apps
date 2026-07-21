---
id: DOC-APP-FACTORY-RULES
canonicalFor: local-engineering-rules
status: active
owners: [product, engineering, quality]
readWhen:
  - planning or executing any work
  - reviewing completion
  - handling a discovery or failure
related:
  - ../AGENTS.md
  - docs/WORKFLOW_ENGINE.md
  - docs/TEST_PLAN.md
  - planning/READINESS_GATE.md
supersedes: []
---

# App Factory Rules

## Purpose

These are the non-negotiable local rules for building Autonomous Apps and for the workflows the finished factory executes. They supplement the locked central standard in `pri8771/iOS_app_factory_rules`.

## Documentation

1. Use the repository map and documentation index before reading or editing.
2. One durable topic has one canonical owner.
3. Separate facts, decisions, assumptions, proposals, risks, bugs, and historical records.
4. Update the feature contract, canonical document, tests, and evidence when behavior changes.
5. Do not store essential project truth only in chat transcripts.
6. Use controlled status terms.
7. Do not mark documentation `verified` without evidence.

## Pre-coding gate

1. No product code begins until `planning/READINESS_GATE.md` is approved.
2. Every V1 feature has an approved contract.
3. Architecture, security, data, test, and release decisions are documented.
4. The master task graph passes structural validation.
5. Repository visibility is resolved before sensitive implementation.
6. The first coding task must be the approved scaffold milestone, not opportunistic feature work.

## Planning

1. Every requirement maps to one or more tasks.
2. Every task has acceptance criteria, inputs, outputs, dependencies, expected scope, required reviews, estimate, confidence, and owner role.
3. Plans are dependency graphs, not flat backlogs.
4. Planning uses independent decomposition, adversarial review, synthesis, compilation, and approval.
5. Plans include implementation, tests, error states, accessibility, security, observability, documentation, migration, and release work where applicable.
6. Plans are versioned; accepted changes never overwrite history.
7. Low-confidence or unresolved work becomes an investigation or decision task before dependent implementation.
8. The plan compiler rejects missing verification, cycles, unresolved ownership, and omitted release work.
9. Estimates are forecasts, not commitments; actuals must be recorded.

## Branching and repositories

1. Start work from `dev`.
2. Use one feature or task branch per bounded change.
3. Open reviewed pull requests into `dev`.
4. Promote `dev → qa`, then `qa → main`.
5. Agents never modify `dev`, `qa`, or `main` directly.
6. Coding tasks use isolated Git worktrees.
7. Do not force push protected branches.
8. Do not mix unrelated changes.
9. Preserve commit, diff, build, test, and review evidence.
10. Verify the remote and target branch before push, pull request, merge, or promotion.

## Execution

1. An agent run is an independent scheduled job, not a turn in a global loop.
2. Workers claim ready tasks independently.
3. There are no global worker rounds.
4. A worker that finishes early immediately becomes eligible for other compatible ready work.
5. Parallelism is constrained by dependencies, expected write scope, WIP, worker capacity, hardware, budget, and policy.
6. Interface contracts precede high-overlap parallel work.
7. Every coding run has a task branch, worktree, scoped tools, context manifest, timeout, and cancellation path.
8. Long-running work persists state and reconciles after restart.
9. Agents communicate asynchronously by default.
10. Bounded deliberation is reserved for consequential uncertainty.
11. Parent and subagent creation obeys depth, count, concurrency, role, provider, time, and cost limits.
12. No process may outlive its owning run without explicit daemon policy.

## Model and CLI rules

1. All model traffic passes through the model gateway.
2. Local-only mode is enforced by code, not prompts.
3. Fallback may not weaken privacy or provider constraints.
4. Model output is untrusted until schema and policy validation.
5. CLI agents run in separate processes and worktrees.
6. Environment variables are sanitized.
7. Executable versions are recorded.
8. Model downloads and removals require explicit user action.
9. Raw secrets are never placed in prompts.
10. Independent reviewers should use a different run and, when useful, a different model family.

## Verification

1. Agent statements are not evidence.
2. Builds, tests, diffs, screenshots, logs, accepted decisions, and independent reviews are evidence.
3. The author cannot be the only reviewer.
4. Reviews and tests fan out in parallel when possible.
5. Required evidence must pass before a task is accepted.
6. A screen is not a complete feature.
7. Never implement only the happy path.
8. Every applicable feature handles initial, loading, content, empty, stale/partial, error, offline, permission, disabled, cancellation, repeated action, and recovery states.
9. No undisclosed fake data or placeholder behavior reaches production.
10. Missing checks produce `verification_pending`, never a false pass.
11. Repair attempts are bounded and preserve complete diagnostics.
12. A waiver must be explicit, approved, scoped, and expiring.

## macOS application quality

1. The interface remains responsive during models, builds, Git, and subprocess work.
2. Support compact, standard, expanded, short-height, and full-screen layouts.
3. Reflow and scroll before truncating important actions or status.
4. Support keyboard navigation, visible focus, VoiceOver, reduced motion, dark mode, and non-color status indicators.
5. Use native menus, pickers, notifications, and Keychain where appropriate.
6. Quit with active work requires an explicit recovery choice.
7. Window restoration must not persist secrets.
8. Release builds are signed, hardened, notarized, and tested on a clean account.

## Security

1. Default deny.
2. Tools and paths are task-scoped.
3. Repository content and model output cannot override policy.
4. No raw secrets in database, prompts, logs, or ordinary artifacts.
5. Use Keychain references.
6. Destructive or externally visible actions require policy and audit.
7. High-impact actions require human approval in V1.
8. Validate paths, executable locations, endpoints, and remote repositories.
9. Deny `sudo` and privilege escalation by default.
10. Redact diagnostic exports.
11. Do not commit credentials regardless of repository visibility.
12. Resolve public/private repository intent before sensitive implementation.

## Changes

1. Newly discovered necessary work becomes a formal change request.
2. Change requests classify cause, facts, uncertainty, impact, affected work, graph patch, and root cause.
3. Distinguish planning omission, scope change, technical discovery, implementation defect, architecture correction, external change, and infrastructure failure.
4. Only affected work pauses.
5. Unrelated work continues.
6. Accepted changes update the graph atomically and create a new plan version.
7. Repairs do not silently change scope or acceptance criteria.
8. Invalidated work and sunk cost remain visible.

## Learning

1. Record every unplanned task, missed dependency, estimate error, rework event, repair attempt, review escape, and human intervention.
2. Compare original plan with actual execution.
3. Record where an issue should have been detected.
4. Repeated mistakes may propose explicit planning rules.
5. Lessons are scoped as project-local, template-level, or factory-wide.
6. Rule promotion requires evidence and configured approval.
7. Optimize accepted output, not raw agent activity or token count.

## Approvals

Human approval is required in V1 for final plan, major scope or architecture change, new paid services, sensitive credentials, destructive data operations, production deployment, signing/notarization credentials, TestFlight or App Store submission, and promotion from `qa` to `main`.

## Completion

Work is accepted only when the approved scope is satisfied, required evidence exists, required reviews pass, documentation is current, blockers are disclosed, change requests are resolved, the completion report is valid, and the next state is recorded.
