#!/usr/bin/env python3
"""Migrate the growth planner away from regenerating maintained sales pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "operator" / "growth_planner.py"


def main() -> int:
    text = PLANNER.read_text(encoding="utf-8")
    changed = False

    legacy_call = "    write_sales_pages()\n"
    safe_call = "    from funnel_guard import validate_sales_pages\n    validate_sales_pages()\n"
    if safe_call not in text:
        if text.count(legacy_call) != 1:
            raise RuntimeError(
                f"Expected one legacy sales-page rewrite call; found {text.count(legacy_call)}"
            )
        text = text.replace(legacy_call, safe_call, 1)
        changed = True

    old_dependencies = """    growth[\"next_external_dependencies\"] = [
        \"Canonical production hosting or GitHub Pages activation\",
        \"Owner-verified payment checkout\",
        \"One authenticated social publishing channel\",
        \"First-party analytics endpoint\",
    ]"""
    new_dependencies = """    growth[\"next_external_dependencies\"] = [
        \"Owner-verified payment checkout\",
        \"One authenticated social publishing channel\",
        \"Analytics read access for automated optimization\",
    ]"""
    if new_dependencies not in text and old_dependencies in text:
        text = text.replace(old_dependencies, new_dependencies, 1)
        changed = True

    if changed:
        PLANNER.write_text(text, encoding="utf-8")

    current = PLANNER.read_text(encoding="utf-8")
    if legacy_call in current:
        raise RuntimeError("Growth planner still calls write_sales_pages")
    if safe_call not in current:
        raise RuntimeError("Growth planner does not validate maintained sales pages")

    print(f"Growth planner migration passed; changed={changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
