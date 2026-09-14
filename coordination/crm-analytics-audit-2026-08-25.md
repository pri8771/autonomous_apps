# CommerceLint CRM and analytics audit — 2026-08-25

## Verified outcome

- Production analytics is consent-gated GA4 using the connected `Web_App` property and measurement ID `G-MC3PB0Q7EX`.
- Before consent, the public scanner loaded only the local analytics controller and no Google Tag Manager script.
- After explicit consent, the page loaded `googletagmanager.com/gtag/js?id=G-MC3PB0Q7EX`; GA4 Realtime then showed one active user in the last five and thirty minutes.
- The production deployment receipt at commit `0f60370` records the verified source and portfolio revisions, privacy checks, and successful release run `32864777018`.
- A private Google Sheet named `CommerceLint CRM` is the operational contact system of record. It has Dashboard, Leads, Activities, and Setup tabs; native tables; stage, owner, activity, and qualification controls; next-action and due-date fields; and separate expected and verified revenue fields.
- Public GitHub audit requests are projected replay-safely into `state/crm.json`. The public ledger rejects email, message, note, and other private-contact fields.
- Primandir HubSpot, Primandir contacts, and Primandir infrastructure are not used.

## Root causes repaired

1. The production sync script replaced the real analytics asset with a 97-byte no-op, while the prior smoke test counted that no-op as healthy.
2. The earlier measurement ID was copied from another site's public JavaScript and was not authoritative for the connected GA4 account.
3. CRM intake had only a public issue ledger and mail link; it had no private contact record, pipeline stages, follow-up controls, activity log, or verified-revenue fields.

## Remaining boundaries and gaps

- Gmail-to-Sheets capture is manual. Automating it requires a dedicated authorized OAuth integration; a sent or composed email is not counted as a lead.
- GA4 data is visible in the owner-controlled property but is not automatically imported into the public operating metrics. Traffic totals must not be copied into state without a verified reporting path.
- The private sheet is intentionally not linked or identified in this public repository.
- Payment collection remains an owner-controlled gate after a prospect accepts scope. No purchase or revenue has been verified.
- The economic score remains $0, and there are still no verified qualified leads. The plumbing is real; market validation is not yet established.

## Evidence

- Source implementation: `pri8771/autonomous_apps#18`
- Production repair: `pri8771/priyanshchordia.com#4`
- Verified deployment: `https://github.com/pri8771/priyanshchordia.com/actions/runs/32864777018`
- Production receipt: `https://github.com/pri8771/priyanshchordia.com/blob/main/deployments/commercelint-production.json`
- Public product: `https://priyanshchordia.com/commercelint/`
