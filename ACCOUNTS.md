# CommerceLint Accounts

No passwords, tokens, private keys, recovery codes, tax data, or payment details belong in this file.

| Service | Purpose | Ownership | Current state |
|---|---|---|---|
| GitHub `pri8771/autonomous_apps` | Source, durable state, schedules, incidents | Priyansh Chordia | Connected and active; local `gh` uses the macOS keyring as `pri8771`; never copy or print its token |
| GitHub `pri8771/priyanshchordia.com` | Production mount and deployment receipt | Priyansh Chordia | Connected and active; routine deployment uses GitHub rather than a separate website-builder login |
| `priyanshchordia.com/commercelint/` | Canonical production website | Priyansh Chordia | Live; all seven production checks passed on 2026-08-31 |
| `pchordia@unsubscriber.me` | Public contact and critical alerts | Priyansh Chordia | Authorized |
| PayPal account | Potential invoice or payment-request settlement after accepted scope | Priyansh Chordia | Existing account activity observed through authorized Gmail; no CommerceLint payment link or invoice flow is verified, so owner action remains required at first accepted sale |
| Google Analytics 4 — `Web_App` | Consent-gated traffic and funnel measurement | Priyansh Chordia | Account `381089409`, property `520476636`, measurement ID `G-MC3PB0Q7EX`; live opt-in traffic reached GA4 Realtime on 2026-08-25; reporting is not automatically ingested |
| Private Google Sheet — `CommerceLint CRM` | Contact, stage, owner, activity, outreach queue, follow-up, and verified-payment ledger | Priyansh Chordia | Connected and private; the public repository stores no sheet ID, contact email, message body, or private note |
| Gmail | Individualized, lawful outreach and lead replies | Priyansh Chordia | OAuth connector requires reauthentication as of 2026-08-31; authenticated sender differs from the public CommerceLint contact address |
| Social publishing channel | Evidence-led distribution | Priyansh Chordia | Draft queue exists; authenticated publishing channel not yet verified |

See `coordination/HANDOFF.md` for the access paths and safe login boundaries. Account identifiers are documented; credentials never are.
