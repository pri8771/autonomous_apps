# CommerceLint CRM

CommerceLint uses a deliberately small zero-budget CRM with two privacy tiers.

## System of record

- **Private Google Sheet — `CommerceLint CRM`:** contact email, organization, stage, owner, next action, due date, expected value, and private notes. This is the operational system of record for outreach and email leads. It is not linked from the public repository.
- **Public Git ledger — `state/crm.json`:** only public GitHub request references, public handles, public storefront URLs, stage, owner, next action, and potential value. It rejects email addresses, messages, notes, and other private fields.
- **Gmail:** remains the private inbound/outbound message surface. A sent message is not a lead; a reply or submitted request is.

Primandir HubSpot, Primandir contacts, and Primandir infrastructure are excluded.

## Funnel stages

`needs_public_url` → `new` → `qualified` → `contacted` → `scope_confirmed` → `payment_requested` → `won`

Use `lost` for a closed opportunity that should not be pursued. `won` requires verified payment; scope acceptance alone is not revenue.

## End-to-end paths

1. A public GitHub issue triggers `.github/workflows/lead-intake.yml`.
2. The worker validates the public URL, produces the bounded first pass, writes the raw public request to `state/leads.json`, and upserts an actionable public record in `state/crm.json`.
3. The private CRM sheet receives the contact record for follow-up. Public issue data can be copied without adding private notes to Git.
4. A private email request opens the visitor's mail application. Nothing is counted until the email is actually received; the operator then records it in the private sheet.
5. Stage, next action, and due date are required for every active opportunity. Payment and revenue remain separate verified events.

The GitHub path is automated. Gmail-to-Sheets entry is intentionally manual until a dedicated OAuth integration can be installed without exposing credentials or creating a paid dependency.

## Operator checks

```text
python operator/crm.py validate
python operator/crm.py summary
```

The public ledger is replay-safe: processing the same GitHub issue again updates one lead and does not manufacture a second activity or opportunity.
