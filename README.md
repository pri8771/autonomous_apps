# CommerceLint Autonomous Business

CommerceLint is an evidence-first AI-shopping readiness scanner and audit business. This repository is the product and operating source of truth; the public release is mounted into the existing production site at `priyanshchordia.com`.

## What is running

- **Canonical product:** `https://priyanshchordia.com/commercelint/`
- **Free browser scanner:** `https://priyanshchordia.com/commercelint/scanner.html`
- **CLI and GitHub Action:** `https://priyanshchordia.com/commercelint/cli.html`
- **Founding audit funnel:** `https://priyanshchordia.com/commercelint/founding-audit.html`
- **Hourly operator:** `.github/workflows/hourly-operator.yml`
- **Independent watchdog:** `.github/workflows/watchdog.yml`
- **Six-hour growth planner:** `.github/workflows/growth-planner.yml`
- **Production deployment:** hourly verified sync through `pri8771/priyanshchordia.com`
- **Search discovery:** IndexNow submission after a changed release passes production verification
- **Optional analytics:** consent-gated GA4 page and funnel events using the dedicated `Web_App` property
- **Durable memory:** `state/`, including runs, reviews, lessons, experiments, content, and operating state
- **Business constitution:** `config/business.json`

The operator follows this contract:

```text
wake → load goal and state → observe → rank tasks → perform one bounded action
→ verify → write evidence → update the next-action queue → sleep
```

## Deployment contract

`docs/` is the public source tree. The production portfolio workflow checks out this repository, mounts `docs/` at `/commercelint/`, rewrites and validates production canonicals, verifies the live homepage, scanner, status JSON, and IndexNow key, then records a machine-readable deployment receipt.

The obsolete standalone GitHub Pages workflow was removed. The raw.githack URL is retained only as an emergency preview and is not the canonical site.

## Run locally

```bash
python3 operator/main.py --dry-run
python3 operator/main.py
```

No Python dependencies outside the standard library are required by the hourly operator.

## Developer CLI and GitHub Action

```bash
python3 cli/commercelint.py tests/fixtures/strong.html --format markdown
python3 -m unittest discover -s tests -v
```

The reusable composite action is defined in `action.yml`. It can fail a build on missing required commerce fields, warnings, or a minimum field-coverage score. The CLI deliberately does not claim to verify selected variants, live HTTP behavior, feeds, checkout, or cross-page consistency.

Use the stable major-version branch in a workflow:

```yaml
- uses: pri8771/autonomous_apps@v1
  with:
    path: fixtures/products/example.html
    min-score: "80"
    fail-on: fail
    format: markdown
    output: commercelint-report.md
```

For maximum supply-chain reproducibility, replace `@v1` with the reviewed immutable commit `@99c971299488437cf8a39819f5f6025b722c12eb`.

## Autonomy and safety

The initial budget is $0. The operator fails closed if a paid service or quota risk appears. It does not fabricate reviews, credentials, customers, results, or human identities. Owner intervention is reserved for identity verification, tax information, CAPTCHA, two-factor authentication, financial-account setup, materially revised legal terms, and spending beyond the reinvestment policy.

## Official 90-day clock

The owner authorized autonomous execution on **August 24, 2026**. That is **Day 1** of the economic challenge; Day 90 is **November 21, 2026**. The 72-hour consecutive health streak remains a separate reliability burn-in measurement and does not delay the economic clock.

The primary score is verified net cash actually received after payment fees, refunds, and authorized expenses. Traffic, content volume, and followers are diagnostic metrics rather than the score.
