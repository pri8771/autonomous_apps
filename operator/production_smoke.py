#!/usr/bin/env python3
"""Verify the configured CommerceLint production funnel and persist evidence."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runlog import metrics_snapshot, record_event, stable_event_id, workflow_run_url

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "business.json"
STATE_PATH = ROOT / "state" / "state.json"
RECEIPT_PATH = ROOT / "state" / "production_smoke.json"
INDEXNOW_KEY = "1d88808c1ec138f77fe50484f83e6de7"
STABLE_ACTION_REF = "pri8771/autonomous_apps@v1"
IMMUTABLE_ACTION_SHA = "99c971299488437cf8a39819f5f6025b722c12eb"
ANALYTICS_MEASUREMENT_ID = "G-MC3PB0Q7EX"
FORBIDDEN_ANALYTICS_MARKERS = (
    "hs-scripts.com",
    "google-analytics.com",
    "sendBeacon(",
    "XMLHttpRequest(",
    "storeUrl",
    "pageTitle",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", "pri8771/autonomous_apps")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    return f"{server}/{repository}/actions/runs/{run_id}"


def verify_once(brand: str, base: str) -> tuple[dict[str, Any], list[str]]:
    specifications = {
        "canonical": (base, (brand, "scanner.html")),
        "scanner": (base + "scanner.html", ("analyzeMarkup", "Product", "Offer")),
        "developer_cli": (
            base + "cli.html",
            (
                "CommerceLint CLI",
                "GitHub Action",
                "Catch missing commerce fields",
                STABLE_ACTION_REF,
                IMMUTABLE_ACTION_SHA,
            ),
        ),
        "status": (base + "status.json", ('"status"', '"challenge_status"')),
        "analytics": (
            base + "assets/analytics.js",
            (
                ANALYTICS_MEASUREMENT_ID,
                "commercelint:analyticsConsent:v1",
                'readConsent() !== "granted"',
                "window.commerceLintTrack = track",
                "send_page_view: false",
            ),
        ),
        "offer": (base + "founding-audit.html", ("$49", "Request")),
        "indexnow_key": (base + INDEXNOW_KEY + ".txt", (INDEXNOW_KEY,)),
    }
    evidence: dict[str, Any] = {}
    failures: list[str] = []
    for name, (url, markers) in specifications.items():
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "CommerceLint-Production-Smoke/1.0"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(131072).decode("utf-8", errors="replace")
                latency_ms = int((time.monotonic() - started) * 1000)
                missing = [marker for marker in markers if marker not in body]
                forbidden = [
                    marker
                    for marker in FORBIDDEN_ANALYTICS_MARKERS
                    if name == "analytics" and marker in body
                ]
                ok = response.status == 200 and not missing and not forbidden
                detail = f"HTTP {response.status}"
                if missing:
                    detail += f"; missing markers: {', '.join(missing)}"
                if forbidden:
                    detail += f"; prohibited analytics markers: {', '.join(forbidden)}"
        except Exception as exc:  # network and parsing failures are evidence
            latency_ms = int((time.monotonic() - started) * 1000)
            ok = False
            detail = f"{type(exc).__name__}: {exc}"
        evidence[name] = {
            "url": url,
            "ok": ok,
            "detail": detail,
            "latency_ms": latency_ms,
        }
        if not ok:
            failures.append(f"{name}: {detail}")
    return evidence, failures


def main() -> int:
    started_at = now_iso()
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{started_at}"
    config = load_json(CONFIG_PATH)
    brand = str(config["business"]["name"])
    base = str(config["site"]["canonical_url"]).rstrip("/") + "/"
    state = load_json(STATE_PATH)
    metrics_before = metrics_snapshot(state)

    evidence: dict[str, Any] = {}
    failures: list[str] = []
    failures_retries: list[str] = []
    for attempt in range(1, 4):
        evidence, failures = verify_once(brand, base)
        if not failures:
            break
        failures_retries.append(f"Production verification attempt {attempt} failed: {'; '.join(failures)}")
        if attempt < 3:
            time.sleep(15)

    verified_at = now_iso()
    status = "healthy" if not failures else "degraded"
    receipt = {
        "schema_version": 1,
        "brand": brand,
        "production_base": base,
        "verified_at_utc": verified_at,
        "status": status,
        "workflow_run": run_url(),
        "stable_action_ref": STABLE_ACTION_REF,
        "immutable_action_sha": IMMUTABLE_ACTION_SHA,
        "privacy_assertion": (
            "Production loads owner-controlled GA4 only after explicit consent; "
            "CommerceLint events exclude scanned content, email, and form text."
        ),
        "checks": evidence,
        "failures": failures,
    }
    write_json(RECEIPT_PATH, receipt)

    state["production_smoke"] = {
        "last_verified_at_utc": verified_at,
        "status": status,
        "brand": brand,
        "production_base": base,
        "required_checks": list(evidence),
        "stable_action_ref": STABLE_ACTION_REF,
        "immutable_action_sha": IMMUTABLE_ACTION_SHA,
        "failures": failures,
    }
    for task in state.get("tasks", []):
        if task.get("id") == "enable-github-pages" and not failures:
            task["title"] = "Activate canonical production hosting"
            task["status"] = "done"
            task["success_condition"] = (
                "Configured canonical site and required funnel surfaces pass production smoke checks"
            )
            task["completed_at_utc"] = verified_at
            task["evidence"] = f"All {len(evidence)} production checks passed."
    write_json(STATE_PATH, state)

    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    record_event({
        "event_id": stable_event_id("production_smoke", run_id),
        "run_id": run_id,
        "workflow": "production_smoke",
        "status": "success" if not failures else "failed",
        "started_at_utc": started_at,
        "ended_at_utc": now_iso(),
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "task_selected": {"id": "verify-production", "title": "Verify the public CommerceLint funnel", "type": "monitoring"},
        "decision_summary": "The independent hourly smoke monitor verifies production availability, required funnel markers, the published CLI reference, analytics privacy invariants, and the IndexNow ownership key.",
        "evidence_consulted": [
            "config/business.json canonical production URL",
            *[f"{name}: {item.get('url')} — {item.get('detail')}" for name, item in evidence.items()],
        ],
        "action_taken": {
            "summary": f"Checked {len(evidence)} production surfaces with up to three bounded attempts.",
            "details": [f"Persisted the latest receipt to {RECEIPT_PATH.relative_to(ROOT)} and updated state/state.json."],
        },
        "verification": {
            "status": "passed" if not failures else "failed",
            "summary": f"{sum(bool(item.get('ok')) for item in evidence.values())} of {len(evidence)} required production checks passed.",
            "checks": [
                {"name": name, "ok": bool(item.get("ok")), "detail": str(item.get("detail", "")), "latency_ms": item.get("latency_ms")}
                for name, item in evidence.items()
            ],
        },
        "metrics_before": metrics_before,
        "metrics_after": metrics_snapshot(state),
        "blockers": failures,
        "failures_retries": failures_retries,
        "lessons": ([] if failures else ["Independent production verification passed without relying on operator self-reporting."]),
        "next_action": (
            "Open or refresh the production incident and retry on the next scheduled monitor run."
            if failures
            else "Continue hourly monitoring and let the deployment-receipt sync reconcile the latest production release."
        ),
        "links": [workflow_run_url() or "", base],
        "commit_hashes": [source_sha] if source_sha else [],
        "source": {"system": "production_smoke_runtime", "references": ["state/production_smoke.json", "state/state.json"]},
    })

    if failures:
        print("Production smoke failed: " + "; ".join(failures))
        return 1
    print(f"Production smoke passed: {len(evidence)} checks at {verified_at}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
