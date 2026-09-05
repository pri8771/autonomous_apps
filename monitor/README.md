# Portfolio watchdog monitor (ORCH8-1)

A second, independent layer of oversight for the CommerceLint operator loop
that runs **outside** GitHub Actions, on the portfolio owner's own machine.

## Why this exists

The repo's own `hourly-operator` / `watchdog` / `production-smoke` loop is
entirely self-healing *as long as GitHub's scheduled triggers keep firing
for this repo*. If GitHub Actions scheduling itself lapses for this repo
(this has happened for multi-hour stretches even while Actions were fully
enabled and the repo was active — see `RUNBOOK.md` "Recovery" and the
repeated `[CommerceLint] Stale heartbeat` incidents in the issue tracker),
nothing *inside* GitHub Actions can notice, because the thing that would
notice (the watchdog's own `schedule:` trigger) is exactly what stopped
firing. This monitor is the external check that doesn't share that failure
mode.

## Permissions contract: read-only + Actions-dispatch only

- All state reads (`config/business.json`, `state/state.json`) go through
  unauthenticated `raw.githubusercontent.com` fetches. No token is needed to
  classify green vs. breach.
- The only authenticated calls are `workflow_dispatch` (POST) and the
  "list workflow runs" read used to poll a dispatch's outcome.
- This script never calls the Contents or Issues write APIs and never
  pushes a commit. It relies entirely on the repo's own workflows
  (`watchdog.yml`, `production-smoke.yml`) to do any writing.
- The token you provide should be a fine-grained PAT scoped to this one
  repo with **Actions: write** and **Contents: read** only — nothing else.
  Do not use a broad classic PAT.

## What it does

`python monitor/portfolio_watchdog.py` runs one bounded check cycle
(designed to be invoked periodically, e.g. by Windows Task Scheduler):

1. Reads the current operator heartbeat age and the configured
   `heartbeat_stale_minutes` threshold (75 by default).
2. Classifies **green** (fresh) or **breach** (stale).
3. Green path: exits quietly. No alert is written, no Slack noise.
4. Breach path — replays exactly the sequence in `RUNBOOK.md` "Recovery" /
   "New-conversation bootstrap" step 6:
   - dispatch `watchdog.yml` (this itself dispatches `hourly-operator.yml`
     if the heartbeat is stale, same as the repo's own scheduled watchdog
     would)
   - verify the operator heartbeat is fresh again
   - dispatch `watchdog.yml` a second time so it observes the fresh
     heartbeat and auto-closes any open `[CommerceLint] Stale heartbeat`
     issue
   - dispatch `production-smoke.yml` as a final health confirmation
   - append one structured alert record to a local JSON Lines file for Kai
     (the portfolio owner's assistant) to relay to Slack

Implemented as a LangGraph `StateGraph` (`langgraph` in
`monitor/requirements.txt`) when that package is installed. If it is not
installed, the same node functions run directly in the same order — this
keeps the module importable and its logic unit-testable without adding a
heavy dependency to the shared CommerceLint CI (`.github/workflows/cli-test.yml`
only ever installs the standard library; this directory is intentionally
excluded from `tests/` discovery so the two products' CI stay independent).

## "Alert via Kai" wiring

The breach-path alert is appended as one JSON line to
`--alert-path` (default `~/.local/state/commercelint-portfolio-monitor/alerts.jsonl`
on the machine the monitor runs on). This keeps the monitor itself
generic and not tied to any one assistant/notification stack. On the
owner's Windows machine, Kai's own heartbeat routine is the consumer:
it tails that file and relays new entries to Slack. That wiring lives in
Kai's own workspace config (`HEARTBEAT.md`), not in this repo, since it is
specific to the owner's assistant setup rather than to CommerceLint.

## Running it

```
pip install -r monitor/requirements.txt
python monitor/portfolio_watchdog.py                 # dry-run (default): classifies only, never dispatches
python monitor/portfolio_watchdog.py --live \
  --token "$COMMERCELINT_MONITOR_GH_TOKEN"            # live: dispatches + polls + alerts on breach
```

Tests (no network, no langgraph required):

```
python -m unittest discover -s monitor/tests -v
```

## Deliberately out of scope for this PR

- **No live/scheduled activation.** This PR ships the code and its tests
  only. It does not install a Windows Task Scheduler entry, does not run
  live against the repo on a recurring basis, and does not generate or
  install any GitHub token. Turning this into a recurring check is an
  owner-supervised follow-up step (see ORCH8-1's Jira ticket).
- Changing CommerceLint product/outreach behavior.
- Storing or documenting private sender addresses, CRM sheet IDs, or
  channel IDs.

## Example: a real recovery this design mirrors

On 2026-08-31 the repo's scheduled triggers (hourly-operator, watchdog,
production-smoke, growth-planner) went silent from 15:26 UTC to 19:17 UTC
(~4h) while Actions remained enabled. A manual run of the exact recovery
sequence implemented here (dispatch watchdog → verify → dispatch watchdog
again → dispatch production-smoke) fully recovered the loop: the operator
ran and published new content, the open `[CommerceLint] Stale heartbeat`
issue (#53) auto-closed, and production smoke passed all 7 checks. This
was the Nth such incident that day (issues #48-#53) - exactly the pattern
this monitor is meant to catch automatically instead of requiring a human
(or Kai) to notice and intervene by hand.
