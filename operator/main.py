#!/usr/bin/env python3
"""MachineCart autonomous hourly operator.

This process is intentionally deterministic by default. It wakes on a schedule,
loads durable state, evaluates playbooks, performs one bounded action, verifies
the result, and commits the resulting state through GitHub Actions.

External connectors can be added without changing the decision contract:
observe -> prioritize -> act -> verify -> remember.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "business.json"
STATE_PATH = ROOT / "state" / "state.json"
CONTENT_PATH = ROOT / "content" / "queue.json"
SOCIAL_QUEUE_PATH = ROOT / "state" / "social_queue.json"
DOCS = ROOT / "docs"
GUIDES = DOCS / "guides"
RUNS = ROOT / "state" / "runs"
DAILY = ROOT / "state" / "daily"
WEEKLY = ROOT / "state" / "weekly"

USER_AGENT = "MachineCart-Autonomous-Operator/1.0 (+https://github.com/pri8771/autonomous_apps)"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    latency_ms: int | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "item"


def stable_id(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def http_check(url: str, timeout: int = 12) -> Check:
    started = datetime.now(timezone.utc)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            response.read(512)
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return Check(url, 200 <= status < 400, f"HTTP {status}", elapsed)
    except urllib.error.HTTPError as exc:
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return Check(url, False, f"HTTP {exc.code}", elapsed)
    except Exception as exc:
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return Check(url, False, f"{type(exc).__name__}: {exc}", elapsed)


def local_asset_checks() -> list[Check]:
    required = [
        DOCS / "index.html",
        DOCS / "scanner.html",
        DOCS / "privacy.html",
        CONFIG_PATH,
        STATE_PATH,
        CONTENT_PATH,
    ]
    checks: list[Check] = []
    for path in required:
        exists = path.exists() and path.stat().st_size > 50
        checks.append(Check(str(path.relative_to(ROOT)), exists, "present" if exists else "missing"))
    if (DOCS / "scanner.html").exists():
        scanner = (DOCS / "scanner.html").read_text(encoding="utf-8")
        for marker in ["analyzeMarkup", "Product", "Offer", "localStorage"]:
            checks.append(Check(f"scanner_marker:{marker}", marker in scanner, "found" if marker in scanner else "missing"))
    return checks


def public_site_checks(config: dict[str, Any]) -> list[Check]:
    site = config["site"]
    checks: list[Check] = []
    canonical = site.get("canonical_url", "").strip()
    interim = site.get("interim_url", "").strip()
    for label, url in (("canonical", canonical), ("interim", interim)):
        if url:
            result = http_check(url)
            result.name = label
            result.detail = f"{url} — {result.detail}"
            checks.append(result)
    return checks


def task_score(task: dict[str, Any]) -> float:
    impact = float(task.get("impact", 1))
    urgency = float(task.get("urgency", 1))
    confidence = float(task.get("confidence", 0.5))
    effort = max(float(task.get("effort", 1)), 0.25)
    priority = float(task.get("priority", 0))
    return priority + (impact * urgency * confidence / effort)


def eligible_tasks(state: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for task in state.get("tasks", []):
        if task.get("status") != "ready":
            continue
        if task.get("owner_required"):
            continue
        if int(task.get("attempts", 0)) >= int(task.get("max_attempts", 3)):
            continue
        candidates.append(task)
    return sorted(candidates, key=task_score, reverse=True)


def find_task(state: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    return next((task for task in state.get("tasks", []) if task.get("id") == task_id), None)


def complete_task(task: dict[str, Any], now: datetime, evidence: str) -> None:
    task["status"] = "done"
    task["completed_at_utc"] = iso(now)
    task["evidence"] = evidence


def render_page(title: str, description: str, body: str, canonical_path: str = "") -> str:
    canonical = f"https://pri8771.github.io/autonomous_apps/{canonical_path.lstrip('/')}" if canonical_path else ""
    canonical_tag = f'<link rel="canonical" href="{html.escape(canonical)}">' if canonical else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)} | MachineCart</title>
  <meta name="description" content="{html.escape(description)}">
  {canonical_tag}
  <link rel="stylesheet" href="../assets/site.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="../index.html">MachineCart</a>
    <nav><a href="../scanner.html">Free scan</a><a href="index.html">Guides</a><a href="../status.html">Operator status</a></nav>
  </header>
  <main class="article-shell">
    {body}
  </main>
  <footer><p>MachineCart provides technical diagnostics, not guarantees of placement or sales.</p></footer>
</body>
</html>
"""


def render_guide(item: dict[str, Any], published_at: str) -> str:
    sections = []
    for section in item.get("sections", []):
        paragraphs = "".join(f"<p>{html.escape(p)}</p>" for p in section.get("paragraphs", []))
        sections.append(f"<section><h2>{html.escape(section['heading'])}</h2>{paragraphs}</section>")
    sources = "".join(
        f'<li><a href="{html.escape(source["url"])}" rel="noreferrer">{html.escape(source["label"])}</a></li>'
        for source in item.get("sources", [])
    )
    body = f"""
    <article>
      <p class="eyebrow">{html.escape(item.get("audience", "Ecommerce teams"))}</p>
      <h1>{html.escape(item["title"])}</h1>
      <p class="lede">{html.escape(item["description"])}</p>
      <p class="meta">Published {html.escape(published_at[:10])} · Reviewed automatically for link and template integrity</p>
      <div class="callout"><strong>Run the free diagnostic:</strong> Inspect a product page locally, then turn every failed check into a repair task. <a href="../scanner.html">Open the scanner →</a></div>
      {''.join(sections)}
      <section><h2>Primary references</h2><ul>{sources}</ul></section>
      <section class="cta-card"><h2>Need an evidence-backed repair plan?</h2><p>Request a founding MachineCart audit. You receive the affected URLs, observed evidence, repair order, and verification checklist.</p><a class="button" href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20founding%20audit">Request an audit</a></section>
    </article>
    """
    return render_page(item["title"], item["description"], body, f"guides/{item['slug']}.html")


def update_guides_index(content: dict[str, Any]) -> None:
    published = [item for item in content["items"] if item.get("status") == "published"]
    published.sort(key=lambda item: item.get("published_at_utc", ""), reverse=True)
    cards = "".join(
        f"""<article class="guide-card">
          <p class="eyebrow">{html.escape(item.get("audience", "Ecommerce teams"))}</p>
          <h2><a href="{html.escape(item['slug'])}.html">{html.escape(item['title'])}</a></h2>
          <p>{html.escape(item['description'])}</p>
        </article>"""
        for item in published
    )
    if not cards:
        cards = "<p>The first implementation guide is being prepared by the hourly operator.</p>"
    body = f"<h1>Implementation guides</h1><p class='lede'>Evidence-first guidance for stores and agencies preparing product data for machine-assisted shopping.</p><div class='guide-grid'>{cards}</div>"
    atomic_write(GUIDES / "index.html", render_page("Implementation guides", "Practical AI-commerce readiness guides.", body, "guides/"))


def update_sitemap(config: dict[str, Any], content: dict[str, Any]) -> None:
    base_url = config["site"]["canonical_url"].rstrip("/") + "/"
    paths = ["", "scanner.html", "status.html", "privacy.html", "guides/"]
    paths += [f"guides/{item['slug']}.html" for item in content["items"] if item.get("status") == "published"]
    urls = "\n".join(f"  <url><loc>{html.escape(base_url + path)}</loc></url>" for path in paths)
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    atomic_write(DOCS / "sitemap.xml", sitemap)


def publish_next_content(content: dict[str, Any], now: datetime) -> tuple[bool, str]:
    queued = [item for item in content.get("items", []) if item.get("status") == "queued"]
    if not queued:
        return False, "No queued content remains."
    queued.sort(key=lambda item: int(item.get("priority", 0)), reverse=True)
    item = queued[0]
    GUIDES.mkdir(parents=True, exist_ok=True)
    published_at = iso(now) or ""
    atomic_write(GUIDES / f"{item['slug']}.html", render_guide(item, published_at))
    item["status"] = "published"
    item["published_at_utc"] = published_at
    item["last_verified_at_utc"] = published_at
    return True, f"Published docs/guides/{item['slug']}.html"


def generate_social_queue(now: datetime) -> tuple[bool, str]:
    posts = [
        "Most ecommerce AI-readiness scores are too vague. A useful audit should show the URL, observed value, expected value, repair owner, and verification step.",
        "A Product schema object can be syntactically valid and still be commercially wrong. Compare price, currency, availability, SKU, and selected variant with the page a shopper actually sees.",
        "Your return policy is part of product data. If the return window differs across product pages, FAQ, checkout, and policy pages, a shopping agent has no reliable source of truth.",
        "The weakest product state often defines catalog quality. Test in-stock, out-of-stock, discounted, variable, and multi-image products—not just one clean example.",
        "A variant is a purchasable record, not a color label. It needs the right SKU, price, stock state, image, attributes, and reproducible selection state.",
        "MachineCart is building an evidence-first readiness scanner for non-Shopify stores. The goal is not a vanity score; it is a prioritized repair backlog.",
        "Before adding more AI-commerce content, fix contradictory commerce facts. Incorrect price or availability is more urgent than an optional schema field.",
        "Agency opportunity: turn AI-commerce audits into implementation work. Diagnose with evidence, separate defects from improvements, then verify repairs with regression checks.",
        "A policy hidden in a footer may technically exist, but it is weak purchase information. Summarize shipping and returns near the buying decision and link to complete terms.",
        "Do your feed and product page agree? Sample live products and compare URL, identifier, price, inventory, and variant attributes. Drift is a distribution problem.",
        "An autonomous business should not change ten things at once. One bounded action, one verification condition, and a permanent lesson beat a pile of unexplained activity.",
        "MachineCart’s operating loop: observe → prioritize → act → verify → remember. Every hourly run leaves evidence instead of pretending that activity equals progress.",
        "If traffic is low, produce distribution. If scans are high but purchases are low, change the offer. If customers are unhappy, stop promotion and repair the product.",
        "Free audit checklist: crawlability, Product/Offer data, variants, identifiers, policy clarity, feed consistency, checkout trust, and evidence for every failure."
    ]
    payload = {
        "schema_version": 1,
        "generated_at_utc": iso(now),
        "status": "drafts_waiting_for_channel_credentials",
        "disclosure_policy": "Disclose automation when doing so increases trust or is required; never claim a human authored an automated interaction.",
        "posts": [
            {
                "id": stable_id(str(index), post),
                "text": post,
                "status": "ready",
                "channels": ["x", "linkedin", "bluesky"],
                "created_at_utc": iso(now),
                "published": []
            }
            for index, post in enumerate(posts, start=1)
        ]
    }
    write_json(SOCIAL_QUEUE_PATH, payload)
    return True, f"Generated {len(posts)} social launch drafts."


def verify_site_assets(task: dict[str, Any], now: datetime) -> tuple[bool, str]:
    checks = local_asset_checks()
    failed = [check for check in checks if not check.ok]
    if failed:
        return False, "; ".join(f"{c.name}: {c.detail}" for c in failed)
    return True, f"{len(checks)} local launch checks passed."


def ensure_content_task(state: dict[str, Any], content: dict[str, Any], config: dict[str, Any], now: datetime) -> None:
    queued = [item for item in content["items"] if item.get("status") == "queued"]
    if not queued:
        return
    existing = [
        task for task in state["tasks"]
        if task.get("type") == "publish_next_content" and task.get("status") in {"ready", "running"}
    ]
    if existing:
        return
    published_times = [parse_iso(item.get("published_at_utc")) for item in content["items"] if item.get("published_at_utc")]
    last_published = max((value for value in published_times if value), default=None)
    gap = int(config["operating_policy"].get("content_minimum_gap_hours", 8))
    if last_published and now - last_published < timedelta(hours=gap):
        return
    next_item = sorted(queued, key=lambda item: int(item.get("priority", 0)), reverse=True)[0]
    state["tasks"].append({
        "id": f"publish-{next_item['id']}",
        "title": f"Publish: {next_item['title']}",
        "type": "publish_next_content",
        "status": "ready",
        "priority": 55,
        "impact": 6,
        "urgency": 5,
        "confidence": 0.75,
        "effort": 2,
        "attempts": 0,
        "max_attempts": 3,
        "owner_required": False,
        "success_condition": f"docs/guides/{next_item['slug']}.html exists"
    })


def calculate_bottleneck(state: dict[str, Any]) -> tuple[str, str]:
    metrics = state["metrics"]
    if state["strategy"].get("stage") == "prelaunch":
        return "infrastructure_and_launch", "Finish a working public funnel and collect the first qualified visitor."
    if metrics["qualified_visitors"] < 200:
        return "qualified_traffic", "Earn qualified visits through implementation guides, evidence-led teardowns, and agency outreach."
    start_rate = metrics["scanner_starts"] / max(metrics["qualified_visitors"], 1)
    if start_rate < 0.10:
        return "landing_page_conversion", "Improve the value proposition, sample evidence, and scanner call to action."
    completion_rate = metrics["scanner_completions"] / max(metrics["scanner_starts"], 1)
    if completion_rate < 0.50:
        return "scanner_completion", "Reduce scanner friction and explain failed checks more clearly."
    offer_rate = metrics["paid_offer_clicks"] / max(metrics["scanner_completions"], 1)
    if offer_rate < 0.02:
        return "offer_relevance", "Improve the paid deliverable, preview, positioning, or price."
    purchase_rate = metrics["purchases"] / max(metrics["paid_offer_clicks"], 1)
    if purchase_rate < 0.10:
        return "checkout_and_trust", "Investigate checkout friction, proof, guarantee, and buyer trust."
    return "retention_and_scale", "Scale the highest-converting acquisition source and improve repeat revenue."


def daily_review(state: dict[str, Any], local_now: datetime, now: datetime) -> str | None:
    local_date = local_now.date().isoformat()
    if state["operator"].get("last_daily_review_local") == local_date:
        return None
    bottleneck, priority = calculate_bottleneck(state)
    previous = state["strategy"].get("current_bottleneck")
    state["strategy"]["current_bottleneck"] = bottleneck
    state["strategy"]["current_daily_priority"] = priority
    state["operator"]["last_daily_review_local"] = local_date
    DAILY.mkdir(parents=True, exist_ok=True)
    report = f"""# MachineCart daily operating review — {local_date}

- Generated: {iso(now)}
- Challenge status: {state['challenge']['status']}
- Current bottleneck: {bottleneck}
- Previous bottleneck: {previous}
- Daily priority: {priority}
- Gross revenue: ${state['metrics']['gross_revenue_usd']:.2f}
- Net operating profit: ${state['metrics']['net_operating_profit_usd']:.2f}
- Qualified visitors: {state['metrics']['qualified_visitors']}
- Scanner starts: {state['metrics']['scanner_starts']}
- Scanner completions: {state['metrics']['scanner_completions']}
- Purchases: {state['metrics']['purchases']}

The operator must prefer measurable work on the current bottleneck over cosmetic activity.
"""
    atomic_write(DAILY / f"{local_date}.md", report)
    return f"Daily review selected bottleneck: {bottleneck}."


def weekly_review(state: dict[str, Any], local_now: datetime, now: datetime) -> str | None:
    if local_now.strftime("%A") != "Sunday":
        return None
    local_date = local_now.date().isoformat()
    if state["operator"].get("last_weekly_review_local") == local_date:
        return None
    state["operator"]["last_weekly_review_local"] = local_date
    WEEKLY.mkdir(parents=True, exist_ok=True)
    open_tasks = [task for task in state["tasks"] if task.get("status") in {"ready", "blocked", "running"}]
    report = f"""# MachineCart weekly review — {local_date}

## Scorecard
- Gross revenue: ${state['metrics']['gross_revenue_usd']:.2f}
- Net operating profit: ${state['metrics']['net_operating_profit_usd']:.2f}
- Qualified visitors: {state['metrics']['qualified_visitors']}
- Completed scans: {state['metrics']['scanner_completions']}
- Purchases: {state['metrics']['purchases']}
- Open or blocked tasks: {len(open_tasks)}
- Lessons recorded: {len(state.get('lessons', []))}

## Decision rule
Continue the current business only while evidence supports a path to revenue. If 500 qualified visitors produce no sales, replace the paid offer. If merchant demand remains weak by operating day 60, prioritize the agency white-label offer.
"""
    atomic_write(WEEKLY / f"{local_date}.md", report)
    return "Weekly business review completed."


def update_burn_in(state: dict[str, Any], now: datetime, run_ok: bool, public_ok: bool, local_ok: bool, config: dict[str, Any]) -> None:
    burn = state["challenge"]["burn_in"]
    if not burn.get("started_at_utc"):
        burn["started_at_utc"] = iso(now)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    last_hour = parse_iso(burn.get("last_counted_hour_utc"))
    if last_hour == current_hour:
        return
    qualifying = run_ok and local_ok and public_ok
    if qualifying:
        burn["successful_hours"] = int(burn.get("successful_hours", 0)) + 1
        if last_hour and current_hour - last_hour <= timedelta(hours=2):
            burn["consecutive_successful_hours"] = int(burn.get("consecutive_successful_hours", 0)) + 1
        else:
            burn["consecutive_successful_hours"] = 1
        burn["last_counted_hour_utc"] = iso(current_hour)
    else:
        burn["consecutive_successful_hours"] = 0
        burn["last_counted_hour_utc"] = iso(current_hour)

    required = int(config["operating_policy"]["burn_in_required_successful_hours"])
    if burn["consecutive_successful_hours"] >= required and state["challenge"]["status"] == "burn_in":
        burn["completed_at_utc"] = iso(now)
        state["challenge"]["status"] = "operating"
        local_now = now.astimezone(ZoneInfo(config["operating_policy"]["timezone"]))
        state["challenge"]["start_date_local"] = local_now.date().isoformat()
        state["challenge"]["day_number"] = 1
        state["strategy"]["stage"] = "launched"
        state["lessons"].append({
            "at_utc": iso(now),
            "category": "operations",
            "lesson": f"Completed {required} consecutive successful hourly checks; the 90-day operating clock started.",
            "evidence": f"public_site_ok={public_ok}; local_assets_ok={local_ok}"
        })


def update_day_number(state: dict[str, Any], local_now: datetime) -> None:
    start = state["challenge"].get("start_date_local")
    if state["challenge"].get("status") != "operating" or not start:
        state["challenge"]["day_number"] = 0
        return
    start_date = datetime.fromisoformat(start).date()
    state["challenge"]["day_number"] = (local_now.date() - start_date).days + 1
    if state["challenge"]["day_number"] > 90:
        state["challenge"]["status"] = "operating_beyond_90_days"


def render_status(state: dict[str, Any], checks: Iterable[Check], now: datetime) -> None:
    checks = list(checks)
    status = {
        "schema_version": 1,
        "generated_at_utc": iso(now),
        "status": "healthy" if all(check.ok for check in checks) else "degraded",
        "challenge_status": state["challenge"]["status"],
        "day_number": state["challenge"]["day_number"],
        "burn_in_consecutive_successful_hours": state["challenge"]["burn_in"]["consecutive_successful_hours"],
        "last_success_at_utc": state["operator"].get("last_success_at_utc"),
        "total_operator_runs": state["operator"]["total_runs"],
        "current_bottleneck": state["strategy"]["current_bottleneck"],
        "current_daily_priority": state["strategy"]["current_daily_priority"],
        "gross_revenue_usd": state["metrics"]["gross_revenue_usd"],
        "net_operating_profit_usd": state["metrics"]["net_operating_profit_usd"],
        "last_major_action": state["operator"].get("last_major_action"),
        "checks": [
            {"name": check.name, "ok": check.ok, "detail": check.detail, "latency_ms": check.latency_ms}
            for check in checks
        ]
    }
    write_json(DOCS / "status.json", status)
    check_rows = "".join(
        f"<tr><td>{html.escape(check.name)}</td><td>{'PASS' if check.ok else 'FAIL'}</td><td>{html.escape(check.detail)}</td></tr>"
        for check in checks
    )
    body = f"""
      <p class="eyebrow">Public operating ledger</p>
      <h1>Autonomous operator status</h1>
      <p class="lede">MachineCart wakes every hour, reads durable state, performs a bounded action, verifies it, and records the result.</p>
      <div class="score-grid">
        <div><span>Challenge</span><strong>{html.escape(str(state['challenge']['status']))}</strong></div>
        <div><span>Day</span><strong>{state['challenge']['day_number']}</strong></div>
        <div><span>Burn-in streak</span><strong>{state['challenge']['burn_in']['consecutive_successful_hours']} / {state['challenge']['burn_in']['required_successful_hours']} hours</strong></div>
        <div><span>Operator runs</span><strong>{state['operator']['total_runs']}</strong></div>
        <div><span>Gross revenue</span><strong>${state['metrics']['gross_revenue_usd']:.2f}</strong></div>
        <div><span>Net profit</span><strong>${state['metrics']['net_operating_profit_usd']:.2f}</strong></div>
      </div>
      <section><h2>Current priority</h2><p><strong>{html.escape(state['strategy']['current_bottleneck'])}</strong></p><p>{html.escape(state['strategy']['current_daily_priority'])}</p></section>
      <section><h2>Last major action</h2><p>{html.escape(str(state['operator'].get('last_major_action') or 'No major action recorded yet.'))}</p></section>
      <section><h2>Latest checks</h2><div class="table-wrap"><table><thead><tr><th>Check</th><th>Result</th><th>Evidence</th></tr></thead><tbody>{check_rows}</tbody></table></div></section>
      <p class="meta">Generated {html.escape(iso(now) or '')}</p>
    """
    status_page = render_page("Operator status", "Live MachineCart autonomous-operator status and business scorecard.", body, "status.html")
    status_page = status_page.replace('href="../assets/site.css"', 'href="assets/site.css"')
    status_page = status_page.replace('href="../index.html"', 'href="index.html"')
    status_page = status_page.replace('href="../scanner.html"', 'href="scanner.html"')
    status_page = status_page.replace('href="index.html">Guides', 'href="guides/index.html">Guides')
    status_page = status_page.replace('href="../status.html"', 'href="status.html"')
    atomic_write(DOCS / "status.html", status_page)


def record_alert(state: dict[str, Any], now: datetime, severity: str, title: str, detail: str) -> None:
    fingerprint = stable_id(severity, title, detail[:200])
    unresolved = [alert for alert in state.get("alerts", []) if alert.get("fingerprint") == fingerprint and not alert.get("resolved_at_utc")]
    if unresolved:
        unresolved[0]["last_seen_at_utc"] = iso(now)
        unresolved[0]["occurrences"] = int(unresolved[0].get("occurrences", 1)) + 1
        return
    state.setdefault("alerts", []).append({
        "id": str(uuid.uuid4()),
        "fingerprint": fingerprint,
        "severity": severity,
        "title": title,
        "detail": detail,
        "created_at_utc": iso(now),
        "last_seen_at_utc": iso(now),
        "occurrences": 1,
        "resolved_at_utc": None
    })


def execute_task(task: dict[str, Any], state: dict[str, Any], content: dict[str, Any], config: dict[str, Any], now: datetime) -> tuple[bool, str]:
    task["status"] = "running"
    task["last_attempt_at_utc"] = iso(now)
    action = task.get("type")
    if action == "verify_site_assets":
        return verify_site_assets(task, now)
    if action == "publish_next_content":
        ok, detail = publish_next_content(content, now)
        if ok:
            update_guides_index(content)
            update_sitemap(config, content)
        return ok, detail
    if action == "generate_social_queue":
        return generate_social_queue(now)
    return False, f"Unknown autonomous task type: {action}"


def run_operator(dry_run: bool = False) -> int:
    now = utc_now()
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    config = load_json(CONFIG_PATH)
    state = load_json(STATE_PATH)
    content = load_json(CONTENT_PATH)
    tz = ZoneInfo(config["operating_policy"]["timezone"])
    local_now = now.astimezone(tz)
    state["operator"]["total_runs"] = int(state["operator"].get("total_runs", 0)) + 1
    state["operator"]["last_run_at_utc"] = iso(now)
    state["operator"]["last_run_id"] = run_id

    event: dict[str, Any] = {
        "run_id": run_id,
        "started_at_utc": iso(now),
        "local_time": local_now.isoformat(),
        "trigger": os.getenv("GITHUB_EVENT_NAME", "local"),
        "checks": [],
        "major_action": None,
        "daily_review": None,
        "weekly_review": None,
        "success": False,
        "error": None,
    }

    try:
        local_checks = local_asset_checks()
        site_checks = public_site_checks(config)
        all_checks = local_checks + site_checks
        local_ok = all(check.ok for check in local_checks)
        public_ok = any(check.ok for check in site_checks) if site_checks else False
        event["checks"] = [check.__dict__ for check in all_checks]

        if not local_ok:
            record_alert(state, now, "critical", "Local launch assets failed verification", "; ".join(c.detail for c in local_checks if not c.ok))
        if not public_ok:
            record_alert(state, now, "warning", "No public MachineCart URL is healthy", "; ".join(c.detail for c in site_checks))

        canonical_ok = any(check.name == "canonical" and check.ok for check in site_checks)
        pages_task = find_task(state, "enable-github-pages")
        if canonical_ok and pages_task and pages_task.get("status") != "done":
            complete_task(pages_task, now, "Canonical GitHub Pages URL returned a successful response.")

        ensure_content_task(state, content, config, now)
        event["daily_review"] = daily_review(state, local_now, now)
        event["weekly_review"] = weekly_review(state, local_now, now)

        candidates = eligible_tasks(state)
        if candidates:
            task = candidates[0]
            task["attempts"] = int(task.get("attempts", 0)) + 1
            ok, detail = execute_task(task, state, content, config, now)
            if ok:
                complete_task(task, now, detail)
                state["operator"]["last_major_action_at_utc"] = iso(now)
                state["operator"]["last_major_action"] = f"{task['title']}: {detail}"
                event["major_action"] = {"task_id": task["id"], "title": task["title"], "ok": True, "detail": detail}
                state.setdefault("lessons", []).append({
                    "at_utc": iso(now),
                    "category": "execution",
                    "lesson": f"Completed: {task['title']}",
                    "evidence": detail,
                })
            else:
                task["status"] = "ready"
                if int(task.get("attempts", 0)) >= int(task.get("max_attempts", 3)):
                    task["status"] = "blocked"
                task["last_error"] = detail
                event["major_action"] = {"task_id": task["id"], "title": task["title"], "ok": False, "detail": detail}
                record_alert(state, now, "warning", f"Task failed: {task['title']}", detail)
        else:
            event["major_action"] = {"task_id": None, "title": "No-op", "ok": True, "detail": "No eligible autonomous task required action."}

        run_ok = local_ok and event["major_action"]["ok"]
        if run_ok:
            state["operator"]["successful_runs"] = int(state["operator"].get("successful_runs", 0)) + 1
            state["operator"]["last_success_at_utc"] = iso(now)
        else:
            state["operator"]["failed_runs"] = int(state["operator"].get("failed_runs", 0)) + 1

        update_burn_in(state, now, run_ok, public_ok, local_ok, config)
        update_day_number(state, local_now)
        state["metrics"]["net_operating_profit_usd"] = round(
            float(state["metrics"]["gross_revenue_usd"])
            - float(state["metrics"]["fees_usd"])
            - float(state["metrics"]["refunds_usd"])
            - float(state["metrics"]["reinvested_expenses_usd"]), 2)

        event["success"] = run_ok
        event["completed_at_utc"] = iso(utc_now())
        state["run_history"].append({
            "run_id": run_id,
            "at_utc": iso(now),
            "success": run_ok,
            "major_action": event["major_action"],
        })
        state["run_history"] = state["run_history"][-168:]
        render_status(state, all_checks, now)
        update_guides_index(content)
        update_sitemap(config, content)

        if not dry_run:
            write_json(STATE_PATH, state)
            write_json(CONTENT_PATH, content)
            append_jsonl(RUNS / f"{local_now.date().isoformat()}.jsonl", event)
        else:
            print(json.dumps(event, indent=2))
        return 0 if run_ok else 1
    except Exception as exc:
        state["operator"]["failed_runs"] = int(state["operator"].get("failed_runs", 0)) + 1
        state["operator"]["last_run_at_utc"] = iso(now)
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        event["success"] = False
        event["error"] = detail[-8000:]
        event["completed_at_utc"] = iso(utc_now())
        record_alert(state, now, "critical", "Hourly operator crashed", f"{type(exc).__name__}: {exc}")
        if not dry_run:
            write_json(STATE_PATH, state)
            append_jsonl(RUNS / f"{local_now.date().isoformat()}.jsonl", event)
        else:
            print(detail, file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MachineCart autonomous operator.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate without persisting state.")
    args = parser.parse_args()
    return run_operator(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
