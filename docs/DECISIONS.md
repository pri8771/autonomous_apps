---
id: DOC-DECISIONS
canonicalFor: accepted-decisions
status: active
owners: [product, engineering]
readWhen:
  - making or revisiting a durable decision
  - planning architecture work
related:
  - docs/PRODUCT.md
  - docs/ARCHITECTURE.md
  - docs/ASSUMPTIONS.md
supersedes: []
---

# Decisions

## Decision policy

A decision is current only when marked `accepted`. Proposals and assumptions are not current behavior. Material changes require a new decision or change request; do not rewrite history.

## DEC-001 — App Factory registration

- **Status:** accepted
- **Decision:** Use `.factory/project-context.json` as authoritative project classification and `pri8771/iOS_app_factory_rules` version `0.4.0` as the locked standard.

## DEC-002 — Product form

- **Status:** accepted
- **Decision:** Build a desktop-first macOS application with a web-technology interface.
- **Reason:** A pure browser application cannot directly manage local CLIs, worktrees, local models, Xcode, simulators, Keychain, and long-running subprocesses without an additional local service.

## DEC-003 — Desktop framework

- **Status:** accepted
- **Decision:** Use Tauri 2 with React, TypeScript, and Vite.
- **Consequence:** The webview is presentation; Rust commands and capabilities mediate native access.

## DEC-004 — Control-plane language

- **Status:** accepted
- **Decision:** Implement the local control plane and initial worker runtime in Rust.
- **Consequence:** Python is not a required bundled runtime. Sidecars require a later accepted decision.

## DEC-005 — Persistence

- **Status:** accepted
- **Decision:** Use SQLite with versioned migrations, foreign keys, transactional transitions, and append-only event history.
- **Consequence:** Postgres and Redis are not V1 dependencies.

## DEC-006 — Workflow durability

- **Status:** accepted
- **Decision:** Implement a bounded durable state-machine/workflow engine persisted in SQLite for V1.
- **Consequence:** Server-oriented workflow infrastructure is deferred.

## DEC-007 — Distribution

- **Status:** accepted
- **Decision:** Distribute V1 outside the Mac App Store using Developer ID signing, Hardened Runtime, and notarization.

## DEC-008 — Supported Macs

- **Status:** accepted
- **Decision:** Support Apple Silicon Macs running macOS 14 or later for V1. Intel is not required.

## DEC-009 — Branch strategy

- **Status:** accepted
- **Decision:** Task branches from `dev`; promote `dev → qa → main` through reviewed pull requests. Agents never write protected branches directly.

## DEC-010 — Repository architecture

- **Status:** accepted
- **Decision:** Build a private modular monolith with explicit internal contracts and no public extension SDK.

## DEC-011 — Initial local runtime

- **Status:** accepted
- **Decision:** Support Ollama first, then generic OpenAI-compatible local endpoints. V1 manages models through an installed runtime.

## DEC-012 — Model policy

- **Status:** accepted
- **Decision:** Allow exact or policy-based cloud/local selection per role and workflow; enforce local-only mode in code.

## DEC-013 — Agent collaboration

- **Status:** accepted
- **Decision:** Use asynchronous blackboard/direct messages by default and bounded deliberation only for consequential uncertainty.

## DEC-014 — Completion standard

- **Status:** accepted
- **Decision:** Completion requires deterministic checks and independent evidence. Agent self-report never closes a task.

## DEC-015 — Initial user model

- **Status:** accepted
- **Decision:** V1 is a single-user local application. Shared remote collaboration is post-V1.

## DEC-016 — Repository visibility

- **Status:** pending_user_action
- **Context:** The repository is currently public while the intended product is private.
- **Decision needed:** Intentionally keep it public or make it private before proprietary code, prompts, provider configuration, or sensitive artifacts are committed.
- **Consequence:** Sensitive implementation remains blocked. Secrets are forbidden in either case.
