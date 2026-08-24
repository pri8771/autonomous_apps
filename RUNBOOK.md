# MachineCart Runbook

## Operating loop
The hourly GitHub Actions job loads durable state, verifies local and public health, selects one eligible bounded task, executes it, verifies the result, records evidence, updates the queue, and commits the next state. The watchdog checks for stale heartbeats and performs a recovery run. The growth planner refreshes the content and acquisition runway every six hours.

## Deployment
Static production assets live in `docs/`. Changes to `docs/**` trigger the deployment workflow. The canonical health target is `https://priyanshchordia.com/machinecart/`; `docs/status.json` is the public machine-readable health ledger.

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

## Financial verification
Count revenue only from a payment-provider transaction or bank-settled evidence accessible to the operator. Record gross receipt, processor fee, refund, expense, and verified net cash separately. Do not count invoices, promises, or pending transfers.

## Next verified trigger
The hourly operator is scheduled at minute 17 UTC. A separate watchdog identifies a stale heartbeat and can run recovery independently.
