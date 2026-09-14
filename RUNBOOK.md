# CommerceLint Runbook

## Operating loop
The hourly GitHub Actions job loads durable state, verifies local and public health, selects one eligible bounded task, executes it, verifies the result, records evidence, updates the queue, and commits the next state. The watchdog checks for stale heartbeats and performs a recovery run. The growth planner refreshes the content and acquisition runway every six hours.

Every run must also persist its normalized event under `state/audit/`. Read `state/audit/INDEX.md` first for the chronological diary, then use the linked JSONL when exact machine fields are needed. A missing diary event is an operating incident even when the business action itself succeeded.

## Deployment
Static production assets live in `docs/`. Changes to `docs/**` trigger the deployment workflow. The canonical health target is `https://priyanshchordia.com/commercelint/`; `docs/status.json` is the public machine-readable health ledger.

## Control and kill switch
`state/CONTROL.json` is fail-closed:
- `RUN`: normal operation.
- `PAUSE`: no new operator or growth action; durable state is preserved.
- `STOP`: no new operator or growth action. On an explicit STOP command, scheduled workflow triggers must also be removed or disabled before shutdown is considered complete.

Never place secrets in the control file or repository.

## Recovery
1. Read the latest workflow failure, open incident issue, `state/state.json`, and the latest `state/runs/*.jsonl` entry.
2. Determine whether the failure is code, deployment, network, quota, permissions, or corrupt state.
3. Preserve a copy of the failing evidence; do not erase history.
4. Apply the smallest reversible repair.
5. Run syntax and local asset checks.
6. Re-run the failed job or allow the watchdog to recover it.
7. Verify the canonical URL and status ledger.
8. Record the cause, repair, and prevention as a lesson.
9. Confirm the recovery run appears in both `state/audit/events/` and the daily Markdown diary without secrets or private customer data.

## Financial verification
Count revenue only from a payment-provider transaction or bank-settled evidence accessible to the operator. Record gross receipt, processor fee, refund, expense, and verified net cash separately. Do not count invoices, promises, or pending transfers.

## Next verified trigger
The hourly operator is scheduled at minute 17 UTC. A separate watchdog identifies a stale heartbeat and can run recovery independently. The watchdog uses the configured heartbeat age threshold; crossing a UTC hour boundary alone does not trigger recovery because GitHub schedules may start late.

## New-conversation bootstrap

1. Read `coordination/HANDOFF.md`, then `MISSION.md`, `COORDINATION.md`, `CRM.md`, and `ACCOUNTS.md`.
2. Fast-forward from `origin/main`; do not overwrite newer operator commits.
3. Verify `state/CONTROL.json`, the live site, newest operator/watchdog/smoke runs, and the matching state receipts.
4. Read private CRM ranges only after resolving its spreadsheet metadata and exact tab names. Never copy the sheet ID, emails, message bodies, or notes into Git.
5. Check Gmail only when authenticated and only for replies to tracked CommerceLint outreach.
6. If the last successful operator run is older than 75 minutes, dispatch the watchdog, verify the recovery operator, rerun the watchdog to close the incident, and rerun production smoke. When current, do not create a duplicate recovery.
7. Record a bounded coordination claim before changing shared documentation or code.

The Codex backup heartbeat is identified as `commercelint-revenue-loop`. GitHub Actions, not a laptop or chat window, runs the primary operator and production controls.
