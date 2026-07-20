# Product Definition

## Product

Autonomous Apps is a private control plane for coordinating cloud and local LLMs that plan, implement, review, test, and integrate software work across iOS and web projects.

## North-star outcome

Given a well-specified feature, produce a reviewed and tested pull request through asynchronous parallel work by multiple independent agents.

## Primary users

- A solo builder operating several software products.
- A technical team that wants configurable agent roles, model routing, and automated verification.

## V1 scope

- Project and repository registration.
- Requirements, features, tasks, and dependency graph.
- Plan generation, critique, compilation, and human approval.
- Configurable roles, models, effort, and local-only policy.
- Isolated Git worktrees and CLI agent execution.
- Event-driven parallel scheduling without global rounds.
- Parallel review and test fan-out.
- Bounded repair loops.
- Agent messages and bounded deliberation rooms.
- Change requests and atomic plan updates.
- Planning-error and execution-learning ledger.
- Local model integration beginning with Ollama.

## Non-goals for V1

- Public plugin ecosystem or marketplace.
- Fully autonomous production deployment.
- Automatic App Store submission.
- Kubernetes-based infrastructure.
- Unlimited recursive agent swarms.
- Marketing automation.
- Multi-tenant enterprise billing.

## Success criteria

The first release must complete an end-to-end benchmark where several agents implement independent subtasks concurrently, reviewers inspect completed work without blocking implementers, a discovered omission updates the plan through a change request, failed checks are repaired, and a final evidence-backed pull request is created.
