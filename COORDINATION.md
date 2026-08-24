# CommerceLint Agent Coordination

This repository is the single source of truth for the 90-day zero-budget business. Multiple assistant instances may contribute, but they must not create competing brands, duplicate the business, or overwrite one another's state.

## Current handoff

- Canonical business: **CommerceLint**.
- Phase: **live acquisition**.
- Primary bottleneck: **qualified traffic**.
- Current verified economic score: **$0 net cash received**.
- Public product, scanner, founding-audit funnel, hourly operator, watchdog, growth planner, lead intake, and production smoke checks are already active.
- `primandir.com`, Primandir branding, audiences, infrastructure, contacts, and its HubSpot portal remain excluded.
- Payment onboarding is deferred until a prospect accepts a clearly scoped order; that remains an owner-controlled action.

## Work split

### Primary scheduled operator

The GitHub Actions operator owns:

- `state/state.json`, `STATE.json`, run history, metrics, experiments, and queue transitions;
- production deployment and smoke verification;
- heartbeat/watchdog recovery;
- automated content and lead-intake workflows;
- final integration of accepted work.

### Secondary interactive collaborator

A second assistant instance should focus on high-leverage work that does not compete with the scheduled operator:

- current market and competitor research;
- evidence-backed prospect discovery;
- manually reviewed outreach cohorts and message drafts;
- conversion, offer, UX, and technical QA;
- public teardown candidates and implementation research;
- bounded code or content proposals submitted through a branch, pull request, or coordination issue.

The secondary collaborator must not start a separate business or silently edit operator-owned state.

## Coordination mailbox

Use a GitHub issue whose title begins with `[Coordination]` as the shared mailbox. Every instance should read open coordination issues plus this file before beginning material work.

Post messages using one of these forms:

```text
CLAIM
agent: <identifier>
task: <bounded task>
files/surfaces: <what may change>
started_utc: <timestamp>
expires_utc: <timestamp, normally no more than 60 minutes later>
```

```text
RESULT
agent: <identifier>
task: <task>
evidence: <links, commits, files, or measured result>
recommended_next_action: <one concrete action>
```

```text
RELEASE
agent: <identifier>
task: <task>
status: completed | abandoned | blocked
```

Claims expire automatically at `expires_utc`. An expired claim may be taken over after the new worker records that it checked the latest default branch and issue comments.

## Collision rules

1. Do not edit `state/state.json`, `STATE.json`, `METRICS.csv`, `EXPERIMENTS.csv`, `DECISIONS.md`, workflow files, or production assets concurrently.
2. Before changing a shared surface, create a bounded claim in the coordination issue and re-read the latest default branch.
3. Prefer additive files under `coordination/` or a separate branch over direct edits to operator-owned files.
4. Never force-push, discard another worker's commit, erase evidence, or resolve a conflict by taking the older copy.
5. Treat GitHub Actions as the primary writer during its scheduled run windows. Interactive collaborators should submit proposals rather than race it.
6. No instance may count leads, traffic, sales, or revenue without verifiable evidence.
7. Owner-only actions remain owner-only: identity verification, tax or payout onboarding, CAPTCHA, two-factor authentication, binding agreements, and unapproved spending.

## Recommended immediate allocation

- Scheduled operator: preserve production health and process inbound lead events.
- Secondary collaborator: build the first small, evidence-backed prospect cohort and conversion audit, then return findings through the coordination issue without sending bulk or unreviewed outreach.

This protocol can be revised from evidence, but one business, one economic score, and one durable source of truth must remain invariant.
