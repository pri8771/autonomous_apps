# CommerceLint Conversation Handoff

Last verified: **2026-08-31 14:04 UTC**. This is the canonical public-safe starting point for a new assistant conversation. Refresh all mutable values before reporting them.

## Objective and non-negotiable constraints

CommerceLint is the single business selected for the owner's 90-day, zero-budget experiment. It must maximize legitimate **verified net cash actually received** between August 24 and November 21, 2026. It may not spend pre-revenue cash, incur debt, start a card-required trial, fabricate evidence, or count an invoice, prospect, click, or pending payment as revenue.

After each new verified settled-revenue event, at most 50% of the then-current available cash may be spent in one bundled reinvestment cycle. The remainder stays reserved. Identity, tax, payout, CAPTCHA, 2FA, binding legal terms, financial-account setup, and any spending outside that policy require the owner.

Do not use or import `primandir.com`, Primandir branding, audiences, infrastructure, contacts, or the Primandir HubSpot portal.

## Current verified snapshot

- Production: `https://priyanshchordia.com/commercelint/` is live.
- Product surfaces: homepage, browser scanner, CLI/Action page, status endpoint, analytics asset, $49 founding-audit offer, and IndexNow key pass the seven-check production smoke suite.
- Operator: 183 successful runs and 0 recorded failures; latest success was `2026-08-31T13:45:49Z`.
- Economic score: $0 verified gross revenue, $0 verified net operating profit, 0 purchases, and 0 verified leads.
- Private CRM aggregate: 2 prospects, 0 leads, 0 outreach marked sent, $0 open potential, and $0 verified cash received.
- Gmail connector: requires reauthentication. Do not repeat this unchanged gate as a notification.
- Analytics: production uses the owner-controlled GA4 `Web_App` property and public measurement ID `G-MC3PB0Q7EX`, loaded only after explicit consent. A live opt-in Realtime event was verified on August 25. GA4 reporting is not automatically ingested into repository metrics.
- Current commercial bottleneck: qualified traffic and market validation, not basic product existence.

These are dated facts. Re-read `state/state.json`, `state/watchdog.json`, `state/production_smoke.json`, the latest GitHub Actions runs, and the private CRM before describing them as current.

## Product and revenue model

The free scanner and CLI detect the presence and parseability of ecommerce Product/Offer data and related commerce fields. The paid **$49 founding audit / implementation defect pack** adds manual evidence the free linter does not claim to verify: selected variants, visible-versus-structured values, policy conflicts, feed or checkout drift, a prioritized repair backlog, and acceptance checks.

The intended acquisition loop is:

```text
qualified agency or store -> free public-page evidence -> free bounded first pass
-> $49 defect pack -> possible recurring agency QA or implementation work
```

The product is technically real; willingness to pay remains unvalidated.

## Systems, accounts, and login boundaries

No password, token, recovery code, tax record, payment detail, private CRM identifier, customer email, message body, or private note belongs in this repository.

| System | Identifier / access path | Authentication state and boundary |
|---|---|---|
| GitHub source and automation | `pri8771/autonomous_apps`, default branch `main` | Local `gh` is authenticated as `pri8771` through the macOS keyring using HTTPS. Never copy or print the token. GitHub Actions uses repository-provided workflow credentials. |
| Production deployment | `pri8771/priyanshchordia.com`, default branch `main` | The portfolio repository mounts this repository's `docs/` at `/commercelint/` and records `deployments/commercelint-production.json`. Continuation normally needs the GitHub login, not a separate website-builder login. |
| Canonical domain | `priyanshchordia.com/commercelint/` | Owner-controlled. Registrar/DNS credentials are not recorded and are not needed for routine repository deployment. |
| GA4 | Account `381089409`; property `520476636` (`Web_App`); measurement ID `G-MC3PB0Q7EX` | Use the owner's existing Google session. The authenticated Google email is intentionally not recorded here. The measurement ID is public configuration, not a credential. |
| Private CRM | Google Sheet named `CommerceLint CRM` | Use the connected Google Drive/Sheets session. Its spreadsheet ID, contacts, message bodies, and notes are supplied only out of band and never committed. |
| Gmail | Connected Gmail app / OAuth session | Reauthentication is currently required. The authenticated sender is not the same as the public CommerceLint contact address. After reconnection, search narrowly for replies to tracked outreach; do not bulk-read unrelated mail. |
| Public contact | `pchordia@unsubscriber.me` | Public contact and critical-alert address. It is not proof of the authenticated Gmail sender. |
| PayPal | Owner's existing PayPal account | No CommerceLint checkout, invoice flow, or payment link is verified. Owner login and payment onboarding are required only after a prospect accepts scope. Never store PayPal credentials or payment data here. |
| Social publishing | No verified channel | Draft queue exists, but no authenticated publishing route is verified. Do not claim or publish without action-time authorization. |
| HubSpot | Explicitly excluded | Never connect CommerceLint to Primandir HubSpot or import its data. |

## Private CRM model

The Google Sheet has `Dashboard`, `Leads`, `Activities`, `Outreach Queue`, and `Setup` tabs. It is the private system of record for contacts, messages, outreach state, customer activity, follow-ups, expected value, and verified receipts.

Keep **prospects** separate from **leads**. A researched company or approved draft is a prospect. Promote it to Lead only after a verified reply, submitted request, or other explicit expression of interest, and record the supporting activity. Count revenue only after verified funds are received.

There is one unresolved reconciliation item: the private Dashboard currently reports zero outreach sent, while `coordination/agency-outreach-experiment-2026-08-24.md` records two messages verified in Gmail Sent on August 24. Do not change counts from the older note alone. Reauthenticate Gmail, verify the tracked threads narrowly, then append evidence to the CRM if appropriate.

## Repository and file map

- Local checkout: `/Users/pchordia/.codex/.chatgpt-projects/g-p-6a8c5f876b00819199ed0d8bec3aab98/autonomous_apps`
- Public operating repository: `https://github.com/pri8771/autonomous_apps`
- Production repository: `https://github.com/pri8771/priyanshchordia.com`
- Public source tree: `docs/`
- Business constitution: `config/business.json`
- Mission and score rules: `MISSION.md`
- Current machine state: `state/state.json`
- Watchdog and smoke evidence: `state/watchdog.json`, `state/production_smoke.json`
- Public CRM projection: `state/crm.json`
- Private/public CRM contract: `CRM.md`
- Account/auth map: `ACCOUNTS.md`
- Coordination and collision rules: `COORDINATION.md`
- Recovery and shutdown: `RUNBOOK.md`
- Durable run diary: `state/audit/INDEX.md`, `state/audit/events/`, `state/audit/daily/`
- Logging contract: `RUN_LOGGING.md`
- Historical CRM/analytics repair evidence: `coordination/crm-analytics-audit-2026-08-25.md`
- Initial outreach evidence: `coordination/agency-outreach-experiment-2026-08-24.md`
- Scheduled workflows: `.github/workflows/hourly-operator.yml`, `watchdog.yml`, `production-smoke.yml`, `growth-planner.yml`, `lead-intake.yml`, `indexnow.yml`, and `cli-test.yml`
- Codex backup heartbeat identifier: `commercelint-revenue-loop`

## New-conversation bootstrap

1. Read this file, `MISSION.md`, `COORDINATION.md`, `RUNBOOK.md`, `CRM.md`, and `ACCOUNTS.md`.
2. Pull `origin/main` with fast-forward only. Preserve all concurrent workflow commits and user changes.
3. Inspect `state/CONTROL.json`; stop new actions when it says `PAUSE` or `STOP`.
4. Verify the canonical site, newest operator, watchdog, and production-smoke runs and state files.
5. Inspect the private CRM Dashboard, Leads, Activities, and Outreach Queue using the out-of-band spreadsheet ID.
6. Check Gmail only when authenticated, and only for replies to tracked CommerceLint outreach.
7. Do not dispatch duplicate recovery when the operator's latest success is no more than 75 minutes old. If it is older, dispatch the watchdog, confirm the recovery operator succeeds, rerun the watchdog to close the incident, and rerun production smoke.
8. Keep private data out of Git. Public state may retain only public URLs, public organizations, non-private stage summaries, aggregates, and replay-safe evidence.
9. Before editing shared surfaces, read the coordination issue, record a bounded claim, and avoid operator-owned state.
10. Continue safe work when one account is blocked; request the owner only for a genuine non-delegable gate.

## Minimal verification commands

```bash
git pull --ff-only origin main
gh auth status
gh run list --repo pri8771/autonomous_apps --limit 15
python3 operator/crm.py validate
python3 operator/crm.py summary
python3 -m unittest discover -s tests -v
python3 -m compileall -q operator cli
git diff --check
curl -LfsS -o /dev/null -w '%{http_code}\n' https://priyanshchordia.com/commercelint/
```

Do not claim deployment, a lead, a reply, a purchase, or revenue from local tests alone. Verify the live destination or private system of record.
