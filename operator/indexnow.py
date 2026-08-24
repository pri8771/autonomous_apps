#!/usr/bin/env python3
"""Submit changed MachineCart URLs to IndexNow with durable evidence.

No secret is used: IndexNow ownership keys are intentionally public and are
verified by fetching the scoped key file from the canonical site.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITEMAP_PATH = DOCS / "sitemap.xml"
CONTROL_PATH = ROOT / "state" / "CONTROL.json"
STATE_PATH = ROOT / "state" / "indexnow_state.json"
CANONICAL_BASE = "https://priyanshchordia.com/machinecart/"
HOST = "priyanshchordia.com"
ENDPOINT = "https://api.indexnow.org/indexnow"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_key() -> tuple[str, str]:
    candidates: list[tuple[Path, str]] = []
    for path in DOCS.glob("*.txt"):
        value = path.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[A-Za-z0-9-]{8,128}", value) and path.stem == value:
            candidates.append((path, value))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one scoped IndexNow key file; found {len(candidates)}")
    path, key = candidates[0]
    return key, CANONICAL_BASE + path.name


def sitemap_urls() -> list[str]:
    root = ET.fromstring(SITEMAP_PATH.read_text(encoding="utf-8"))
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text.strip() for node in root.findall("s:url/s:loc", namespace) if node.text]
    return normalize_urls(urls)


def normalize_urls(urls: list[str]) -> list[str]:
    allowed_prefix = CANONICAL_BASE
    unique = sorted({url for url in urls if url.startswith(allowed_prefix)})
    if not unique:
        raise RuntimeError("No canonical MachineCart URLs were selected")
    if len(unique) > 10_000:
        raise RuntimeError("IndexNow batch exceeds 10,000 URLs")
    return unique


def urls_for_paths(paths: list[str]) -> list[str]:
    selected: list[str] = []
    for raw in paths:
        path = raw.strip().replace("\\", "/")
        if not path.startswith("docs/"):
            continue
        relative = path.removeprefix("docs/")
        if relative in {"sitemap.xml"} or re.fullmatch(r"[A-Za-z0-9-]{8,128}\.txt", relative):
            return sitemap_urls()
        if not relative.endswith(".html"):
            continue
        selected.append(CANONICAL_BASE if relative == "index.html" else CANONICAL_BASE + relative)
    return normalize_urls(selected) if selected else sitemap_urls()


def fingerprint(urls: list[str]) -> str:
    commit = os.environ.get("GITHUB_SHA", "")
    material = commit + "\n" + "\n".join(urls)
    if not commit:
        for url in urls:
            relative = url.removeprefix(CANONICAL_BASE) or "index.html"
            path = DOCS / relative
            if path.exists() and path.is_file():
                material += "\n" + hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def submit(payload: dict[str, Any]) -> tuple[int, str, int]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    delays = [0, 5, 15, 30]
    last_status = 0
    last_detail = ""
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        request = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "MachineCart-IndexNow/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                last_status = int(response.status)
                last_detail = response.read(1000).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_status = int(exc.code)
            last_detail = exc.read(1000).decode("utf-8", errors="replace")
            retry_after = exc.headers.get("Retry-After")
            if retry_after and retry_after.isdigit() and attempt < len(delays):
                time.sleep(min(int(retry_after), 60))
        except Exception as exc:  # network failures are evidence too
            last_status = 0
            last_detail = f"{type(exc).__name__}: {exc}"

        if last_status in {200, 202}:
            return last_status, last_detail, attempt
        if last_status in {400, 422}:
            break
    return last_status, last_detail, len(delays)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Changed repository paths")
    parser.add_argument("--all", action="store_true", help="Submit every URL in the sitemap")
    args = parser.parse_args()

    control = load_json(CONTROL_PATH, {"mode": "RUN"})
    mode = str(control.get("mode", "RUN")).upper()
    if mode in {"PAUSE", "STOP"}:
        print(f"IndexNow control mode is {mode}; no submission executed.")
        return 0

    urls = sitemap_urls() if args.all else urls_for_paths(args.paths)
    key, key_location = read_key()
    current_fingerprint = fingerprint(urls)
    state = load_json(STATE_PATH, {"schema_version": 1, "history": []})

    if state.get("last_successful_fingerprint") == current_fingerprint:
        print("This commit and URL set were already accepted by IndexNow.")
        return 0

    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }
    status, detail, attempts = submit(payload)
    accepted = status in {200, 202}
    record = {
        "at_utc": now_iso(),
        "accepted": accepted,
        "http_status": status,
        "attempts": attempts,
        "url_count": len(urls),
        "urls": urls,
        "key_location": key_location,
        "fingerprint": current_fingerprint,
        "response_excerpt": detail[:1000],
    }
    state["last_attempt"] = record
    if accepted:
        state["last_successful_fingerprint"] = current_fingerprint
        state["last_success_at_utc"] = record["at_utc"]
    state.setdefault("history", []).append(record)
    state["history"] = state["history"][-50:]
    write_json(STATE_PATH, state)
    print(json.dumps(record, indent=2))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
