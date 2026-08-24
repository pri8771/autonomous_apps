#!/usr/bin/env python3
"""Idempotently connect scanner results to the structured audit request funnel."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "docs" / "scanner.html"
AUDIT = ROOT / "docs" / "founding-audit.html"


def migrate_scanner() -> bool:
    text = SCANNER.read_text(encoding="utf-8")
    destination_marker = "founding-audit.html?${auditParams.toString()}#request"
    if destination_marker in text:
        return False

    start_marker = "    const subject = encodeURIComponent(`MachineCart deep audit"
    end_marker = "    $('auditButton').href = `mailto:pchordia@unsubscriber.me?subject=${subject}&body=${body}`;"
    start = text.find(start_marker)
    end_start = text.find(end_marker, start)
    if start < 0 or end_start < 0:
        raise RuntimeError("Could not locate the legacy scanner audit handoff")
    end = end_start + len(end_marker)

    replacement = """    const auditParams = new URLSearchParams({
      source: 'scanner',
      score: String(report.score),
      failed: String(report.counts.fail),
      warnings: String(report.counts.warning),
      pageTitle: report.page.title || 'Product page'
    });
    if (report.source.url) auditParams.set('storeUrl', report.source.url);
    const acquisition = new URLSearchParams(window.location.search);
    for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']) {
      const value = acquisition.get(key);
      if (value) auditParams.set(key, value);
    }
    $('auditButton').href = `founding-audit.html?${auditParams.toString()}#request`;"""

    SCANNER.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
    return True


def migrate_audit_form() -> bool:
    text = AUDIT.read_text(encoding="utf-8")
    changed = False

    if "const params = new URLSearchParams(window.location.search);" not in text:
        marker = """    const form = document.getElementById('auditRequestForm');
    const status = document.getElementById('requestStatus');
    form.addEventListener('submit', event => {"""
        replacement = """    const form = document.getElementById('auditRequestForm');
    const status = document.getElementById('requestStatus');
    const params = new URLSearchParams(window.location.search);
    const scannedUrl = params.get('storeUrl');
    if (scannedUrl) document.getElementById('storeUrl').value = scannedUrl;
    const scanContext = [
      params.get('score') ? `Scanner score: ${params.get('score')}` : '',
      params.get('failed') ? `Failed checks: ${params.get('failed')}` : '',
      params.get('warnings') ? `Warnings: ${params.get('warnings')}` : '',
      params.get('pageTitle') ? `Scanned page: ${params.get('pageTitle')}` : ''
    ].filter(Boolean).join('\\n');
    if (scanContext) document.getElementById('details').value = scanContext;

    form.addEventListener('submit', event => {"""
        if marker not in text:
            raise RuntimeError("Could not locate the audit form initialization")
        text = text.replace(marker, replacement, 1)
        changed = True

    acquisition_marker = "`Acquisition source: ${params.get('source') || 'direct'}`,"
    if acquisition_marker not in text:
        marker = "        `Desired timing: ${data.get('urgency')}`,"
        addition = """
        `Acquisition source: ${params.get('source') || 'direct'}`,
        `UTM source: ${params.get('utm_source') || 'not supplied'}`,
        `UTM medium: ${params.get('utm_medium') || 'not supplied'}`,
        `UTM campaign: ${params.get('utm_campaign') || 'not supplied'}`,
        `Referrer: ${document.referrer || 'not supplied'}`,"""
        if marker not in text:
            raise RuntimeError("Could not locate the audit request timing field")
        text = text.replace(marker, marker + addition, 1)
        changed = True

    if changed:
        AUDIT.write_text(text, encoding="utf-8")
    return changed


def validate() -> None:
    scanner = SCANNER.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    required = {
        "scanner handoff": "founding-audit.html?${auditParams.toString()}#request" in scanner,
        "scanner context": "Scanner score:" in audit,
        "campaign attribution": "UTM campaign:" in audit,
        "structured form": "auditRequestForm" in audit,
    }
    failed = [name for name, ok in required.items() if not ok]
    if failed:
        raise RuntimeError(f"Conversion migration validation failed: {failed}")


def main() -> int:
    scanner_changed = migrate_scanner()
    audit_changed = migrate_audit_form()
    validate()
    print(
        "MachineCart conversion migration passed; "
        f"scanner_changed={scanner_changed}; audit_changed={audit_changed}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
