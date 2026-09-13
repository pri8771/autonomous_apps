# H04 — Stripe Checkout implementation handoff

This source adds a real provider adapter; no Stripe request, account activation,
payment, webhook registration, hosted release or email delivery was performed
during development. The owner authorizes payment setup as an individual seller.
Older prospect-first/deferred-payment planning does not block this authorized
engineering. This change does not attest to live account activation.

## Implementation

`operator/stripe_checkout.py` uses Stripe's HTTPS API directly through Python's
standard library; it adds no package dependency. Checkout is always `mode=payment`
with one item: Sample **199 cents**, Lite **999 cents**, Comprehensive **1999 cents**,
USD. No subscription, card storage, additional upsell, promotion code or free trial
is configured. Current handling expects these exact final totals; changing tax,
discount or price behavior requires matching order/receipt handling, not accepting
an arbitrary webhook amount.

The server validates public URLs, plan limits, delivery email and submitted price
before calling Stripe. It supplies prices and order metadata; browser input cannot
provide a key, account, currency, price ID, endpoint or redirect destination.
Raw Stripe-Signature verification checks timestamp plus body bytes, `v1` HMAC and a
five-minute window. The signed event must match the stored Checkout Session,
mode, order, plan, currency, amount and paid state. A return-page visit is never
proof of payment. Unpaid completion queues nothing; async success can queue later.

Private SQLite stores order/email/intake, verified events and report jobs. One
transaction records payment and its unique fulfillment job. Concurrent deliveries,
new event IDs for the same paid session, restarts and interrupted job insertion
cannot create multiple jobs. Late failures cannot regress a succeeded payment.
`stage_report` reuses the existing plan-scoped renderer and stores the report
privately; it never fetches arbitrary pages or claims email delivery. The existing
`payment_fulfillment.py` JSON/HMAC harness is explicitly fixture-only and must not
be mounted as a payment endpoint.

## Trusted runtime setup

The root account/runtime owner supplies values through protected process
environment, never browser fields, Git, Jira, test logs or command arguments:

- `COMMERCELINT_STRIPE_MODE`: explicitly `test` or `live`; there is no fallback.
- For test: `COMMERCELINT_STRIPE_TEST_SECRET_KEY`,
  `COMMERCELINT_STRIPE_TEST_WEBHOOK_SECRET`, `COMMERCELINT_STRIPE_TEST_DB_PATH`.
- For live: the corresponding `COMMERCELINT_STRIPE_LIVE_*` names, with a live key
  and a separate database. An existing database refuses an opposite mode.
- `COMMERCELINT_CHECKOUT_SUCCESS_URL` and `COMMERCELINT_CHECKOUT_CANCEL_URL`:
  actual HTTPS return pages beneath `https://priyanshchordia.com/commercelint/`.

Use an absolute database path outside the repository in an owner-only directory.
On POSIX the adapter requires private directory/file permissions; on Windows the
runtime owner must apply the equivalent private ACL. Secrets are redacted from
configuration repr. No private order data enters the public `state/` projection.
Do not copy a test database or endpoint secret into the live service. Keep the
host clock synchronized for signature verification.

The callable entry point is:

```python
from stripe_checkout import StripeConfig, StripeCheckout, create_wsgi_app
payments = StripeCheckout(StripeConfig.from_environment())
application = create_wsgi_app(payments)
```

Add `operator/` to the service's import path rather than importing Python's
standard-library `operator` package. Mount the WSGI callable behind an existing
HTTPS-capable host with request rate limiting, protected storage and process
supervision. Public GitHub Pages only serves static files and cannot execute this
adapter. No new hosting account or Sites project is required by the implementation.

- `POST /checkout`: JSON `request_id`, `plan_id`, `urls`, `contact_email`, optional
  `claimed_price`; canonical site Origin required. Use a random request ID once
  per intended purchase and reuse it across network retries. The response contains
  Stripe's actual hosted checkout URL after provider confirmation.
- `POST /webhook`: **unaltered raw bytes** and `Stripe-Signature`; register
  `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
  `checkout.session.async_payment_failed`, `checkout.session.expired` in the
  matching sandbox/live endpoint. Configure snapshot events from this direct
  account. Connect-account events are refused. Explicitly tagged other products
  are ignored. Unhandled event types receive an acknowledgement without mutation.
- A transient provider/storage/binding failure produces 503 so retries remain
  possible; rejected signatures/receipt mismatches produce 400. The handler queues
  work and returns without running the report or sending email.
- A trusted fulfillment worker reads queued private jobs, fetches exactly the
  accepted public URLs using existing safe-fetch controls, and calls `stage_report`.
  Existing private order email is available to the separately configured delivery
  adapter. It must retain an actual send/readback receipt before setting delivered;
  this change deliberately has no fake mail sender or delivery transition.

There is no public order-status or report-download route in this adapter, and no
authenticated private report is exposed by knowing an order ID. Checkout creation
is idempotent within the saved request; uncertain attempts older than 23 hours
require reconciliation with Stripe before making a new attempt, because a provider
idempotency key is not an indefinite payment lock. Original provider parameters
are durably saved and replayed unchanged even if email casing or redirect settings
change before a lost-response retry. An expired/failed session needs
an explicitly new, reconciled attempt; do not blindly retry with a new ID.

## Remaining acceptance work

1. Root binds the sandbox secret, matching endpoint signing secret, private store
   and actual HTTP host; wire the existing static inquiry form to that endpoint.
   These are concrete runtime bindings, not a second owner approval request.
2. Complete an owner-controlled sandbox checkout. Verify signed paid event, exactly
   one durable job under duplicate delivery, real report and controlled private
   delivery. Mark it as a test; never count it as a customer or settled revenue.
3. Root verifies live Stripe activation/individual-seller details and independently
   binds live key, live endpoint and new live database before offering real payment.
   A sandbox existing in the Dashboard does not prove any of these live facts.
4. Retain technical review and exact receiving-source/deployment readback. Payment
   success is still separate from settled net cash, refunds/disputes and delivery.
   Refund requests continue through the existing support process; this adapter
   does not issue refunds or declare a complete refund/dispute integration.

## Verification and official references

All provider, DNS and HTTP interactions in tests use fixtures/mocks; no actual
Stripe/model calls. Focused tests cover all tiers, malformed/unsupported intake,
lost creation response, idempotency-window expiry, signed-body mutation and clock
skew, wrong mode/currency/amount/session, unpaid and late events, concurrency,
transaction rollback, restart, private report scope and WSGI request boundaries.

- [Stripe Checkout Session creation](https://docs.stripe.com/api/checkout/sessions/create)
- [Stripe raw-body signature verification](https://docs.stripe.com/webhooks/signature)
- [Stripe event handling, retries and manual signature verification](https://docs.stripe.com/webhooks)
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests)

Documentation consulted 2026-09-13. The current API account/webhook version must be
recorded in the live receipt; this adapter does not invent an account API version.
