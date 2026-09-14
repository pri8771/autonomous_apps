# CommerceLint CRM

CommerceLint uses a deliberately small zero-budget CRM with two privacy tiers.

## System of record

- **Private Google Sheet — `CommerceLint CRM`:** Dashboard, Leads, Activities, Outreach Queue, and Setup tabs hold contact email, organization, stage, owner, next action, due date, expected value, verified receipts, and private notes. This is the operational system of record for outreach and email leads. It is not linked from the public repository.
- **Public Git ledger — `state/crm.json`:** only public GitHub request references, public handles, public storefront URLs, stage, owner, next action, and potential value. It rejects email addresses, messages, notes, and other private fields.
- **Gmail:** remains the private inbound/outbound message surface. A sent message is not a lead; a reply or submitted request is.

Primandir HubSpot, Primandir contacts, and Primandir infrastructure are excluded.

## Prospect versus lead

A researched organization, suitable contact route, approved message, or queued outreach item is a **Prospect**, not a Lead. Promote a Prospect to Lead only after a verified reply, submitted request, or other explicit expression of interest, and append the supporting Activity. A fit label such as `Qualified` on a Prospect does not make it a qualified lead.

As of the 2026-08-31 verification, the private Dashboard contains 2 prospects, 0 leads, 0 outreach marked sent, and $0 verified cash. The older public outreach note records two messages verified in Gmail Sent on August 24; reconcile that historical evidence only after Gmail is reauthenticated and the tracked threads are narrowly rechecked.

## Funnel stages

`needs_public_url` → `new` → `qualified` → `contacted` → `scope_confirmed` → `payment_requested` → `won`

Use `lost` for a closed opportunity that should not be pursued. `won` requires verified payment; scope acceptance alone is not revenue.

## End-to-end paths

1. A public GitHub issue triggers `.github/workflows/lead-intake.yml`.
2. The worker validates the public URL, produces the bounded first pass, writes the raw public request to `state/leads.json`, and upserts an actionable public record in `state/crm.json`.
3. The private CRM sheet receives the contact record for follow-up. Public issue data can be copied without adding private notes to Git.
4. A private email request opens the visitor's mail application. Nothing is counted until the email is actually received; the operator then records it in the private sheet.
5. Stage, next action, and due date are required for every active opportunity. Payment and revenue remain separate verified events.
6. Approved outreach remains in the Outreach Queue until a send is verified. A draft or approval is not a send, and a send is not a lead.

The GitHub path is automated. Gmail-to-Sheets entry is intentionally manual until a dedicated OAuth integration can be installed without exposing credentials or creating a paid dependency.

## Operator checks

```text
python operator/crm.py validate
python operator/crm.py summary
```

The public ledger is replay-safe: processing the same GitHub issue again updates one lead and does not manufacture a second activity or opportunity.
