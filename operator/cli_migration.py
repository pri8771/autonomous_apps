#!/usr/bin/env python3
"""Verify and publish the CommerceLint developer CLI once.

This migration is intentionally idempotent. The hourly operator runs it before
its normal decision cycle. Publication happens only after deterministic tests,
a strong-fixture success gate, and an incomplete-fixture failure gate pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "state" / "cli_launch.json"
CLI = ROOT / "cli" / "commercelint.py"
STRONG = ROOT / "tests" / "fixtures" / "strong.html"
INCOMPLETE = ROOT / "tests" / "fixtures" / "missing-offer.html"
PUBLIC_REPORT = ROOT / "docs" / "downloads" / "commercelint-cli-sample-report.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def replace_once(path_text: str, old: str, new: str) -> bool:
    path = ROOT / path_text
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path_text}: expected one occurrence of {old!r}, found {count}")
    atomic_write(path, text.replace(old, new, 1))
    return True


def run(command: list[str], *, expected: int = 0) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != expected:
        raise RuntimeError(
            f"Command returned {completed.returncode}, expected {expected}: {command}\n"
            f"stdout={completed.stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
        )
    return result


def verify_bundle() -> list[dict[str, Any]]:
    required = [
        CLI,
        STRONG,
        INCOMPLETE,
        ROOT / "tests" / "test_cli.py",
        ROOT / "action.yml",
        ROOT / ".github" / "workflows" / "cli-test.yml",
        ROOT / "docs" / "cli.html",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file() or path.stat().st_size < 40]
    if missing:
        raise RuntimeError(f"Missing CLI launch assets: {missing}")

    PUBLIC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    results = [
        run([sys.executable, "-m", "py_compile", str(CLI.relative_to(ROOT))]),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        run(
            [
                sys.executable,
                str(CLI.relative_to(ROOT)),
                str(STRONG.relative_to(ROOT)),
                "--format",
                "markdown",
                "--output",
                str(PUBLIC_REPORT.relative_to(ROOT)),
                "--min-score",
                "90",
                "--fail-on",
                "fail",
                "--quiet",
            ]
        ),
        run(
            [
                sys.executable,
                str(CLI.relative_to(ROOT)),
                str(INCOMPLETE.relative_to(ROOT)),
                "--format",
                "text",
                "--fail-on",
                "fail",
            ],
            expected=1,
        ),
    ]
    report = PUBLIC_REPORT.read_text(encoding="utf-8")
    if "**Score:** 100/100" not in report or "## Limitations" not in report:
        raise RuntimeError("Strong fixture report did not contain the expected verified evidence.")
    return results


def patch_public_surfaces() -> list[str]:
    changed: list[str] = []

    replacements = [
        (
            "docs/index.html",
            '      <a href="scanner.html">Free scan</a>\n      <a href="guides/index.html">Guides</a>',
            '      <a href="scanner.html">Free scan</a>\n      <a href="cli.html">CI / CLI</a>\n      <a href="guides/index.html">Guides</a>',
        ),
        (
            "docs/scanner.html",
            '<nav><a href="scanner.html">Free scan</a><a href="guides/index.html">Guides</a><a href="status.html">Status</a></nav>',
            '<nav><a href="scanner.html">Free scan</a><a href="cli.html">CI / CLI</a><a href="guides/index.html">Guides</a><a href="status.html">Status</a></nav>',
        ),
        (
            "docs/llms.txt",
            "- Run the free browser scanner: https://priyanshchordia.com/commercelint/scanner.html\n",
            "- Run the free browser scanner: https://priyanshchordia.com/commercelint/scanner.html\n"
            "- Run the zero-dependency CLI or GitHub Action: https://priyanshchordia.com/commercelint/cli.html\n",
        ),
        (
            "docs/llms.txt",
            "## Founding audit\n",
            "## Developer CLI and GitHub Action\n\n"
            "The CLI checks field presence, JSON-LD parseability, identifiers, Offer fields, canonical signals, headings, descriptions, and obvious policy links. It can output JSON, Markdown, or text and enforce a minimum score in CI. It does not prove selected-variant state, visible-versus-structured consistency, feed or checkout agreement, rendered JavaScript, live HTTP status, or cross-page policy consistency.\n\n"
            "## Founding audit\n",
        ),
        (
            "operator/main.py",
            '    paths = ["", "scanner.html", "status.html", "privacy.html", "sample-audit.html", "founding-audit.html", "agency.html", "methodology.html", "service.json", "llms.txt", "guides/"]',
            '    paths = ["", "scanner.html", "cli.html", "status.html", "privacy.html", "sample-audit.html", "founding-audit.html", "agency.html", "methodology.html", "service.json", "llms.txt", "guides/"]',
        ),
        (
            ".github/workflows/indexnow.yml",
            '      - "docs/index.html"\n      - "docs/scanner.html"',
            '      - "docs/index.html"\n      - "docs/cli.html"\n      - "docs/scanner.html"',
        ),
        (
            "README.md",
            "- **Free browser scanner:** `https://priyanshchordia.com/commercelint/scanner.html`\n",
            "- **Free browser scanner:** `https://priyanshchordia.com/commercelint/scanner.html`\n"
            "- **CLI and GitHub Action:** `https://priyanshchordia.com/commercelint/cli.html`\n",
        ),
        (
            "README.md",
            "No Python dependencies outside the standard library are required by the hourly operator.\n",
            "No Python dependencies outside the standard library are required by the hourly operator.\n\n"
            "## Developer CLI and GitHub Action\n\n"
            "```bash\n"
            "python3 cli/commercelint.py tests/fixtures/strong.html --format markdown\n"
            "python3 -m unittest discover -s tests -v\n"
            "```\n\n"
            "The reusable composite action is defined in `action.yml`. It can fail a build on missing required commerce fields, warnings, or a minimum field-coverage score. The CLI deliberately does not claim to verify selected variants, live HTTP behavior, feeds, checkout, or cross-page consistency.\n",
        ),
    ]
    for path, old, new in replacements:
        if replace_once(path, old, new):
            changed.append(path)

    service_path = ROOT / "docs" / "service.json"
    service = load_json(service_path)
    developer_tool = {
        "name": "CommerceLint CLI and GitHub Action",
        "url": "https://priyanshchordia.com/commercelint/cli.html",
        "source_url": "https://github.com/pri8771/autonomous_apps",
        "price": 0,
        "price_currency": "USD",
        "runtime": "Python standard library",
        "outputs": ["JSON report", "Markdown report", "text report", "CI exit status"],
        "limitations": [
            "Field presence and discoverability screening only.",
            "Does not prove selected-variant, feed, checkout, policy-text, rendered-JavaScript, or live-HTTP consistency.",
        ],
    }
    if service.get("developer_tool") != developer_tool:
        service["developer_tool"] = developer_tool
        write_json(service_path, service)
        changed.append("docs/service.json")

    return changed


def update_durable_memory(at: str, verification: list[dict[str, Any]], changed: list[str]) -> None:
    summary_path = ROOT / "STATE.json"
    summary = load_json(summary_path)
    summary["generated_at_utc"] = at
    summary["last_verified_action"] = (
        "Launched a tested zero-dependency CommerceLint CLI and reusable GitHub Action, "
        "then linked it from the public product and machine-readable service surfaces."
    )
    summary["next_action"] = (
        "Use the developer tool as a durable distribution surface while monitoring the bounded "
        "agency-first cohort for verified replies or submitted requests."
    )
    write_json(summary_path, summary)

    state_path = ROOT / "state" / "state.json"
    state = load_json(state_path)
    task_id = "launch-developer-cli"
    if not any(task.get("id") == task_id for task in state.get("tasks", [])):
        state.setdefault("tasks", []).append(
            {
                "id": task_id,
                "title": "Launch a zero-dependency CommerceLint CLI and reusable GitHub Action",
                "type": "product_distribution",
                "status": "done",
                "priority": 82,
                "impact": 8,
                "urgency": 7,
                "confidence": 0.8,
                "effort": 4,
                "attempts": 1,
                "max_attempts": 2,
                "owner_required": False,
                "success_condition": (
                    "CLI, fixtures, tests, composite action, CI workflow, and public documentation "
                    "are installed and deterministic tests pass"
                ),
                "completed_at_utc": at,
                "evidence": "Five tests, a 100/100 strong fixture, and an expected incomplete-fixture exit code of 1 passed.",
            }
        )
    state["operator"]["last_major_action_at_utc"] = at
    state["operator"]["last_major_action"] = (
        "Launched the zero-dependency CommerceLint CLI and reusable GitHub Action with deterministic fixtures and CI tests."
    )
    lesson = (
        "A bounded open developer tool can create a reusable distribution surface while keeping "
        "the paid offer focused on cross-surface accuracy and implementation work."
    )
    if not any(item.get("lesson") == lesson for item in state.get("lessons", [])):
        state.setdefault("lessons", []).append(
            {
                "at_utc": at,
                "category": "product_distribution",
                "lesson": lesson,
                "evidence": (
                    "CLI supports JSON, Markdown, text, minimum score, and failure policies without "
                    "third-party Python dependencies."
                ),
            }
        )
    write_json(state_path, state)

    decisions_path = ROOT / "DECISIONS.md"
    decisions = decisions_path.read_text(encoding="utf-8")
    marker = "## 2026-08-24 — Add a developer-native distribution surface"
    if marker not in decisions:
        decisions += (
            f"\n\n{marker}\n\n"
            "- **Decision:** publish a zero-dependency CLI and reusable GitHub Action that mirrors the free browser tool's bounded field-presence promise.\n"
            "- **Reason:** developers and agencies can adopt a CI check without an account, creating product-led distribution and implementation evidence.\n"
            "- **Boundary:** selected variants, visible-versus-structured comparisons, policies, feeds, checkout, and live crawlability remain part of the paid defect pack or separately scoped work.\n"
        )
        atomic_write(decisions_path, decisions)

    changelog_path = ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    entry = (
        "- Launched the zero-dependency CommerceLint CLI, composite GitHub Action, deterministic "
        "fixtures, CI tests, sample report, and public developer documentation."
    )
    if entry not in changelog:
        atomic_write(changelog_path, changelog.rstrip() + "\n" + entry + "\n")

    write_json(
        MARKER,
        {
            "schema_version": 1,
            "status": "verified_and_published",
            "verified_at_utc": at,
            "verification": verification,
            "changed_files": sorted(set(changed)),
            "public_url": "https://priyanshchordia.com/commercelint/cli.html",
            "source_url": "https://github.com/pri8771/autonomous_apps",
            "sample_report": "docs/downloads/commercelint-cli-sample-report.md",
        },
    )


def already_complete() -> bool:
    if not MARKER.exists():
        return False
    try:
        marker = load_json(MARKER)
    except (OSError, json.JSONDecodeError):
        return False
    required_markers = [
        (ROOT / "docs" / "index.html", 'href="cli.html">CI / CLI'),
        (ROOT / "docs" / "sitemap.xml", "/commercelint/cli.html"),
        (ROOT / "docs" / "service.json", '"developer_tool"'),
        (ROOT / "operator" / "main.py", '"cli.html"'),
    ]
    return marker.get("status") == "verified_and_published" and all(
        path.exists() and expected in path.read_text(encoding="utf-8")
        for path, expected in required_markers
    )


def main() -> int:
    if already_complete():
        print("CommerceLint CLI launch migration already verified and published.")
        return 0

    at = now_iso()
    verification = verify_bundle()
    changed = patch_public_surfaces()
    update_durable_memory(at, verification, changed)
    print(
        json.dumps(
            {
                "status": "verified_and_published",
                "verified_at_utc": at,
                "changed_files": changed,
                "test_commands": len(verification),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
