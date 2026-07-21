---
id: DOC-SECURITY
canonicalFor: security-privacy-permissions
status: active
owners: [security, engineering]
readWhen:
  - adding tools or providers
  - changing process or filesystem access
  - handling credentials
  - preparing distribution
related:
  - docs/ARCHITECTURE.md
  - docs/MACOS_APP.md
  - docs/MODEL_SYSTEM.md
  - docs/TEST_PLAN.md
supersedes: []
---

# Security and Privacy

## Purpose

Define the security boundary, trust model, permissions, secrets handling, network policy, subprocess controls, and release protections for Autonomous Apps.

## Current summary

Autonomous Apps combines untrusted model output with powerful local development tools. The Rust/Tauri layer is the privileged boundary. Every agent, model, CLI, workflow, and project receives explicit capabilities. Raw credentials are not given to models. Destructive and externally visible actions require policy authorization.

## Threat model

Protect against malicious model commands, prompt injection, unrelated filesystem access, secret leakage, cloud use in local-only mode, supply-chain compromise, repository corruption, endpoint impersonation, orphan processes, privileged UI misuse, unauthorized release, public-repository disclosure, and tampered application updates.

## Trust boundaries

- **Webview:** presentation only; typed commands, no arbitrary native access.
- **Rust control plane:** validates commands, policy, paths, credentials, and state.
- **Model output:** untrusted.
- **CLIs/tools:** explicitly configured and validated.
- **Repository content:** potentially hostile input and never higher authority than factory policy.
- **Cloud services:** external processors governed by project policy.
- **Local runtimes:** local but still mediated by the gateway.

## Capability model

Examples: repository read, worktree write, Git commit/push, PR creation, process spawn, tests, Xcode, simulator, browser, local/cloud model invocation, network, artifacts, secret use, deployment, and promotion.

Each grant binds project, task/workflow, actor, action, path/endpoint/environment, expiration, budget, and approval. Default deny applies. Prompts cannot grant permissions.

## Filesystem rules

Operate only in registered repositories, task worktrees, factory data, and explicit user locations. Resolve canonical paths; reject traversal and symlink escapes; do not scan the home directory; verify ownership before cleanup.

## Process rules

Resolve and approve executables; use explicit argument vectors and workdirs; sanitize environment; track process trees; apply timeout/output limits; cancel descendants; deny `sudo` and privilege escalation by default.

## Git rules

Never write directly to `dev`, `qa`, or `main`; use task worktrees; verify repository and remote; deny force push on protected branches; do not rewrite unrelated history; audit merge and promotion.

## Secret handling

Use macOS Keychain. SQLite stores references and safe metadata. Models receive secret-backed operations, not values. Redact logs/errors. Never place provider keys in workflows or Git.

## Model privacy

Record provider/endpoint class, local/cloud classification, project privacy mode, context manifest, data classification, policy decision, and redacted usage. Source-sensitive content only goes to allowed endpoints.

## Local-only mode

Disable cloud model adapters, embeddings, and prompt telemetry; deny model-provider network requests outside approved local hosts; sanitize CLI cloud credentials; audit denied attempts. Git and other networks remain separately controlled.

## Network rules

Explicit integration endpoints, TLS for non-loopback, fail closed on certificate errors, validate redirects, limit downloads, verify signatures/checksums where available, and never send source content to analytics.

## Prompt injection protections

Treat repository/web content as data; separate trusted instructions from retrieval; label untrusted content; enforce tools outside the model; require confirmation for scope expansion; preserve provenance; use independent review.

## Model downloads

Before pull, show source/runtime, identifier, size/resource guidance, license/source metadata where available, destination, and confirmation. Removal also requires confirmation.

## Destructive actions

Repository/worktree deletion, database drop, history rewrite, model removal, release cancellation, deployment, App Store actions, and credential changes require explicit tools, impact preview, policy, audit, and human approval when high impact.

## Approval integrity

Approvals bind exact subject/version, evidence snapshot, requested action, environment, expiration, and approver. Material subject change invalidates approval.

## Audit log

Append actor, action, subject, policy result, approval, tool/endpoint, result, correlation ID, timestamp, and redacted metadata.

## macOS distribution security

Developer ID signing, Hardened Runtime, secure timestamp, notarization, entitlement review, embedded-binary validation, no debug-only entitlement, signed updates before auto-update, and clean-account release testing.

## Public repository constraint

The repository is currently public. Before proprietary code, prompts, provider configuration, credentials, or sensitive artifacts are added, intentionally keep it public or make it private and review history. Secrets are forbidden regardless of visibility.

## Security tests

Capability denial, path traversal, symlink escape, environment sanitization, secret redaction, local-only outbound denial, malicious tool request, prompt injection fixture, unauthorized branch write, duplicate destructive action, process-tree cancellation, tampered artifact/update, approval invalidation, database/artifact permission, and notarization/Gatekeeper checks.

## Incident response

Stop scheduling, cancel safely, preserve redacted audit evidence, revoke credentials, quarantine affected components, identify scope, restore known-good state, and record corrective planning rules.
