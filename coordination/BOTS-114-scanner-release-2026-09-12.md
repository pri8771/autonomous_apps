# BOTS-114 scanner continuity release

The Windows Cursor Auto candidate adds local result restore/clear controls and clearer failure guidance. Root integration corrects repeated scan counting during restore, protects against corrupt/disabled storage, and reads the original analysis timestamp from the atomically saved report. A saved result remains explicitly historical; it is not a fresh scan or a verified paid audit.

Bounded source ownership: docs/scanner.html, tests/scanner-storage.test.mjs, related CI coverage and this receipt. Windows ownership handoff was confirmed in its 2026-09-12 18:19 EDT return. GitHub coordination issue 11 was read: no unexpired claims on these files. Operator-owned state and business metrics remain untouched. Root integrates through an isolated branch/PR and preserves newer main commits.

Validation: six targeted JavaScript checks and fifteen existing Python tests passed. Actual independent Claude Haiku review receipts are retained in the private Astra planning/five-bot-live-2026-09-12/commercelint directory. An initial review made unsupported claims about textContent injection; the coordinator preserved that verdict and requested a focused reconsideration instead of fabricating fixes. A separately identified partial-storage timestamp problem was repaired by using report.generatedAt.

The initial live scanner passed empty-input, built-in-example and malformed-JSON-LD tests before this patch. That is baseline evidence, not proof this candidate is deployed. Final public destination readback is recorded separately after deployment. No new customers, lead submission, payment or revenue is claimed.
