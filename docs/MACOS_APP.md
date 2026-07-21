---
id: DOC-MACOS-APP
canonicalFor: macos-product-behavior
status: active
owners: [product, design, engineering]
readWhen:
  - changing desktop behavior
  - adding native integrations
  - preparing distribution
related:
  - docs/PRODUCT.md
  - docs/ARCHITECTURE.md
  - docs/SECURITY.md
  - docs/TEST_PLAN.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
---

# macOS Application

## Purpose

Define how Autonomous Apps behaves as a macOS product, including navigation, windows, local integrations, accessibility, lifecycle, and distribution.

## Current summary

Autonomous Apps is a desktop-first macOS application. Its UI uses React and Vite inside Tauri, while Rust owns system access and long-running execution. The app is designed for sustained operational use rather than a single chat session.

## Supported platform

- Apple Silicon.
- macOS 14 or later.
- Xcode is optional for factory administration but required for iOS build and simulator workflows.
- Git is required for code-execution workflows.
- Docker and local model runtimes are optional capabilities detected at runtime.

Unsupported systems must fail with a clear compatibility message rather than partial or misleading behavior.

## Primary navigation

1. **Portfolio** — all managed projects and health.
2. **Project Command Center** — one project’s plan, tasks, runs, reviews, changes, and releases.
3. **Factory Activity** — all active and queued work.
4. **Approvals** — actions requiring human authority.
5. **Models** — cloud and local model configuration, installation, health, and benchmarks.
6. **Workflows** — workflow definitions and run history.
7. **Roles and Teams** — reusable agent configuration.
8. **Settings** — repositories, tools, credentials, privacy, budgets, and diagnostics.

V1 must work correctly in one main window. Additional windows are later enhancements.

## Project command center sections

- Overview.
- Product and requirements.
- Plan and dependency graph.
- Tasks.
- Agent activity.
- Messages and deliberations.
- Pull requests and branches.
- Builds and tests.
- Evidence and completion reports.
- Change requests.
- Decisions, assumptions, and risks.
- Costs and model usage.
- Releases.

## Window and layout behavior

- Define a minimum usable window size during the UI scaffold.
- Support compact, standard, expanded, full-screen, and short-height layouts.
- Reflow and scroll before truncating important information.
- Keep primary actions, errors, blockers, and approval consequences reachable.
- Persist useful window size, sidebar state, selected project, and filters.
- Do not persist secrets or sensitive prompt content in ordinary restoration state.

## macOS conventions

- Provide native application, File, Edit, View, Window, and Help menus where applicable.
- Use keyboard shortcuts for common navigation and safe actions.
- Use standard file and folder pickers.
- Use notifications only for meaningful background events.
- Make dock, menu-bar, and quit behavior appropriate for long-running work.
- Do not terminate managed subprocesses merely because the main window closes unless explicitly configured.

## Background execution

V1 background work runs while the app process is active.

When the user quits with active work, offer:

- Cancel work and quit.
- Leave work in a recoverable interrupted state and quit.
- Return to the app.

The app reconciles interrupted workflows at next launch. A separate always-on daemon is a later capability.

## Local tool discovery

Detect, version, and health-check Git, Xcode, simulator tooling, Docker-compatible runtime, required package managers, supported coding CLIs, Ollama/local endpoints, and browsers. Detection does not imply permission to execute.

## File-system access

- Users explicitly select repository and workspace locations.
- Task agents receive only relevant project and worktree paths.
- The app does not scan the entire home directory.
- Large artifacts live under Application Support or user-selected storage, not Git by default.

## Credentials and Keychain

Provider keys, Git credentials, signing references, and service tokens use macOS Keychain-backed storage. The UI may show safe metadata but must not reveal secrets after entry.

## Local model experience

The Model Center must detect the runtime, show installed models, accept supported model names, show storage and memory guidance, pull with cancellable progress, run health checks and benchmarks, assign models to roles, warn about resource pressure, and require confirmation before downloads or removal.

## Accessibility

- VoiceOver-compatible labels, roles, values, and focus order.
- Full keyboard navigation for primary workflows.
- Visible focus.
- Reduced motion.
- Sufficient contrast.
- Non-color status indicators.
- Text scaling where supported.
- Accessible graph alternatives such as tables or ordered dependency lists.
- Useful announcements for material background changes without excessive noise.

## Appearance

Support light, dark, and system appearance. Dense operational views may offer comfortable and compact density, but the default remains readable.

## Error and recovery behavior

Associate failures with the operation that caused them. Preserve user input where recovery is possible. Separate cancellation, offline state, missing tools, permission denial, policy denial, and execution failure. Never expose raw credentials, full prompts, stack traces, or private absolute paths in user-facing errors. Provide a copyable redacted diagnostic package.

## Performance expectations

- Main interface remains responsive during agents, models, builds, and Git operations.
- Large logs are virtualized and paged.
- Task graphs load incrementally for large projects.
- Background events may be batched without losing audit records.
- Resource-intensive inference shows queue and memory pressure.

## Privacy modes

### Standard local-first

Project state and execution remain local. Explicit cloud integrations may receive task-relevant content.

### Local-only

Model inference, embeddings, and prompt telemetry stay local. The model gateway rejects external provider requests. Git and other network integrations have separate policies.

## Distribution

V1 uses direct distribution outside the Mac App Store with Developer ID signing, Hardened Runtime, notarization, and a signed package. Automatic update is deferred until update signing, schema migration, interruption safety, and rollback are verified.

## Diagnostics

Provide runtime versions, database schema version, tool status, worker and model health, redacted logs, storage use, app-owned processes, recovery actions, and an exportable redacted bundle.
