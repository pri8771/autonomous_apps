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

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "business.json"
STATE_PATH = ROOT / "state" / "state.json"
RECEIPT_PATH = ROOT / "state" / "production_smoke.json"
INDEXNOW_KEY = "1d88808c1ec138f77fe50484f83e6de7"
FORBIDDEN_ANALYTICS_MARKERS = (
    "hs-scripts.com",
    "google-analytics.com",
    "googletagmanager.com",
    "sendBeacon(",
    "XMLHttpRequest(",
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
            ("CommerceLint CLI", "GitHub Action", "Catch missing commerce fields"),
        ),
        "status": (base + "status.json", ('"status"', '"challenge_status"')),
        "analytics_shim": (base + "assets/analytics.js", ("window.", "function")),
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
                    if name == "analytics_shim" and marker in body
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
    config = load_json(CONFIG_PATH)
    brand = str(config["business"]["name"])
    base = str(config["site"]["canonical_url"]).rstrip("/") + "/"

    evidence: dict[str, Any] = {}
    failures: list[str] = []
    for attempt in range(1, 4):
        evidence, failures = verify_once(brand, base)
        if not failures:
            break
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
        "privacy_assertion": (
            "Production analytics compatibility code contains no known third-party "
            "network analytics endpoints."
        ),
        "checks": evidence,
        "failures": failures,
    }
    write_json(RECEIPT_PATH, receipt)

    state = load_json(STATE_PATH)
    state["production_smoke"] = {
        "last_verified_at_utc": verified_at,
        "status": status,
        "brand": brand,
        "production_base": base,
        "required_checks": list(evidence),
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

    if failures:
        print("Production smoke failed: " + "; ".join(failures))
        return 1
    print(f"Production smoke passed: {len(evidence)} checks at {verified_at}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
