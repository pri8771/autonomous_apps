---
id: DOC-RELEASE-CHECKLIST
canonicalFor: release-readiness
status: active
owners: [release, quality, security]
readWhen:
  - promoting to qa
  - preparing a stable build
  - changing signing or updates
related:
  - docs/TEST_PLAN.md
  - docs/SECURITY.md
  - docs/STATUS.md
supersedes: []
---

# Release Checklist

## Promotion to `qa`

- [ ] Source is `dev` and changes arrived through reviewed pull requests.
- [ ] Feature contracts and completion reports are current.
- [ ] Format, lint, schema, unit, integration, and UI suites pass.
- [ ] No protected-branch direct write occurred.
- [ ] Bugs, risks, assumptions, and database migrations are current.
- [ ] Sensitive logs and artifacts are redacted.
- [ ] QA build is reproducible.
- [ ] Rollback or forward recovery exists.

## V1 golden-path gate

- [ ] Project onboarding works.
- [ ] Feature intake creates a valid planning request.
- [ ] Independent planners run in parallel.
- [ ] Plan compiler rejects incomplete work.
- [ ] Human approval activates a plan.
- [ ] At least three implementation tasks run concurrently.
- [ ] A fast worker claims another task without waiting.
- [ ] Reviews and tests fan out as each task completes.
- [ ] A failed task repairs within limits.
- [ ] An omitted task creates a change request.
- [ ] Accepted change updates the graph while unrelated work continues.
- [ ] Integration creates an evidence-backed pull request.
- [ ] Costs, decisions, messages, approvals, and planning errors are visible.
- [ ] App restart recovery is verified during active work.

## Stable macOS build

- [ ] Source is `qa`; target is `main`.
- [ ] Version/build number is unique.
- [ ] Release configuration builds cleanly.
- [ ] Tauri capabilities and macOS entitlements match behavior.
- [ ] No debug-only entitlement.
- [ ] Embedded binaries are identified and signed as needed.
- [ ] Hardened Runtime is enabled.
- [ ] Developer ID signing succeeds.
- [ ] Notarization succeeds and logs are reviewed.
- [ ] Ticket is stapled where applicable.
- [ ] Gatekeeper accepts the package.
- [ ] Clean-account or clean-machine install passes.
- [ ] Updates remain disabled unless signed-update recovery is verified.
- [ ] Application data survives upgrade.
- [ ] Prior database fixtures migrate.
- [ ] Package checksum and release notes exist.

## Product integrity

- [ ] No undisclosed fake data or placeholder controls.
- [ ] No staging endpoints or test credentials.
- [ ] No provider keys or signing material in Git.
- [ ] Local-only tests pass.
- [ ] Destructive actions require policy and confirmation.
- [ ] Diagnostics are redacted.
- [ ] Repository visibility is intentional.
- [ ] Dependency and model licenses are reviewed.

## macOS experience

- [ ] Light/dark/system appearance.
- [ ] Compact/standard/expanded/short/full-screen layouts.
- [ ] Keyboard-only golden path.
- [ ] VoiceOver review.
- [ ] Reduced motion.
- [ ] Large logs and task graphs remain responsive.
- [ ] Quit, sleep/wake, and restart recover safely.
- [ ] Missing local tools produce truthful states.

## Security

- [ ] Capability, traversal, symlink, process cancellation, prompt injection, local-only, secret redaction, approval invalidation, and artifact integrity tests pass.
- [ ] No unresolved critical/high security finding.

## Documentation and evidence

- [ ] Status, architecture, features, bugs, risks, assumptions, handoff, and commands are current.
- [ ] Completion reports are valid.
- [ ] Evidence identifies environment, revision, result, and artifact.
- [ ] Release approval is recorded.
