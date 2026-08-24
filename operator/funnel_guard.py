#!/usr/bin/env python3
"""Regression guard for MachineCart's maintained commercial funnel."""

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
            "audit-request-composed",
        ),
        DOCS / "agency.html": (
            "downloads/machinecart-audit-backlog.csv",
            "downloads/machinecart-audit-report-template.md",
        ),
        DOCS / "sample-audit.html": (
            "Sample MachineCart audit",
            "founding-audit.html",
        ),
        DOCS / "methodology.html": (
            "How MachineCart audits a store",
            "founding-audit.html",
        ),
        DOCS / "service.json": (
            '"paid_service"',
            '"price": 49',
        ),
        DOCS / "llms.txt": (
            "MachineCart",
            "Founding audit",
        ),
        DOCS / "downloads" / "machinecart-audit-backlog.csv": (
            "finding_id",
            "verification_procedure",
        ),
        DOCS / "downloads" / "machinecart-audit-report-template.md": (
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
    print("MachineCart commercial funnel regression guard passed.")
