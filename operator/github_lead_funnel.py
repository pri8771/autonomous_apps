#!/usr/bin/env python3
"""Keep the public defect-pack request path wired to the GitHub intake workflow."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "founding-audit.html"
ISSUE_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "commercelint-defect-pack.yml"
INTAKE_WORKFLOW = ROOT / ".github" / "workflows" / "lead-intake.yml"
INTAKE_SCRIPT = ROOT / "operator" / "lead_intake.py"
REQUEST_URL = (
    "https://github.com/pri8771/autonomous_apps/issues/new"
    "?template=commercelint-defect-pack.yml"
)
PANEL_MARKER = 'data-commercelint-github-intake="v1"'


def main() -> int:
    required = [PAGE, ISSUE_FORM, INTAKE_WORKFLOW, INTAKE_SCRIPT]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing lead-funnel assets: " + ", ".join(missing))

    content = PAGE.read_text(encoding="utf-8")
    content = content.replace("window.machineCartTrack?.", "window.commerceLintTrack?.")
    content = content.replace(
        "<title>Founding AI-Shopping Readiness Audit | CommerceLint</title>",
        "<title>Request a plan | CommerceLint</title>",
    )
    content = content.replace(
        'content="Request a $49 evidence-backed ecommerce readiness audit and implementation backlog."',
        'content="Request Sample $1.99, Lite $9.99 or Comprehensive $19.99 selected public-page diagnostics."',
    )
    content = content.replace(
        "<h1>Turn a readiness score into a repair backlog.</h1>",
        "<h1>Turn product-page evidence into a repair backlog.</h1>",
    )
    content = content.replace(
        "For $49, CommerceLint reviews a representative sample of your public catalog and delivers evidence your developer or agency can act on.",
        "Choose Sample $1.99 (automated field checks for 1 public product URL), Lite $9.99 (up to 5) or Comprehensive $19.99 (up to 15). Scope and terms are confirmed before payment.",
    )

    if PANEL_MARKER not in content:
        old = """      <section class="scanner-card lead-card" id="request">
        <p class="eyebrow">Request an audit</p>
        <h2>Tell CommerceLint what to inspect.</h2>"""
        if old not in content:
            raise SystemExit("The founding-offer request insertion point was not found.")
        panel = f"""      <section class="scanner-card lead-card" id="request" {PANEL_MARKER}>
        <p class="eyebrow">Fastest path for public stores</p>
        <h2>Open a GitHub request and get an automated first pass.</h2>
        <p>Supply one public storefront or product URL. The intake worker validates that the address is public, records the lead durably, performs a bounded HTML review, and posts reproducible evidence back to the request.</p>
        <div class="notice"><strong>Public by design:</strong> GitHub requests are visible to everyone. Never include credentials, customer data, private URLs, unpublished information, or payment details. Use the private email option for confidential context.</div>
        <div class="button-row">
          <a class="button" href="{REQUEST_URL}">Open public defect-pack request</a>
          <a class="button secondary" href="#private-email">Use private email instead</a>
        </div>
        <p class="field-help">Opening a request is free and does not create a purchase obligation. Plans are Sample $1.99 (1 public product URL), Lite $9.99 (up to 5) and Comprehensive $19.99 (up to 15). Sample is automated field screening, not bespoke manual review. Scope is confirmed before payment; checkout is not connected.</p>
      </section>

      <section class="scanner-card lead-card" id="private-email">
        <p class="eyebrow">Private email request</p>
        <h2>Tell CommerceLint what to inspect.</h2>"""
        content = content.replace(old, panel, 1)

    content = content.replace(
        '<button class="button" type="submit">Prepare audit request</button>',
        '<button class="button" type="submit">Prepare private email request</button>',
    )
    content = content.replace(
        "CommerceLint founding audit request",
        "CommerceLint founding defect-pack request",
    )
    content = content.replace(
        "I understand the initial price is $49, scope is confirmed before payment, and the audit does not guarantee indexing, recommendation, or sales.",
        "I understand this is a plan inquiry, not a purchase. Scope and terms are confirmed before payment, and the work does not guarantee indexing, recommendation, traffic, or sales.",
    )

    if PANEL_MARKER not in content or REQUEST_URL not in content:
        raise SystemExit("The GitHub intake panel was not installed.")
    if 'id="request"' not in content or 'id="private-email"' not in content:
        raise SystemExit("The public and private request anchors are incomplete.")
    if "machineCartTrack" in content:
        raise SystemExit("A retired analytics callback remains in the founding page.")

    PAGE.write_text(content, encoding="utf-8")
    print("CommerceLint GitHub lead funnel is present and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
