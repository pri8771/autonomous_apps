#!/usr/bin/env python3
"""Durable, privacy-safe CommerceLint autonomous run logging.

The canonical record is one JSON object per line under ``state/audit/events``.
Human-readable daily diaries, daily JSON snapshots, and indexes are rebuilt from
that stream after every append. Decision summaries are operational rationales;
this module never accepts or records hidden chain-of-thought.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "state" / "audit"
TIMEZONE_NAME = "America/New_York"
LOCAL_TIMEZONE = ZoneInfo(TIMEZONE_NAME)
SCHEMA_VERSION = 1

SECRET_KEY_RE = re.compile(
    r"(?:authorization|cookie|credential|password|passwd|secret|token|api[_-]?key|private[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
TOKEN_PATTERNS = (
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
)
SECRET_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "code",
    "credential",
    "key",
    "password",
    "secret",
    "signature",
    "token",
}
REDACTED = "[REDACTED]"
UNKNOWN = "Not recorded in source evidence."


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def local_timestamp(value: str | None) -> str | None:
    parsed = parse_timestamp(value)
    return parsed.astimezone(LOCAL_TIMEZONE).isoformat() if parsed else None


def workflow_run_url() -> str | None:
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    if not run_id:
        return None
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", "pri8771/autonomous_apps").strip("/")
    return f"{server}/{repository}/actions/runs/{run_id}"


def redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return value
    hostname = parsed.hostname or ""
    try:
        parsed_port = parsed.port
    except ValueError:
        return "[REDACTED_INVALID_URL]"
    port = f":{parsed_port}" if parsed_port else ""
    netloc = hostname + port
    query = [
        (key, REDACTED if key.lower() in SECRET_QUERY_KEYS else item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit((parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment))


def redact_string(value: str) -> tuple[str, bool]:
    original = value
    value = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    for pattern in TOKEN_PATTERNS:
        value = pattern.sub(REDACTED, value)
    if value.startswith(("http://", "https://")):
        value = redact_url(value)
    if len(value) > 8000:
        value = value[:8000] + "…[TRUNCATED]"
    return value, value != original


def redact(value: Any, key: str = "") -> tuple[Any, bool]:
    """Recursively redact secrets, credentials, emails, and sensitive URL query values."""
    if key and SECRET_KEY_RE.search(key):
        return REDACTED, True
    if isinstance(value, dict):
        changed = False
        clean: dict[str, Any] = {}
        for raw_key, item in value.items():
            item_key = str(raw_key)
            clean_value, item_changed = redact(item, item_key)
            clean[item_key] = clean_value
            changed = changed or item_changed
        return clean, changed
    if isinstance(value, list):
        changed = False
        clean_list = []
        for item in value:
            clean_item, item_changed = redact(item)
            clean_list.append(clean_item)
            changed = changed or item_changed
        return clean_list, changed
    if isinstance(value, tuple):
        return redact(list(value), key)
    if isinstance(value, str):
        return redact_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    return redact_string(str(value))


def compact_text(value: Any, default: str = UNKNOWN, limit: int = 1200) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [compact_text(item, default="") for item in items if compact_text(item, default="")]


def stable_event_id(*parts: str) -> str:
    readable = ":".join(re.sub(r"[^A-Za-z0-9_.-]+", "-", part).strip("-") for part in parts if part)
    if len(readable) <= 180:
        return readable
    digest = hashlib.sha256(readable.encode("utf-8")).hexdigest()[:16]
    return readable[:160] + ":" + digest


def metrics_snapshot(state: dict[str, Any] | None) -> dict[str, Any]:
    metrics = dict((state or {}).get("metrics", {}))
    return {str(key): metrics[key] for key in sorted(metrics)}


def normalize_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    now = iso_utc(utc_now())
    started_at = raw_event.get("started_at_utc") or raw_event.get("ended_at_utc") or now
    ended_at = raw_event.get("ended_at_utc") or started_at
    start = parse_timestamp(str(started_at))
    end = parse_timestamp(str(ended_at))
    if not start or not end:
        raise ValueError("Run-log timestamps must be ISO-8601 values.")
    if end < start:
        end = start

    workflow = compact_text(raw_event.get("workflow"), "unknown_workflow", 120)
    event_id = compact_text(
        raw_event.get("event_id"),
        stable_event_id(workflow, iso_utc(start), compact_text(raw_event.get("run_id"), "run")),
        220,
    )
    task = raw_event.get("task_selected")
    if not isinstance(task, dict):
        task = {"id": None, "title": compact_text(task, "No task recorded", 300)}
    task = {
        "id": compact_text(task.get("id"), default="", limit=160) or None,
        "title": compact_text(task.get("title"), "No task recorded", 400),
        "type": compact_text(task.get("type"), default="", limit=160) or None,
    }
    verification = raw_event.get("verification")
    if not isinstance(verification, dict):
        verification = {"status": "unknown", "summary": compact_text(verification)}
    action = raw_event.get("action_taken")
    if not isinstance(action, dict):
        action = {"summary": compact_text(action), "details": []}
    source = raw_event.get("source") if isinstance(raw_event.get("source"), dict) else {}

    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "run_id": compact_text(raw_event.get("run_id"), event_id, 220),
        "workflow": workflow,
        "status": compact_text(raw_event.get("status"), "unknown", 40).lower(),
        "started_at_utc": iso_utc(start),
        "ended_at_utc": iso_utc(end),
        "started_at_local": start.astimezone(LOCAL_TIMEZONE).isoformat(),
        "ended_at_local": end.astimezone(LOCAL_TIMEZONE).isoformat(),
        "timezone": TIMEZONE_NAME,
        "trigger": compact_text(raw_event.get("trigger"), UNKNOWN, 200),
        "task_selected": task,
        "decision_summary": compact_text(raw_event.get("decision_summary"), limit=1200),
        "evidence_consulted": string_list(raw_event.get("evidence_consulted")),
        "action_taken": {
            "summary": compact_text(action.get("summary")),
            "details": string_list(action.get("details")),
        },
        "verification": {
            "status": compact_text(verification.get("status"), "unknown", 60).lower(),
            "summary": compact_text(verification.get("summary")),
            "checks": verification.get("checks", []) if isinstance(verification.get("checks", []), list) else [],
        },
        "metrics_before": raw_event.get("metrics_before", {}) if isinstance(raw_event.get("metrics_before", {}), dict) else {},
        "metrics_after": raw_event.get("metrics_after", {}) if isinstance(raw_event.get("metrics_after", {}), dict) else {},
        "blockers": string_list(raw_event.get("blockers")),
        "failures_retries": string_list(raw_event.get("failures_retries")),
        "lessons": string_list(raw_event.get("lessons")),
        "next_action": compact_text(raw_event.get("next_action")),
        "links": string_list(raw_event.get("links")),
        "commit_hashes": string_list(raw_event.get("commit_hashes")),
        "backfilled": bool(raw_event.get("backfilled", False)),
        "backfill_notes": string_list(raw_event.get("backfill_notes")),
        "source": {
            "system": compact_text(source.get("system"), "runtime", 160),
            "references": string_list(source.get("references")),
        },
    }
    clean, changed = redact(event)
    clean["redaction_applied"] = changed
    return clean


def _events_path(root: Path, local_date: str) -> Path:
    return root / "state" / "audit" / "events" / f"{local_date}.jsonl"


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if isinstance(item, dict):
            events.append(item)
    return events


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _format_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (dict, list)):
        return "`" + json.dumps(value, ensure_ascii=False, sort_keys=True) + "`"
    return str(value).replace("|", "\\|")


def _markdown_list(items: Iterable[Any], empty: str = "None recorded.") -> str:
    values = [compact_text(item, default="") for item in items if compact_text(item, default="")]
    return "\n".join(f"- {item}" for item in values) if values else f"- {empty}"


def _metrics_markdown(before: dict[str, Any], after: dict[str, Any]) -> str:
    keys = sorted(set(before) | set(after))
    if not keys:
        return "No metrics snapshot was available for this run."
    rows = ["| Metric | Before | After |", "|---|---:|---:|"]
    rows.extend(f"| `{key}` | {_format_value(before.get(key))} | {_format_value(after.get(key))} |" for key in keys)
    return "\n".join(rows)


def render_daily_markdown(local_date: str, events: list[dict[str, Any]], generated_at: str) -> str:
    ordered = sorted(events, key=lambda item: (item["started_at_utc"], item["event_id"]))
    workflows = sorted({event["workflow"] for event in ordered})
    failures = sum(event["status"] not in {"success", "passed", "healthy", "skipped"} for event in ordered)
    lines = [
        f"# CommerceLint autonomous diary — {local_date}",
        "",
        f"- Generated: `{generated_at}` UTC / `{local_timestamp(generated_at)}` {TIMEZONE_NAME}",
        f"- Recorded runs: **{len(ordered)}**",
        f"- Workflows: {', '.join(f'`{item}`' for item in workflows) if workflows else 'None'}",
        f"- Runs requiring attention: **{failures}**",
        "- Decision summaries are concise operational rationales, not hidden chain-of-thought.",
        "- Missing historical detail is labeled explicitly; backfill never invents events.",
        "",
    ]
    for event in ordered:
        local_start = parse_timestamp(event["started_at_utc"]).astimezone(LOCAL_TIMEZONE)
        title = event["task_selected"]["title"]
        lines.extend(
            [
                f"## {local_start.strftime('%H:%M:%S %Z')} — {event['workflow']} — {event['status']}",
                "",
                f"- Run ID: `{event['run_id']}`",
                f"- Event ID: `{event['event_id']}`",
                f"- Start: `{event['started_at_utc']}` UTC / `{event['started_at_local']}` {TIMEZONE_NAME}",
                f"- End: `{event['ended_at_utc']}` UTC / `{event['ended_at_local']}` {TIMEZONE_NAME}",
                f"- Trigger: {event['trigger']}",
                f"- Task selected: **{title}**" + (f" (`{event['task_selected']['id']}`)" if event['task_selected']['id'] else ""),
                f"- Backfilled: {'yes' if event['backfilled'] else 'no'}",
                "",
                "### Decision summary",
                "",
                event["decision_summary"],
                "",
                "### Evidence consulted",
                "",
                _markdown_list(event["evidence_consulted"]),
                "",
                "### Action taken",
                "",
                event["action_taken"]["summary"],
                "",
                _markdown_list(event["action_taken"]["details"]),
                "",
                "### Verification",
                "",
                f"- Status: **{event['verification']['status']}**",
                f"- Summary: {event['verification']['summary']}",
                _markdown_list(
                    [
                        f"{item.get('name', 'check')}: {'passed' if item.get('ok') else 'failed'} — {item.get('detail', '')}"
                        if isinstance(item, dict)
                        else item
                        for item in event["verification"]["checks"]
                    ]
                ),
                "",
                "### Metrics",
                "",
                _metrics_markdown(event["metrics_before"], event["metrics_after"]),
                "",
                "### Blockers",
                "",
                _markdown_list(event["blockers"]),
                "",
                "### Failures and retries",
                "",
                _markdown_list(event["failures_retries"]),
                "",
                "### Lessons",
                "",
                _markdown_list(event["lessons"]),
                "",
                "### Next action",
                "",
                event["next_action"],
                "",
                "### References",
                "",
                _markdown_list(event["links"] + [f"commit `{item}`" for item in event["commit_hashes"]]),
            ]
        )
        if event["backfill_notes"]:
            lines.extend(["", "### Backfill limitations", "", _markdown_list(event["backfill_notes"])])
        lines.extend(["", "---", ""])
    return "\n".join(lines).rstrip() + "\n"


def rebuild_day(local_date: str, root: Path = ROOT) -> dict[str, Any]:
    events_path = _events_path(root, local_date)
    events = load_events(events_path)
    events.sort(key=lambda item: (item["started_at_utc"], item["event_id"]))
    generated_at = iso_utc(utc_now())
    daily = {
        "schema_version": SCHEMA_VERSION,
        "date_local": local_date,
        "timezone": TIMEZONE_NAME,
        "generated_at_utc": generated_at,
        "generated_at_local": local_timestamp(generated_at),
        "event_count": len(events),
        "status_counts": {},
        "workflow_counts": {},
        "events": events,
    }
    for event in events:
        daily["status_counts"][event["status"]] = daily["status_counts"].get(event["status"], 0) + 1
        daily["workflow_counts"][event["workflow"]] = daily["workflow_counts"].get(event["workflow"], 0) + 1
    daily_root = root / "state" / "audit" / "daily"
    write_json(daily_root / f"{local_date}.json", daily)
    atomic_write(daily_root / f"{local_date}.md", render_daily_markdown(local_date, events, generated_at))
    rebuild_index(root)
    return daily


def rebuild_index(root: Path = ROOT) -> dict[str, Any]:
    daily_root = root / "state" / "audit" / "daily"
    days: list[dict[str, Any]] = []
    for path in sorted(daily_root.glob("????-??-??.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        events = payload.get("events", [])
        days.append(
            {
                "date_local": payload.get("date_local", path.stem),
                "event_count": len(events),
                "status_counts": payload.get("status_counts", {}),
                "workflow_counts": payload.get("workflow_counts", {}),
                "first_started_at_utc": events[0]["started_at_utc"] if events else None,
                "last_ended_at_utc": events[-1]["ended_at_utc"] if events else None,
                "markdown": f"daily/{path.stem}.md",
                "json": f"daily/{path.stem}.json",
                "jsonl": f"events/{path.stem}.jsonl",
            }
        )
    generated_at = iso_utc(utc_now())
    index = {
        "schema_version": SCHEMA_VERSION,
        "timezone": TIMEZONE_NAME,
        "generated_at_utc": generated_at,
        "generated_at_local": local_timestamp(generated_at),
        "day_count": len(days),
        "event_count": sum(day["event_count"] for day in days),
        "days": days,
    }
    audit_root = root / "state" / "audit"
    write_json(audit_root / "index.json", index)
    lines = [
        "# CommerceLint autonomous run-log index",
        "",
        f"- Generated: `{generated_at}` UTC / `{local_timestamp(generated_at)}` {TIMEZONE_NAME}",
        f"- Days recorded: **{index['day_count']}**",
        f"- Runs recorded: **{index['event_count']}**",
        "- Canonical machine stream: `events/YYYY-MM-DD.jsonl`",
        "- Daily machine snapshots: `daily/YYYY-MM-DD.json`",
        "- Daily human diaries: `daily/YYYY-MM-DD.md`",
        "",
        "| Eastern date | Runs | Workflow counts | Status counts | Diary | JSON | JSONL |",
        "|---|---:|---|---|---|---|---|",
    ]
    for day in days:
        workflows = ", ".join(f"{key}: {value}" for key, value in sorted(day["workflow_counts"].items()))
        statuses = ", ".join(f"{key}: {value}" for key, value in sorted(day["status_counts"].items()))
        date = day["date_local"]
        lines.append(
            f"| {date} | {day['event_count']} | {workflows or '—'} | {statuses or '—'} | "
            f"[Markdown](daily/{date}.md) | [JSON](daily/{date}.json) | [JSONL](events/{date}.jsonl) |"
        )
    atomic_write(audit_root / "INDEX.md", "\n".join(lines) + "\n")
    return index


def record_event(raw_event: dict[str, Any], root: Path = ROOT) -> tuple[dict[str, Any], bool]:
    event = normalize_event(raw_event)
    local_date = event["started_at_local"][:10]
    path = _events_path(root, local_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_events(path)
    if any(item.get("event_id") == event["event_id"] for item in existing):
        rebuild_day(local_date, root)
        return event, False
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    rebuild_day(local_date, root)
    return event, True


def record_events(raw_events: Iterable[dict[str, Any]], root: Path = ROOT) -> tuple[int, int]:
    """Append a batch idempotently and rebuild each affected day once."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    total = 0
    for raw_event in raw_events:
        event = normalize_event(raw_event)
        local_date = event["started_at_local"][:10]
        grouped.setdefault(local_date, []).append(event)
        total += 1
    appended = 0
    for local_date, events in grouped.items():
        path = _events_path(root, local_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = load_events(path)
        known = {item.get("event_id") for item in existing}
        new_events = [event for event in events if event["event_id"] not in known]
        if new_events:
            with path.open("a", encoding="utf-8") as handle:
                for event in new_events:
                    handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            appended += len(new_events)
        rebuild_day(local_date, root)
    rebuild_index(root)
    return total, appended


def event_from_environment() -> dict[str, Any]:
    """Build a bounded workflow event from explicitly allowlisted environment fields."""
    now = iso_utc(utc_now())
    workflow = os.environ.get("RUNLOG_WORKFLOW", "workflow")
    run_id = os.environ.get("RUNLOG_RUN_ID") or os.environ.get("GITHUB_RUN_ID") or now
    links = json.loads(os.environ.get("RUNLOG_LINKS", "[]"))
    run_link = workflow_run_url()
    if run_link:
        links.append(run_link)
    sha = os.environ.get("GITHUB_SHA", "").strip()
    return {
        "event_id": stable_event_id(workflow, str(run_id)),
        "run_id": str(run_id),
        "workflow": workflow,
        "status": os.environ.get("RUNLOG_STATUS", "unknown"),
        "started_at_utc": os.environ.get("RUNLOG_STARTED_AT_UTC", now),
        "ended_at_utc": os.environ.get("RUNLOG_ENDED_AT_UTC", now),
        "trigger": os.environ.get("RUNLOG_TRIGGER") or os.environ.get("GITHUB_EVENT_NAME", "local"),
        "task_selected": {
            "id": os.environ.get("RUNLOG_TASK_ID") or None,
            "title": os.environ.get("RUNLOG_TASK_TITLE", "Workflow execution"),
            "type": os.environ.get("RUNLOG_TASK_TYPE") or None,
        },
        "decision_summary": os.environ.get("RUNLOG_DECISION_SUMMARY", UNKNOWN),
        "evidence_consulted": json.loads(os.environ.get("RUNLOG_EVIDENCE", "[]")),
        "action_taken": {
            "summary": os.environ.get("RUNLOG_ACTION", UNKNOWN),
            "details": json.loads(os.environ.get("RUNLOG_ACTION_DETAILS", "[]")),
        },
        "verification": {
            "status": os.environ.get("RUNLOG_VERIFICATION_STATUS", "unknown"),
            "summary": os.environ.get("RUNLOG_VERIFICATION", UNKNOWN),
            "checks": json.loads(os.environ.get("RUNLOG_CHECKS", "[]")),
        },
        "metrics_before": json.loads(os.environ.get("RUNLOG_METRICS_BEFORE", "{}")),
        "metrics_after": json.loads(os.environ.get("RUNLOG_METRICS_AFTER", "{}")),
        "blockers": json.loads(os.environ.get("RUNLOG_BLOCKERS", "[]")),
        "failures_retries": json.loads(os.environ.get("RUNLOG_FAILURES_RETRIES", "[]")),
        "lessons": json.loads(os.environ.get("RUNLOG_LESSONS", "[]")),
        "next_action": os.environ.get("RUNLOG_NEXT_ACTION", UNKNOWN),
        "links": links,
        "commit_hashes": [sha] if sha else [],
        "source": {"system": "github_actions", "references": []},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write or rebuild CommerceLint durable autonomous run logs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    record_parser = subparsers.add_parser("record", help="Record one event from a JSON payload.")
    record_parser.add_argument("--payload", type=Path, help="JSON file; stdin is used when omitted.")
    subparsers.add_parser("record-env", help="Record an event from allowlisted RUNLOG_* environment fields.")
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild daily views and indexes from JSONL.")
    rebuild_parser.add_argument("--date", help="One America/New_York date; all dates are rebuilt when omitted.")
    args = parser.parse_args()

    if args.command == "record":
        if args.payload:
            payload = json.loads(args.payload.read_text(encoding="utf-8"))
        else:
            payload = json.load(__import__("sys").stdin)
        event, appended = record_event(payload)
        print(json.dumps({"event_id": event["event_id"], "appended": appended}, sort_keys=True))
        return 0
    if args.command == "record-env":
        event, appended = record_event(event_from_environment())
        print(json.dumps({"event_id": event["event_id"], "appended": appended}, sort_keys=True))
        return 0
    if args.date:
        rebuild_day(args.date)
    else:
        events_root = AUDIT_ROOT / "events"
        for path in sorted(events_root.glob("????-??-??.jsonl")):
            rebuild_day(path.stem)
        rebuild_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
