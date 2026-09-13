# CommerceLint private checkout runtime

This composes the existing Stripe adapter and report renderer with a public HTML
fetch worker and authenticated browser report delivery. It has no email sender.
Source and local tests do not establish a real Stripe checkout, customer payment,
external report delivery or production deployment. No public frontend or shared
portfolio deployment is changed by this patch.

## Protected configuration and local execution

Use Python 3.11 or newer. The implementation uses the standard library. Keep
configuration and database outside the source tree. On POSIX use an owner-only
directory (0700), configuration file (0600) and database (0600). The config loader
rejects symlinks, non-owner files, unrelated setting names and public permissions.
Windows must use a protected process environment and owner-only storage ACLs;
the POSIX config-file loader intentionally does not claim to verify Windows ACLs.

Supply a JSON object of these environment setting names through an owner-only
file, or directly through the host's protected process environment. Never paste
secret values in command arguments, this document, tickets, or screenshots:

| Setting | Required input |
|---|---|
| COMMERCELINT_STRIPE_MODE | `test` for sandbox work |
| COMMERCELINT_STRIPE_TEST_SECRET_KEY | Real sandbox secret/restricted API key allowed to create Checkout Sessions |
| COMMERCELINT_STRIPE_TEST_WEBHOOK_SECRET | Signing secret for the exact sandbox snapshot endpoint or local Stripe CLI listener |
| COMMERCELINT_STRIPE_TEST_DB_PATH | Absolute path to a new private test SQLite database |
| COMMERCELINT_CHECKOUT_SUCCESS_URL | `https://priyanshchordia.com/commercelint/inquiry.html?payment=return` |
| COMMERCELINT_CHECKOUT_CANCEL_URL | `https://priyanshchordia.com/commercelint/inquiry.html?payment=cancel` |
| COMMERCELINT_DELIVERY_KEY | Random URL-safe secret, 43–128 characters; e.g. 32 bytes from a cryptographic generator, stored privately |
| COMMERCELINT_RUNTIME_ORIGIN | `http://127.0.0.1:8765` for the built-in sandbox server; exact HTTPS origin for a qualified remote host |

The delivery key is bound to the database at initialization. Restore the same key
after restart; changing it is refused because previously issued access files
would otherwise silently stop working. Test/live stores are separate; never copy
a test store or endpoint secret into live configuration. The delivery token is
mode-bound. Startup checks do not contact Stripe or prove credential validity.

From this product checkout, with an actual protected config file:

```sh
python3 operator/checkout_runtime.py check-config --config /absolute/private/path/runtime-test.json
python3 operator/checkout_runtime.py serve-local --config /absolute/private/path/runtime-test.json
```

Open `http://127.0.0.1:8765/`. Enter the plan, public product URLs and contact email.
Save the private access file before opening Stripe in a separate tab. The original
tab remains the private report page. A return-page visit never establishes
payment. Reloads preserve the same pending request; changed intake requires
reconciliation before a new tab/purchase. The private access file can restore
report access on the runtime page without putting tokens in a URL.

Forward the exact sandbox snapshot events to `/webhook` using an authenticated
Stripe CLI listener, or the qualified HTTPS host. Use the signing secret returned
for that listener/endpoint, not another dashboard endpoint. Subscribe to
`checkout.session.completed`, `checkout.session.async_payment_succeeded`,
`checkout.session.async_payment_failed`, and `checkout.session.expired`.
No Stripe CLI authentication or endpoint registration occurred in this change.

After a verified test payment queues a job, run the finite worker command:

```sh
python3 operator/checkout_runtime.py work-once --config /absolute/private/path/runtime-test.json
```

Return to the original tab and select **Check for my report**. Downloaded Markdown
is treated as a file, never injected into the page as HTML. The browser hashes
received bytes and submits an authenticated acknowledgement. This records
`client_receipt_recorded`; it does not prove the file was saved or read, and never
claims email delivery. No customer email, submitted URL or token is logged by
the included server. Keep private access files private; access expires 30 days
after checkout preparation and ordinary retries do not extend it.

## Hosted composition and operational limits

An existing qualified Python WSGI host can mount
`checkout_runtime.create_application()` with `operator/` on the import path and
protected environment settings. The host owns HTTPS, request timeouts and rate
limits, private persistent disk, clock synchronization, process supervision,
backups/retention and access-log redaction. Do not expose Python's built-in server
to the network. Static GitHub Pages cannot execute this service. The separate
worker uses the same private database/settings; an existing authorized job runner
may invoke `work-once` on its normal cadence or after a queued event. No new
schedule, service, account or paid host is installed here.

`POST /inquiry` and `/checkout` accept the original four intake fields (and optional
claimed price); return Stripe's confirmed Checkout URL plus the private access
token. Only configured runtime/canonical website origins receive CORS access.
`POST /report` accepts `{order_id}` and `Authorization: Bearer <token>` and returns
202 while pending, or private Markdown plus its exact byte hash once staged.
`POST /acknowledge` accepts `{order_id, artifact_sha256}` with the same bearer.
There is no public order lookup, report path, or token-bearing query string.

The worker claims one paid job in a SQLite transaction, fetches outside the
transaction, and stages via the existing plan-scoped scanner/renderer. Concurrent
workers skip active leases; leases expire after 30 minutes. Failed fetch/render
attempts wait five minutes, then stop after three attempts as support-required.
An operator must investigate rejected/non-HTML/oversize/JavaScript-only pages and
reconcile the existing order before explicitly requeuing or arranging a remedy;
do not start another charge to retry report generation. Repeated webhook events
do not duplicate orders, jobs or staged reports. Do not claim automated refunds.

Every redirect is revalidated; connections pin an already-public resolved IP and
retain HTTPS certificate/SNI validation for the original host. Any nonpublic
address in DNS rejects the destination. No proxy environment, credentials,
cookies or JavaScript execution is used. HTML is limited to 2 MiB/page with
bounded socket/body waits and at most three followed redirects; HTTPS downgrade
is refused. DNS resolution itself uses the host resolver and its system timeout.
Deploy with an overall worker-process time limit above the plan workload and
below the 30-minute lease to bound abnormal resolver delays.

## Actual remaining inputs and acceptance

The named account and secret manifests identify static Pages, an existing private
Windows worker and OPO's separate Sites project. They do not identify a qualified
CommerceLint public Python HTTP host or a protected Stripe sandbox secret item.
No required CommerceLint runtime settings were present in this process when
checked. This is a narrow finding about those manifests/process settings, not a
claim that no credential exists anywhere. OPO's project/secrets are not reused.

1. Recover the existing sandbox key and matching listener/endpoint signing secret
   from their authorized protected store, or provision them through the account
   owner. The sandbox is under the existing seller; do not create a duplicate
   merchant or wait for live KYC to test sandbox.
2. Use the local server plus an authorized Stripe CLI listener for owner testing,
   or supply an existing approved Python HTTPS origin, private disk and job runner.
   Register the matching webhook. No new paid hosting is implied.
3. Retain the actual session/event IDs, mode, exactly one job, report byte hash and
   browser acknowledgement for the owner-controlled sandbox order. Never retain
   tokens/contact data in public receipts or count the test as revenue.
4. Public frontend binding to the verified backend belongs to the release owner.
   Live mode additionally requires actual account activation/capability readback,
   independently protected live credentials and a separate private live store.
5. H04 remains local scope with no exact native Jira mapping verified. The
   designated writer must admit/map this backend scope before a code commit.
   BOTS-113/114 candidate/baseline references do not automatically provide that
   mapping. Existing staged source and history remain preserved.
