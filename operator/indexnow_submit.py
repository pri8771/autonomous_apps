#!/usr/bin/env python3
"""Submit newly changed CommerceLint public pages through IndexNow.

The worker is intentionally bounded:
- only URLs under the canonical /commercelint/ path are eligible;
- routine hourly status files and non-page assets are excluded;
- the scoped public key file is verified before submission;
- retries use backoff and accepted responses are recorded as job evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from runlog import record_event, stable_event_id, workflow_run_url

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITEMAP = DOCS / "sitemap.xml"
RESULT_PATH = ROOT / "indexnow-result.json"

HOST = "priyanshchordia.com"
BASE_URL = "https://priyanshchordia.com/commercelint/"
KEY = "1d88808c1ec138f77fe50484f83e6de7"
KEY_LOCATION = f"{BASE_URL}{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
USER_AGENT = "CommerceLint-IndexNow/1.0 (+https://priyanshchordia.com/commercelint/)"

EXCLUDED_PATHS = {
    "docs/status.html",
    "docs/status.json",
    "docs/sitemap.xml",
    f"docs/{KEY}.txt",
}
ELIGIBLE_SUFFIXES = {".html", ".txt", ".json"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def normalize_doc_path(path_text: str) -> str | None:
    path_text = path_text.strip()
    if not path_text.startswith("docs/") or path_text in EXCLUDED_PATHS:
        return None
    relative = Path(path_text).relative_to("docs")
    if any(part in {"assets", "downloads"} for part in relative.parts):
        return None
    if relative.suffix.lower() not in ELIGIBLE_SUFFIXES:
        return None
    if relative.as_posix() == "index.html":
        return BASE_URL
    if relative.name == "index.html":
        return f"{BASE_URL}{relative.parent.as_posix().rstrip('/')}/"
    return f"{BASE_URL}{relative.as_posix()}"


def paths_from_diff(before: str, after: str) -> list[str]:
    if not before or set(before) == {"0"}:
        return []
    output = run_git("diff", "--name-status", before, after, "--", "docs")
    urls: set[str] = set()
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t")
        status = fields[0]
        candidate_paths: list[str]
        if status.startswith("R") or status.startswith("C"):
            candidate_paths = fields[1:3]
        else:
            candidate_paths = fields[1:2]
        for candidate in candidate_paths:
            url = normalize_doc_path(candidate)
            if url:
                urls.add(url)
    return sorted(urls)


def urls_from_sitemap() -> list[str]:
    if not SITEMAP.exists():
        raise FileNotFoundError(f"Missing sitemap: {SITEMAP}")
    root = ET.parse(SITEMAP).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {
        (node.text or "").strip()
        for node in root.findall("sm:url/sm:loc", namespace)
        if (node.text or "").strip().startswith(BASE_URL)
    }
    return sorted(urls)


def fetch_text(url: str, timeout: int = 20) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*;q=0.8"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read(4096).decode("utf-8", errors="replace")


def verify_key() -> dict[str, object]:
    attempts: list[dict[str, object]] = []
    for delay in (0, 15, 45):
        if delay:
            time.sleep(delay)
        try:
            status, body = fetch_text(KEY_LOCATION)
            ok = 200 <= status < 300 and body.strip() == KEY
            attempts.append({"status": status, "body_matches": body.strip() == KEY})
            if ok:
                return {"ok": True, "attempts": attempts}
        except Exception as exc:  # network evidence is recorded below
            attempts.append({"error": f"{type(exc).__name__}: {exc}"})
    return {"ok": False, "attempts": attempts}


def submit(urls: Iterable[str]) -> dict[str, object]:
    url_list = sorted(set(urls))
    if not url_list:
        return {"ok": True, "skipped": True, "reason": "No eligible public page changed.", "url_count": 0}
    if len(url_list) > 10_000:
        raise ValueError("IndexNow submission exceeds the 10,000 URL protocol limit.")
    invalid = [url for url in url_list if not url.startswith(BASE_URL)]
    if invalid:
        raise ValueError(f"Refusing URLs outside the scoped canonical path: {invalid[:3]}")

    key_check = verify_key()
    if not key_check["ok"]:
        return {
            "ok": False,
            "stage": "key_verification",
            "key_location": KEY_LOCATION,
            "key_check": key_check,
            "url_count": len(url_list),
        }

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list,
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    attempts: list[dict[str, object]] = []

    for delay in (0, 15, 45):
        if delay:
            time.sleep(delay)
        request = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json,text/plain,*/*",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = int(response.status)
                response_body = response.read(4096).decode("utf-8", errors="replace")
            accepted = status in {200, 202}
            attempts.append({"status": status, "body": response_body[:1000]})
            if accepted:
                return {
                    "ok": True,
                    "accepted": True,
                    "status": status,
                    "url_count": len(url_list),
                    "urls": url_list,
                    "key_location": KEY_LOCATION,
                    "attempts": attempts,
                }
            if status not in {429, 500, 502, 503, 504}:
                break
        except urllib.error.HTTPError as exc:
            response_body = exc.read(4096).decode("utf-8", errors="replace")
            attempts.append({"status": int(exc.code), "body": response_body[:1000]})
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except Exception as exc:
            attempts.append({"error": f"{type(exc).__name__}: {exc}"})

    return {
        "ok": False,
        "stage": "submission",
        "url_count": len(url_list),
        "urls": url_list,
        "key_location": KEY_LOCATION,
        "attempts": attempts,
    }


def main() -> int:
    started_at = now_iso()
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{started_at}"
    parser = argparse.ArgumentParser(description="Submit changed CommerceLint pages through IndexNow.")
    parser.add_argument("--before", default="", help="Git commit before the change.")
    parser.add_argument("--after", default="HEAD", help="Git commit after the change.")
    parser.add_argument("--full", action="store_true", help="Submit every URL currently listed in the sitemap.")
    parser.add_argument(
        "--all-if-empty",
        action="store_true",
        help="Use the sitemap when no eligible page can be derived from the commit diff.",
    )
    args = parser.parse_args()

    try:
        if args.full:
            urls = urls_from_sitemap()
            mode = "full_sitemap"
        else:
            urls = paths_from_diff(args.before, args.after)
            mode = "changed_pages"
            if not urls and args.all_if_empty:
                urls = urls_from_sitemap()
                mode = "sitemap_fallback"

        submission = submit(urls)
    except Exception as exc:
        mode = "full_sitemap" if args.full else "changed_pages"
        urls = []
        submission = {
            "ok": False,
            "stage": "unhandled_exception",
            "error": f"{type(exc).__name__}: {exc}",
            "url_count": 0,
            "attempts": [],
        }

    result = {
        "schema_version": 1,
        "generated_at_utc": now_iso(),
        "mode": mode,
        "before": args.before or None,
        "after": args.after,
        **submission,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    attempts = result.get("attempts", []) if isinstance(result.get("attempts"), list) else []
    failures_retries = []
    for index, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            continue
        status = attempt.get("status")
        if attempt.get("error") or status not in {200, 202}:
            failures_retries.append(
                f"Attempt {index}: {attempt.get('error') or f'HTTP {status}'}"
            )
    if result.get("error"):
        failures_retries.append(str(result["error"]))
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    record_event({
        "event_id": stable_event_id("indexnow_notification", run_id),
        "run_id": run_id,
        "workflow": "indexnow_notification",
        "status": "success" if result.get("ok") else "failed",
        "started_at_utc": started_at,
        "ended_at_utc": result["generated_at_utc"],
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "task_selected": {"id": "notify-search-engines", "title": "Submit CommerceLint URLs to IndexNow", "type": "distribution"},
        "decision_summary": (
            "A manual full-sitemap submission was requested."
            if mode == "full_sitemap"
            else "No eligible changed URL was found, so the bounded sitemap fallback was selected."
            if mode == "sitemap_fallback"
            else "The workflow selected only eligible public CommerceLint pages changed by the triggering commit."
        ),
        "evidence_consulted": [
            f"Git comparison {args.before or 'not recorded'}..{args.after}",
            *[str(url) for url in result.get("urls", urls)],
            KEY_LOCATION,
        ],
        "action_taken": {
            "summary": (
                str(result.get("reason"))
                if result.get("skipped")
                else f"Submitted {result.get('url_count', 0)} URLs using mode {mode}."
            ),
            "details": [],
        },
        "verification": {
            "status": "passed" if result.get("ok") else "failed",
            "summary": (
                "No eligible page required submission."
                if result.get("skipped")
                else f"IndexNow accepted the submission with HTTP {result.get('status')}."
                if result.get("accepted")
                else f"IndexNow stage {result.get('stage', 'submission')} did not complete successfully."
            ),
            "checks": [
                {"name": "indexnow_attempt", "ok": attempt.get("status") in {200, 202}, "detail": str(attempt.get("error") or f"HTTP {attempt.get('status')}")}
                for attempt in attempts
                if isinstance(attempt, dict)
            ],
        },
        "metrics_before": {},
        "metrics_after": {"submitted_url_count": result.get("url_count", 0), "attempt_count": len(attempts)},
        "blockers": ([] if result.get("ok") else [f"IndexNow stage {result.get('stage', 'submission')} failed."]),
        "failures_retries": failures_retries,
        "lessons": [],
        "next_action": (
            "Wait for a changed release before notifying search engines again."
            if result.get("ok")
            else "Review the retained artifact and retry after the next eligible changed release."
        ),
        "links": [workflow_run_url() or "", *[str(url) for url in result.get("urls", urls)]],
        "commit_hashes": [value for value in (args.before, args.after, source_sha) if value and set(value) != {"0"}],
        "source": {"system": "indexnow_runtime", "references": ["indexnow-result.json"]},
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
