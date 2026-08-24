#!/usr/bin/env python3
"""Install explicit-opt-in, data-minimized GA4 instrumentation for CommerceLint.

This migration is idempotent. It updates current public pages, the scanner,
privacy disclosures, durable operating state, and the page generator used by
future autonomous content releases.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ANALYTICS = DOCS / "assets" / "analytics.js"
MEASUREMENT_ID = "G-3TY7EMFMWM"
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not locate {label}")
    return text.replace(old, new, 1)


def install_analytics_runtime() -> None:
    if not ANALYTICS.is_file():
        raise RuntimeError("docs/assets/analytics.js is missing")
    text = ANALYTICS.read_text(encoding="utf-8")
    required = (
        MEASUREMENT_ID,
        "commercelint:analyticsConsent:v1",
        "window.commerceLintTrack = track",
        "send_page_view: false",
        "scanned URLs",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError("analytics runtime is incomplete: " + ", ".join(missing))

    old = '''    writeConsent(value);
    removeConsentBanner();
    if (value === "granted") initializeAnalytics();'''
    new = '''    writeConsent(value);
    removeConsentBanner();
    if (value === "granted") initializeAnalytics();
    else if (analyticsInitialized) {
      window.gtag("consent", "update", {
        analytics_storage: "denied",
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied",
      });
    }'''
    text = replace_once(text, old, new, "analytics consent-withdrawal hook")
    ANALYTICS.write_text(text, encoding="utf-8")


def install_page_loaders() -> None:
    pattern = re.compile(
        r"\s*<script\b[^>]*\bsrc=[\"'][^\"']*assets/analytics\.js[\"'][^>]*>\s*</script>",
        re.IGNORECASE,
    )
    for path in sorted(DOCS.rglob("*.html")):
        text = pattern.sub("", path.read_text(encoding="utf-8"))
        relative = os.path.relpath(ANALYTICS, path.parent).replace(os.sep, "/")
        tag = f'  <script defer src="{relative}"></script>\n'
        if "</head>" not in text:
            raise RuntimeError(f"{path.relative_to(ROOT)} has no closing head tag")
        text = text.replace("</head>", tag + "</head>", 1)
        path.write_text(text, encoding="utf-8")


def instrument_scanner() -> None:
    path = DOCS / "scanner.html"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "  async function runScan() {\n    scannerCard.classList.add('loading');",
        "  async function runScan() {\n    window.commerceLintTrack?.('scanner_start', { scan_mode: mode });\n    scannerCard.classList.add('loading');",
        "scanner-start event",
    )

    text = replace_once(
        text,
        "      renderReport(analyzeMarkup(markup, source));\n      message.textContent = 'Analysis complete.';",
        """      const report = analyzeMarkup(markup, source);
      renderReport(report);
      const scoreBand = report.score >= 85 ? '85_100' : report.score >= 65 ? '65_84' : report.score >= 40 ? '40_64' : '0_39';
      const resultBand = report.score >= 85 ? 'strong' : report.score >= 65 ? 'repairable' : 'material_gaps';
      window.commerceLintTrack?.('scanner_complete', {
        scan_mode: mode,
        score_band: scoreBand,
        result_band: resultBand,
        missing_count: report.counts.fail,
        warning_count: report.counts.warning,
        pass_count: report.counts.pass
      });
      message.textContent = 'Analysis complete.';""",
        "scanner-completion event",
    )

    text = replace_once(
        text,
        """    } catch (error) {
      message.textContent = `${error.message} Try “Paste HTML” for a reliable local scan.`;""",
        """    } catch (error) {
      const errorText = String(error && error.message || '');
      const errorCategory = /Paste at least|Enter a public product URL/.test(errorText)
        ? 'input_validation'
        : /Retrieval|HTTP|retrieved page|AbortError|fetch/i.test(errorText)
          ? 'url_retrieval'
          : 'analysis';
      window.commerceLintTrack?.('scanner_error', { scan_mode: mode, error_category: errorCategory });
      message.textContent = `${error.message} Try “Paste HTML” for a reliable local scan.`;""",
        "scanner-error event",
    )

    text = replace_once(
        text,
        """  $('downloadButton').addEventListener('click', () => {
    if (!latestReport) return;""",
        """  $('downloadButton').addEventListener('click', () => {
    if (!latestReport) return;
    window.commerceLintTrack?.('evidence_download', { download_kind: 'scanner_json' });""",
        "evidence-download event",
    )

    text = replace_once(
        text,
        """  $('loadExample').addEventListener('click', () => {
    setMode('paste');""",
        """  $('loadExample').addEventListener('click', () => {
    window.commerceLintTrack?.('example_loaded', { source_surface: 'scanner' });
    setMode('paste');""",
        "example-loaded event",
    )

    path.write_text(text, encoding="utf-8")


def update_privacy() -> None:
    path = DOCS / "privacy.html"
    text = path.read_text(encoding="utf-8")
    section = '''<section><h2>Optional analytics</h2>
      <p>CommerceLint loads Google Analytics 4 only after you select <strong>Allow analytics</strong>. Before that choice, no Google Analytics script is requested and no analytics event is sent.</p>
      <p>When enabled, CommerceLint sends the sanitized page path without query strings, broad scanner outcome bands and counts, offer or CLI interest clicks, evidence-download events, and lead-start events. It does <strong>not</strong> send pasted HTML, scanned product URLs, titles from scanned stores, scan evidence, email addresses, or form contents.</p>
      <p>CommerceLint events use the <code>cl_</code> prefix and are separated by the <code>priyanshchordia.com</code> hostname in an owner-controlled Google Analytics account. Advertising storage, Google signals, ad personalization, and ad-user-data consent remain disabled.</p>
      <p>Your preference is stored in this browser. Global Privacy Control or Do Not Track disables analytics. You may change the preference below at any time.</p>
      <div class="button-row"><button type="button" class="button" data-cl-consent="granted">Allow analytics</button><button type="button" class="button secondary" data-cl-consent="denied">Decline analytics</button></div>
      <p class="field-help">Google processes consented analytics data under its own privacy terms. CommerceLint uses the data to measure page paths, scanner completion, offer interest, and acquisition sources.</p></section>'''
    text, count = re.subn(
        r"<section><h2>(?:Analytics|Optional analytics)</h2>.*?</section>",
        section,
        text,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("privacy analytics section was not found")
    text = text.replace("Last updated August 23, 2026.", "Last updated August 24, 2026.")
    path.write_text(text, encoding="utf-8")


def update_config() -> None:
    path = ROOT / "config" / "business.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["site"].update(
        {
            "analytics_provider": "google_analytics_4",
            "analytics_measurement_id": MEASUREMENT_ID,
            "analytics_mode": "explicit_opt_in",
            "analytics_event_namespace": "cl_",
            "analytics_hostname_dimension": "priyanshchordia.com",
            "analytics_data_minimization": [
                "strip query strings from page_location",
                "never send pasted HTML or scan evidence",
                "never send scanned URLs or scanned page titles",
                "never send email addresses or form contents",
                "disable advertising storage, Google signals, ad personalization, and ad user data",
            ],
        }
    )
    value["site"].pop("analytics_exclusion_reason", None)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def update_generator() -> None:
    path = ROOT / "operator" / "main.py"
    text = path.read_text(encoding="utf-8")
    analytics_asset = '        DOCS / "assets" / "analytics.js",\n'
    privacy_asset = '        DOCS / "privacy.html",\n'
    if analytics_asset not in text:
        if privacy_asset not in text:
            raise RuntimeError("operator local-asset insertion point is missing")
        text = text.replace(privacy_asset, privacy_asset + analytics_asset, 1)

    loader = '  <script defer src="../assets/analytics.js"></script>\n'
    if loader not in text:
        anchor = '  <link rel="stylesheet" href="../assets/site.css">\n</head>'
        if anchor not in text:
            raise RuntimeError("operator page-template insertion point is missing")
        text = text.replace(
            anchor,
            '  <link rel="stylesheet" href="../assets/site.css">\n' + loader + "</head>",
            1,
        )
    path.write_text(text, encoding="utf-8")


def update_state() -> None:
    path = ROOT / "state" / "state.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    for task in value.get("tasks", []):
        if task.get("id") == "instrument-first-party-analytics":
            task.update(
                {
                    "title": "Deploy consent-gated CommerceLint funnel analytics",
                    "type": "analytics_deployment",
                    "status": "running",
                    "owner_required": False,
                    "attempts": max(1, int(task.get("attempts", 0)) + 1),
                    "max_attempts": max(3, int(task.get("max_attempts", 1))),
                    "success_condition": "Production loads GA4 only after explicit consent and records sanitized page, scanner, offer, CLI, download, and lead-start events",
                    "evidence": f"Source instrumentation prepared with {MEASUREMENT_ID}; production verification is pending.",
                    "last_attempt_at_utc": NOW,
                }
            )
            break
    else:
        value.setdefault("tasks", []).append(
            {
                "id": "instrument-first-party-analytics",
                "title": "Deploy consent-gated CommerceLint funnel analytics",
                "type": "analytics_deployment",
                "status": "running",
                "priority": 94,
                "impact": 10,
                "urgency": 10,
                "confidence": 0.9,
                "effort": 2,
                "attempts": 1,
                "max_attempts": 3,
                "owner_required": False,
                "success_condition": "Production loads GA4 only after explicit consent and records sanitized funnel events",
                "evidence": f"Source instrumentation prepared with {MEASUREMENT_ID}; production verification is pending.",
                "last_attempt_at_utc": NOW,
            }
        )

    lesson = "Consent-gated GA4 instrumentation was added with strict event allowlisting and query-string removal."
    if not any(item.get("lesson") == lesson for item in value.get("lessons", [])):
        value.setdefault("lessons", []).append(
            {
                "at_utc": NOW,
                "category": "measurement",
                "lesson": lesson,
                "evidence": f"Measurement ID {MEASUREMENT_ID}; source pages, privacy policy, scanner events, and future guide generator updated.",
            }
        )
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    summary_path = ROOT / "STATE.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["last_verified_action"] = "Prepared explicit-opt-in GA4 instrumentation with sanitized CommerceLint funnel events and no scanned-content collection."
        summary["next_action"] = "Deploy and independently verify consent gating, then use hostname-filtered analytics to prioritize acquisition and conversion work."
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def append_decision_records() -> None:
    decisions = ROOT / "DECISIONS.md"
    heading = "## 2026-08-24 — Consent-gated funnel analytics"
    if decisions.exists() and heading not in decisions.read_text(encoding="utf-8"):
        with decisions.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n{heading}\n"
                f"**Decision:** Use owner-controlled GA4 measurement ID `{MEASUREMENT_ID}` for CommerceLint with explicit opt-in consent, hostname separation, a `cl_` event namespace, and a strict non-content event allowlist.\n\n"
                "**Data minimization:** Strip query strings; never send pasted HTML, scanned URLs, scanned page titles, evidence, email addresses, or form contents. Keep advertising storage, Google signals, ad personalization, and ad-user-data consent disabled.\n\n"
                "**Reason:** The business needs acquisition and funnel evidence, while scanned commerce content can be sensitive and is unnecessary for aggregate decisions.\n"
            )

    changelog = ROOT / "CHANGELOG.md"
    change_heading = "## 2026-08-24 — Consent-gated analytics"
    if changelog.exists() and change_heading not in changelog.read_text(encoding="utf-8"):
        with changelog.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n{change_heading}\n"
                f"- Added explicit-opt-in Google Analytics 4 using `{MEASUREMENT_ID}`.\n"
                "- Added sanitized page, scanner, offer, CLI, download, and lead-start events.\n"
                "- Added consent withdrawal and Global Privacy Control / Do Not Track handling.\n"
                "- Updated every public HTML page, scanner instrumentation, privacy disclosure, durable state, and future guide generation.\n"
            )


def validate() -> None:
    failures: list[str] = []
    loader_pattern = re.compile(r'<script\b[^>]*src=["\'][^"\']*assets/analytics\.js["\']', re.I)
    for path in sorted(DOCS.rglob("*.html")):
        count = len(loader_pattern.findall(path.read_text(encoding="utf-8")))
        if count != 1:
            failures.append(f"{path.relative_to(ROOT)} has {count} analytics loaders")

    analytics = ANALYTICS.read_text(encoding="utf-8")
    for forbidden in ("storeUrl", "pageTitle"):
        if forbidden in analytics:
            failures.append(f"analytics.js contains prohibited scanner parameter name {forbidden}")

    scanner = (DOCS / "scanner.html").read_text(encoding="utf-8")
    for marker in (
        "commerceLintTrack?.('scanner_start'",
        "commerceLintTrack?.('scanner_complete'",
        "commerceLintTrack?.('scanner_error'",
        "commerceLintTrack?.('evidence_download'",
    ):
        if marker not in scanner:
            failures.append(f"scanner is missing {marker}")

    privacy = (DOCS / "privacy.html").read_text(encoding="utf-8")
    for marker in ("only after you select", "does <strong>not</strong> send pasted HTML", "Global Privacy Control"):
        if marker not in privacy:
            failures.append(f"privacy disclosure is missing {marker}")

    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    install_analytics_runtime()
    install_page_loaders()
    instrument_scanner()
    update_privacy()
    update_config()
    update_generator()
    update_state()
    append_decision_records()
    validate()
    print(f"Installed consent-gated CommerceLint analytics using {MEASUREMENT_ID}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
