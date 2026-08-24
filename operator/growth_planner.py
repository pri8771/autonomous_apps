#!/usr/bin/env python3
"""MachineCart deterministic growth planner.

Runs every six hours. It keeps the acquisition backlog stocked, maintains the
sales funnel, and hands executable work to the hourly operator through durable
files. It requires no paid API and never invents customer results.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "content" / "queue.json"
GROWTH_STATE_PATH = ROOT / "state" / "growth_state.json"
INDEX_PATH = ROOT / "docs" / "index.html"
SCANNER_PATH = ROOT / "docs" / "scanner.html"
OPERATOR_PATH = ROOT / "operator" / "main.py"
DOCS = ROOT / "docs"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(value, encoding="utf-8")
    temp.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


PLATFORMS = [
    {
        "slug": "wix-stores",
        "name": "Wix Stores",
        "audience": "Wix merchants and implementers",
        "context": "Review the live product template, every installed commerce app, and representative catalog states rather than assuming the platform default remains unchanged.",
    },
    {
        "slug": "squarespace-commerce",
        "name": "Squarespace Commerce",
        "audience": "Squarespace merchants and designers",
        "context": "Test the published storefront after template, extension, and custom-code changes because the customer-visible offer is the source that must remain consistent.",
    },
    {
        "slug": "bigcommerce",
        "name": "BigCommerce",
        "audience": "BigCommerce teams and agencies",
        "context": "Sample products across themes, channels, price lists, and variant states so channel-specific data does not silently drift from the canonical catalog.",
    },
    {
        "slug": "adobe-commerce",
        "name": "Adobe Commerce",
        "audience": "Adobe Commerce and Magento teams",
        "context": "Treat theme output, extensions, indexing, store views, and configurable products as separate failure surfaces that require evidence from the live page.",
    },
    {
        "slug": "headless-commerce",
        "name": "Headless Commerce",
        "audience": "Headless commerce product and engineering teams",
        "context": "Verify that server-rendered or pre-rendered purchase facts stay synchronized with client state, catalog APIs, feeds, and checkout services.",
    },
]

TOPICS = [
    {
        "slug": "product-data-readiness",
        "title": "Product-Data Readiness Checklist",
        "description": "A reproducible review of product identity, structured data, identifiers, images, descriptions, and canonical URLs.",
        "keywords": ["AI shopping readiness", "product structured data", "ecommerce product audit"],
        "sections": [
            ("Establish the product source of truth", [
                "Document which system owns title, description, brand, SKU, global identifiers, images, canonical URL, and purchasable variants. Record the owner before changing templates or feeds.",
                "{context}",
            ]),
            ("Compare visible and machine-readable facts", [
                "Extract every Product or ProductGroup object and compare it with the product shoppers can see. A syntactically valid object can still identify the wrong item or stale variant.",
                "Prioritize contradictions over optional completeness. Incorrect identity, price, currency, or availability can change a purchase decision.",
            ]),
            ("Test representative catalog states", [
                "Include a simple product, a variable product, an out-of-stock item, a discounted item, and an item with multiple images. Preserve the URL and raw evidence for every defect.",
            ]),
            ("Turn findings into regression checks", [
                "Assign each failure to its likely source, define the expected value, and repeat the same sample after repair. Do not close the item on visual inspection alone.",
            ]),
        ],
    },
    {
        "slug": "offer-price-stock-consistency",
        "title": "Price and Availability Consistency Audit",
        "description": "How to find contradictions among the visible offer, structured data, feeds, variants, promotions, and checkout.",
        "keywords": ["Offer schema audit", "price availability consistency", "ecommerce stock data"],
        "sections": [
            ("Start with the selected purchasable state", [
                "Record the selected variant, visible price, currency, stock message, offer URL, and checkout eligibility. Those values—not a generic parent product—define the current offer.",
                "{context}",
            ]),
            ("Compare every distribution surface", [
                "Compare the page, Product/Offer JSON-LD, merchant feed, internal catalog API, and checkout. Flag any mismatch in price, currency, availability, identifier, or selected attributes.",
            ]),
            ("Exercise the states most likely to fail", [
                "Test sale pricing, scheduled promotions, low stock, sold-out variants, regional currency, customer-group pricing, and products that cannot ship to all destinations.",
            ]),
            ("Fix ownership before symptoms", [
                "Identify which system is authoritative for each field and remove duplicate calculations where possible. Add a regression sample that detects drift after releases and catalog imports.",
            ]),
        ],
    },
    {
        "slug": "variant-integrity-audit",
        "title": "Variant Integrity Audit",
        "description": "A practical check for size, color, material, SKU, price, image, URL, and availability relationships.",
        "keywords": ["product variant data", "ProductGroup audit", "ecommerce variant integrity"],
        "sections": [
            ("Model each purchasable combination", [
                "Treat a variant as a real purchasable record with its own attributes, identifier, offer, image, and stock state. A color or size label alone is not sufficient.",
                "{context}",
            ]),
            ("Look for silent parent-child mismatches", [
                "Check whether the selected option changes the structured offer, visible price, image, SKU, availability, and URL state. Common defects expose parent data after the shopper selects a child variant.",
            ]),
            ("Verify reproducible selection", [
                "Where practical, ensure the chosen variant can be revisited through a stable URL or deterministic state. Test browser refresh, link sharing, and direct entry.",
            ]),
            ("Sample edge cases", [
                "Include unavailable combinations, price-changing options, duplicate labels, missing images, and variants introduced by a recent import. Keep a known-good fixture for release testing.",
            ]),
        ],
    },
    {
        "slug": "shipping-returns-clarity",
        "title": "Shipping and Returns Clarity Audit",
        "description": "Make fulfillment and return constraints consistent, discoverable, and useful at the purchase decision.",
        "keywords": ["machine readable returns", "shipping policy audit", "ecommerce fulfillment clarity"],
        "sections": [
            ("Create one policy source of truth", [
                "Define which system owns destinations, processing times, delivery estimates, thresholds, return windows, fees, exclusions, and item-condition requirements.",
                "{context}",
            ]),
            ("Compare every customer surface", [
                "Check product pages, cart, checkout, FAQ, policy pages, confirmation messages, and structured data. Treat conflicting terms as defects, not copywriting differences.",
            ]),
            ("Put decision facts near the product", [
                "Summarize material shipping and return constraints near the buying decision and link to complete terms. A footer-only policy is technically reachable but commercially weak.",
            ]),
            ("Monitor operational drift", [
                "Re-run the sample after logistics, theme, marketplace, region, or app changes. Verify that policy text and actual checkout behavior still agree.",
            ]),
        ],
    },
]

SOURCES = [
    {"label": "Schema.org Product", "url": "https://schema.org/Product"},
    {"label": "Schema.org ProductGroup", "url": "https://schema.org/ProductGroup"},
    {"label": "Schema.org Offer", "url": "https://schema.org/Offer"},
    {"label": "Google product structured data", "url": "https://developers.google.com/search/docs/appearance/structured-data/product"},
]


def build_item(platform: dict[str, str], topic: dict[str, Any], priority: int) -> dict[str, Any]:
    sections = []
    for heading, paragraphs in topic["sections"]:
        sections.append({
            "heading": heading,
            "paragraphs": [paragraph.format(context=platform["context"]) for paragraph in paragraphs],
        })
    return {
        "id": f"{platform['slug']}-{topic['slug']}",
        "slug": f"{platform['slug']}-{topic['slug']}",
        "title": f"{platform['name']} {topic['title']}",
        "description": topic["description"],
        "audience": platform["audience"],
        "status": "queued",
        "priority": priority,
        "keywords": [platform["name"], *topic["keywords"]],
        "sections": sections,
        "sources": SOURCES,
        "planned_by": "deterministic-growth-planner-v1",
    }


def replenish_content(content: dict[str, Any]) -> int:
    existing = {item.get("id") for item in content.setdefault("items", [])}
    added = 0
    priority = 58
    for platform in PLATFORMS:
        for topic in TOPICS:
            item = build_item(platform, topic, priority)
            priority = max(priority - 1, 35)
            if item["id"] in existing:
                continue
            content["items"].append(item)
            existing.add(item["id"])
            added += 1
    return added


def page(title: str, description: str, body: str, canonical: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)} | MachineCart</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="canonical" href="https://pri8771.github.io/autonomous_apps/{canonical}">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-header"><a class="brand" href="index.html">MachineCart</a><nav><a href="scanner.html">Free scan</a><a href="sample-audit.html">Sample audit</a><a href="guides/index.html">Guides</a></nav></header>
  <main class="article-shell">{body}</main>
  <footer><div class="footer-row"><p>MachineCart provides evidence-backed technical diagnostics, not placement or revenue guarantees.</p><nav><a href="privacy.html">Privacy</a><a href="mailto:pchordia@unsubscriber.me">Contact</a></nav></div></footer>
</body>
</html>"""


def write_sales_pages() -> None:
    sample_body = """
<article>
  <p class="eyebrow">Example deliverable</p>
  <h1>Sample MachineCart audit</h1>
  <p class="lede">A useful audit does not stop at a score. It shows the exact evidence, commercial risk, probable source, repair order, owner, and verification method.</p>
  <div class="panel sample-table"><table>
    <thead><tr><th>Priority</th><th>Observed evidence</th><th>Why it matters</th><th>Repair and verification</th></tr></thead>
    <tbody>
      <tr><td class="fail">P0</td><td>Selected size is sold out, but Offer.availability reports InStock.</td><td>A machine can interpret an unavailable variant as purchasable.</td><td>Generate availability from the selected child SKU; re-test sold-out and in-stock fixtures.</td></tr>
      <tr><td class="fail">P0</td><td>Visible price is £39; structured offer reports 39 USD.</td><td>The offer describes a materially different commercial fact.</td><td>Use storefront currency from the pricing source; verify every active locale.</td></tr>
      <tr><td class="warn">P1</td><td>Product page says 30-day returns; checkout links to a 14-day policy.</td><td>The buyer and an automated system receive contradictory terms.</td><td>Choose one policy owner and synchronize product, FAQ, and checkout surfaces.</td></tr>
      <tr><td>P2</td><td>Product has SKU but no applicable GTIN or MPN explanation.</td><td>Identity reconciliation may be weaker across feeds and channels.</td><td>Add real identifiers when they exist; never fabricate one. Document legitimate absence.</td></tr>
    </tbody>
  </table></div>
  <section><h2>What the paid founding audit includes</h2><ul><li>Representative catalog sample across product states</li><li>Raw evidence for every finding</li><li>Defect-versus-improvement classification</li><li>Prioritized implementation backlog</li><li>Verification checklist for repaired pages</li></ul></section>
  <section class="cta-card"><h2>Founding audit: $49</h2><p>The first cohort helps validate the report and workflow. Payment is arranged only after scope is confirmed.</p><a class="button" href="founding-audit.html">Request the founding audit</a></section>
</article>"""
    atomic_write(DOCS / "sample-audit.html", page("Sample Ecommerce AI-Readiness Audit", "See the evidence, repair order, and verification detail included in a MachineCart audit.", sample_body, "sample-audit.html"))

    audit_body = """
<article>
  <p class="eyebrow">Founding customer offer</p>
  <h1>Turn a readiness score into a repair backlog.</h1>
  <p class="lede">For $49, MachineCart reviews a representative sample of your public catalog and delivers evidence your developer or agency can act on.</p>
  <div class="grid-3">
    <section class="panel"><h2>Evidence</h2><p>Affected URL, observed value, expected value, and reproducible context for each finding.</p></section>
    <section class="panel"><h2>Priority</h2><p>Incorrect commerce facts first, then identity and variants, followed by completeness improvements.</p></section>
    <section class="panel"><h2>Verification</h2><p>A compact regression checklist to confirm repairs across representative product states.</p></section>
  </div>
  <section><h2>Founding scope</h2><ul><li>Up to 15 public product URLs or one representative catalog sample</li><li>Product, Offer, variant, identifier, canonical, shipping, and returns checks</li><li>One report and one clarification round</li><li>No claim of guaranteed indexing, recommendation, or sales</li></ul></section>
  <section class="cta-card"><h2>Request the audit</h2><p>Send the store URL and platform. No payment is requested until the scope is accepted.</p><a class="button" href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20founding%20audit&body=Store%20URL%3A%0APlatform%3A%0AWhat%20changed%20recently%3A%0AMain%20concern%3A">Email the store details</a><a class="button secondary" href="sample-audit.html">View sample findings</a></section>
</article>"""
    atomic_write(DOCS / "founding-audit.html", page("Founding AI-Shopping Readiness Audit", "Request a $49 evidence-backed ecommerce readiness audit and implementation backlog.", audit_body, "founding-audit.html"))

    agency_body = """
<article>
  <p class="eyebrow">Agency pilot</p>
  <h1>Add an evidence-first AI-commerce audit to your service line.</h1>
  <p class="lede">Use a repeatable diagnostic to find implementation work without selling a vague score or unsupported ranking promise.</p>
  <div class="grid-3">
    <section class="panel"><h2>White-label structure</h2><p>Client-ready findings organized by affected URL, severity, probable source, owner, and verification.</p></section>
    <section class="panel"><h2>Implementation path</h2><p>Separate defects from opportunities so the client knows what is broken and what is merely incomplete.</p></section>
    <section class="panel"><h2>Reusable checks</h2><p>Keep representative fixtures and regression steps for future theme, app, feed, and catalog changes.</p></section>
  </div>
  <section class="cta-card"><h2>Join the founding agency pilot</h2><p>The pilot starts with one sample client audit. Commercial terms are agreed before any paid work.</p><a class="button" href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20agency%20pilot&body=Agency%20website%3A%0APlatforms%20served%3A%0ATypical%20client%20size%3A%0A">Request a pilot audit</a><a class="button secondary" href="sample-audit.html">See the report style</a></section>
</article>"""
    atomic_write(DOCS / "agency.html", page("MachineCart Agency Pilot", "A white-label, evidence-backed AI-commerce audit workflow for ecommerce agencies.", agency_body, "agency.html"))


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        return False
    atomic_write(path, text.replace(old, new, 1))
    return True


def patch_funnel() -> list[str]:
    changed = []
    replacements = [
        (INDEX_PATH, 'href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20founding%20audit"', 'href="founding-audit.html"'),
        (INDEX_PATH, 'href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20agency%20pilot"', 'href="agency.html"'),
        (SCANNER_PATH, 'href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20deep%20audit"', 'href="founding-audit.html"'),
        (OPERATOR_PATH, 'paths = ["", "scanner.html", "status.html", "privacy.html", "guides/"]', 'paths = ["", "scanner.html", "status.html", "privacy.html", "sample-audit.html", "founding-audit.html", "agency.html", "guides/"]'),
        (OPERATOR_PATH, 'href="mailto:pchordia@unsubscriber.me?subject=MachineCart%20founding%20audit"', 'href="../founding-audit.html"'),
    ]
    for path, old, new in replacements:
        if replace_once(path, old, new):
            changed.append(str(path.relative_to(ROOT)))
    return changed


def main() -> int:
    timestamp = now_iso()
    content = load_json(CONTENT_PATH, {"schema_version": 1, "items": []})
    growth = load_json(GROWTH_STATE_PATH, {"schema_version": 1, "total_runs": 0, "history": []})

    added = replenish_content(content)
    write_sales_pages()
    patched = patch_funnel()

    items = content.get("items", [])
    queued = sum(item.get("status") == "queued" for item in items)
    published = sum(item.get("status") == "published" for item in items)
    growth["total_runs"] = int(growth.get("total_runs", 0)) + 1
    growth["last_run_at_utc"] = timestamp
    growth["content_backlog"] = {"queued": queued, "published": published, "added_this_run": added}
    growth["funnel_assets"] = ["docs/sample-audit.html", "docs/founding-audit.html", "docs/agency.html"]
    growth["current_acquisition_thesis"] = "High-intent implementation guides and concrete sample evidence will attract merchants and agencies more effectively than generic AI-commerce commentary."
    growth["next_external_dependencies"] = [
        "Canonical production hosting or GitHub Pages activation",
        "Owner-verified payment checkout",
        "One authenticated social publishing channel",
        "First-party analytics endpoint",
    ]
    growth.setdefault("history", []).append({
        "at_utc": timestamp,
        "added_content_items": added,
        "queued_content_items": queued,
        "published_content_items": published,
        "patched_files": patched,
    })
    growth["history"] = growth["history"][-120:]

    write_json(CONTENT_PATH, content)
    write_json(GROWTH_STATE_PATH, growth)
    print(json.dumps(growth["history"][-1], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
