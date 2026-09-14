# CommerceLint durable run logging

Every autonomous CommerceLint cycle writes a normalized audit event. The event stream is the durable source for both human review and machine processing.

## Files

- `state/audit/events/YYYY-MM-DD.jsonl` — canonical append-only events, partitioned by the America/New_York calendar date.
- `state/audit/daily/YYYY-MM-DD.json` — machine-readable daily snapshot rebuilt from JSONL.
- `state/audit/daily/YYYY-MM-DD.md` — human-readable day-by-day, task-by-task diary.
- `state/audit/index.json` and `state/audit/INDEX.md` — machine and human indexes.
- `state/audit/schema.json` — the machine-readable event contract.

The older `state/runs/*.jsonl` operator stream and `state/daily/*.md` business reviews remain in place for compatibility. They are evidence inputs, not replacements for the unified audit diary.

## Event contract

Each event records:

1. Exact run start and end in UTC and America/New_York.
2. Trigger and stable run/event identifiers.
3. Selected task and a concise operational decision summary.
4. Inputs and evidence consulted.
5. Action taken and verification checks/results.
6. Metrics before and after when the source retained them.
7. Blockers, failures/retries, lessons, and next action.
8. Workflow/public links and relevant source or receipt commit hashes.
9. Backfill provenance and explicit historical limitations.

Decision summaries explain the applicable policy, priority, or recorded evidence. Hidden chain-of-thought is neither requested nor stored.

## Privacy and security

The logger accepts only explicit fields; it never dumps the process environment. Before persistence it recursively redacts:

- secret- or credential-named fields;
- GitHub-style access tokens, bearer credentials, and private keys;
- email addresses, including prospective customer addresses;
- credentials embedded in URLs and sensitive query parameters.

Do not pass raw issue bodies, form text, scanned page content, credentials, authentication headers, cookies, or private customer data into logging fields. Store only bounded operational summaries and public or repository-local evidence references.

## Workflow coverage

- `hourly_operator`: written by `operator/main.py`, including verified no-ops and control-mode skips.
- `growth_planner`: written by `operator/growth_planner.py`, including control-mode skips and failures.
- `watchdog`: evaluated and written by `operator/watchdog.py`; the workflow persists the diary with the shared state-writer lock.
- `production_smoke`: written by `operator/production_smoke.py`, including bounded retry evidence.
- `production_deployment`: the smoke workflow ingests the versioned receipt produced by `pri8771/priyanshchordia.com` through `operator/deployment_log_sync.py`.
- `indexnow_notification`: written by `operator/indexnow_submit.py` and committed by the search-notification workflow.
- `lead_intake`: written after a replay-safe public request and response artifact are persisted; raw issue bodies are never copied into the diary.
- `cli_tests`: written by the durable CI evidence job after deterministic CLI and Action verification.

The external deployment receipt remains the proof of publication. A source commit or deployment schedule alone is not treated as production success.

## Backfill

`operator/backfill_runlogs.py` reconstructs only what retained repository state, JSONL events, commit history, GitHub Actions metadata, and versioned deployment receipts support. Unknown triggers, decisions, retry details, metrics, lessons, or next actions remain explicitly labeled as not recorded.

```bash
python3 operator/backfill_runlogs.py
python3 operator/runlog.py rebuild
```

Backfill is idempotent through stable event IDs.
