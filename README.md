# Autonomous Apps

Autonomous Apps is a desktop-first macOS application that operates as a private, local-first software factory for iOS and web products.

It coordinates cloud models, local models, and CLI coding agents to plan work, execute independent tasks in parallel, review and test completed work, repair failures, incorporate newly discovered work through change requests, and deliver evidence-backed pull requests and releases.

## Product form

The primary product is a signed and notarized macOS desktop app built with a web-technology interface:

- Tauri 2 desktop shell and Rust control plane
- React, TypeScript, and Vite user interface
- SQLite local system of record
- Native access to Git, CLIs, local models, Xcode, Keychain, files, and subprocesses
- Optional cloud model and Git hosting integrations
- A future browser companion may reuse the UI, but no browser server is required for V1

## North-star outcome

Given a well-specified feature, the factory produces a reviewed, tested pull request through asynchronous parallel work by multiple independent agents.

## Initial golden path

1. Create or register a product project and repository.
2. Enter a feature specification.
3. Generate, critique, compile, and approve a dependency-aware task graph.
4. Run implementation agents concurrently in isolated Git worktrees.
5. Fan completed work out to independent reviews and tests without blocking implementers.
6. Repair failures automatically within bounded limits.
7. Record newly discovered work as formal change requests.
8. Apply accepted changes to a new version of the project graph while unrelated work continues.
9. Integrate approved branches and create an evidence-backed pull request.
10. Record planning omissions, estimate errors, rework, model performance, and human interventions.

## Repository workflow

```text
feature or task branch
        ↓
       dev
        ↓
       qa
        ↓
      main
```

All implementation and documentation work starts from `dev`. Promotion to `qa` and `main` occurs through reviewed pull requests with the required evidence.

## Documentation fast path

1. `AGENTS.md`
2. `.factory/repository-map.json`
3. `.factory/project-context.json`
4. `.factory/standard-lock.json`
5. `docs/README.md`
6. Only the canonical documents and feature contracts relevant to the task

## Current status

`planned`

The product scope, platform choice, architecture, rules, feature inventory, test strategy, risks, decisions, and dependency-aware task graph are being finalized. No product code should begin until the pre-coding readiness gate in `planning/READINESS_GATE.md` is approved.
