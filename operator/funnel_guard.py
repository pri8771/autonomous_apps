#!/usr/bin/env python3
"""Regression guard for CommerceLint's maintained commercial funnel."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def validate_sales_pages() -> None:
    """Raise when a maintained conversion asset has regressed."""

    requirements = {
        DOCS / "founding-audit.html": (
            "auditRequestForm",
            "contactEmail",
            "storeUrl",
            "assets/inquiry.js",
            'name="plan"',
        ),
        DOCS / "pricing.html": ("Sample", "$1.99", "Lite", "$9.99", "Comprehensive", "$19.99", "checkout is not connected"),
        DOCS / "assets" / "inquiry.js": ("audit-request-composed", "mailto:pchordia@unsubscriber.me", "Object.prototype.hasOwnProperty"),
        DOCS / "assets" / "plans.js": ("1.99", "9.99", "19.99"),
        DOCS / "agency.html": (
            "downloads/commercelint-audit-backlog.csv",
            "downloads/commercelint-audit-report-template.md",
        ),
        DOCS / "sample-audit.html": (
            "Sample CommerceLint audit",
            "founding-audit.html",
        ),
        DOCS / "methodology.html": (
            "How CommerceLint audits a store",
            "founding-audit.html",
        ),
        DOCS / "service.json": (
            '"paid_service"',
            '"price": 1.99',
            '"price": 9.99',
            '"price": 19.99',
        ),
        DOCS / "llms.txt": (
            "CommerceLint",
            "Pricing:",
        ),
        DOCS / "downloads" / "commercelint-audit-backlog.csv": (
            "finding_id",
            "verification_procedure",
        ),
        DOCS / "downloads" / "commercelint-audit-report-template.md": (
            "# AI-Shopping Readiness Audit",
            "## Regression checklist",
        ),
    }

    failures: list[str] = []
    for asset, markers in requirements.items():
        if not asset.exists():
            failures.append(f"{asset.relative_to(ROOT)}: missing")
            continue
        content = asset.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in content]
        if missing:
            failures.append(
                f"{asset.relative_to(ROOT)}: missing required markers {missing}"
            )

    if failures:
        raise RuntimeError("Commercial funnel regression: " + "; ".join(failures))


if __name__ == "__main__":
    validate_sales_pages()
    print("CommerceLint commercial funnel regression guard passed.")
