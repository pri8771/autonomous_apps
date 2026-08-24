# MachineCart Autonomous Business

MachineCart is an evidence-first AI-shopping readiness scanner and audit business. This repository contains both the public static product and the scheduled business operator.

## What is running

- **Public product:** browser-based product-page scanner in `docs/`
- **Hourly operator:** `.github/workflows/hourly-operator.yml`
- **Independent repository watchdog:** `.github/workflows/watchdog.yml`
- **Durable memory:** `state/state.json`, run logs, daily reviews, weekly reviews, lessons, experiments, and task queue
- **Business constitution:** `config/business.json`
- **Content backlog:** `content/queue.json`
- **Public status:** `docs/status.html` and `docs/status.json`

The operator follows this contract:

```text
wake → load goal and state → observe → rank tasks → perform one bounded action
→ verify → write evidence → update the next-action queue → sleep
```

## Current URLs

- Canonical production URL: `https://priyanshchordia.com/machinecart/`
- Interim static preview: `https://raw.githack.com/pri8771/autonomous_apps/main/docs/index.html`
- Repository: `https://github.com/pri8771/autonomous_apps`

GitHub Pages must be enabled once under **Settings → Pages → Source: GitHub Actions**. Until then, the interim preview can serve the static files.

## Run locally

```bash
python3 operator/main.py --dry-run
python3 operator/main.py
```

No Python dependencies outside the standard library are required.

## Autonomy and safety

The initial budget is $0. The operator fails closed if a paid service or quota risk appears. It does not fabricate reviews, credentials, customers, results, or human identities. Owner intervention is reserved for identity verification, tax information, CAPTCHA, two-factor authentication, financial-account setup, materially revised legal terms, and spending beyond the reinvestment policy.

## Official challenge clock

The owner sent `START` on **August 24, 2026**. Day 1 begins immediately and Day 90 ends on **November 21, 2026**. The 72-hour health streak remains visible as a reliability measurement, but it does not delay the economic clock. The primary score is verified net cash actually received after fees, refunds, and authorized expenses.
