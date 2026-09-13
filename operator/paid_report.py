#!/usr/bin/env python3
"""Generate plan-scoped CommerceLint paid reports from public page HTML."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI_DIR = ROOT / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))
if str(ROOT / "operator") not in sys.path:
    sys.path.insert(0, str(ROOT / "operator"))

import commercelint  # noqa: E402
from plans import get_plan, load_plans_config  # noqa: E402
from public_url import validate_url_batch  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def analyze_html(source_name: str, markup: str) -> dict[str, Any]:
    return commercelint.analyze_html(markup, source=source_name)


def page_reports_from_html(
    plan_id: str,
    pages: list[dict[str, str]],
    *,
    order_id: str | None = None,
    resolve_dns: bool = False,
) -> dict[str, Any]:
    """Build a paid report from already-fetched public HTML pages.

    pages: [{"url": "...", "html": "..."}]
    """
    config = load_plans_config()
    plan = get_plan(plan_id, config)
    max_urls = int(plan["max_public_product_urls"])
    urls = [page["url"] for page in pages]
    batch = validate_url_batch(urls, max_urls=max_urls, resolve_dns=resolve_dns)
    if not batch["ok"]:
        raise ValueError(batch["error"])

    if len(pages) != len(batch["accepted_urls"]):
        # Re-validate using normalized URLs already accepted.
        pass

    page_results: list[dict[str, Any]] = []
    fail_labels: Counter[str] = Counter()
    warning_labels: Counter[str] = Counter()

    for page, accepted_url in zip(pages, batch["accepted_urls"], strict=False):
        markup = page.get("html") or ""
        if not markup.strip():
            raise ValueError(f"Missing HTML for accepted URL: {accepted_url}")
        report = analyze_html(accepted_url, markup)
        page_results.append(
            {
                "url": accepted_url,
                "score": report["score"],
                "counts": report["counts"],
                "page_title": report["page"]["title"],
                "checks": report["checks"],
                "source_sha256": report["source"]["sha256"],
            }
        )
        for check in report["checks"]:
            if check["status"] == "fail":
                fail_labels[check["label"]] += 1
            elif check["status"] == "warning":
                warning_labels[check["label"]] += 1

    comparison = None
    if plan.get("includes_page_comparison") and len(page_results) > 1:
        comparison = {
            "score_by_url": {item["url"]: item["score"] for item in page_results},
            "lowest_score_url": min(page_results, key=lambda item: item["score"])["url"],
            "highest_score_url": max(page_results, key=lambda item: item["score"])["url"],
        }

    repeated = None
    if plan.get("includes_repeated_issue_grouping"):
        repeated = {
            "fail_checks_appearing_on_multiple_pages": [
                {"label": label, "page_count": count}
                for label, count in fail_labels.most_common()
                if count > 1
            ],
            "warning_checks_appearing_on_multiple_pages": [
                {"label": label, "page_count": count}
                for label, count in warning_labels.most_common()
                if count > 1
            ],
        }

    retest = None
    if plan.get("includes_retest_checklist"):
        priorities = []
        for item in page_results:
            for check in item["checks"]:
                if check["status"] in {"fail", "warning"}:
                    priorities.append(
                        {
                            "url": item["url"],
                            "status": check["status"],
                            "check": check["label"],
                            "repair": check["repair"],
                        }
                    )
        retest = {
            "checklist": priorities[:50],
            "instruction": "Retest each repaired URL with the free scanner or CLI and confirm live storefront behavior.",
        }

    payload = {
        "schema_version": 1,
        "report_type": "commercelint_paid_report",
        "generated_at_utc": now_iso(),
        "order_id": order_id,
        "plan": {
            "id": plan["id"],
            "name": plan["name"],
            "price_usd": plan["price_usd"],
            "max_public_product_urls": max_urls,
            "deliverable": plan["deliverable"],
            "report_kind": plan["report_kind"],
        },
        "pages": page_results,
        "comparison": comparison,
        "repeated_issues": repeated,
        "retest_checklist": retest,
        "limitations": list(config.get("shared_limitations") or []),
        "promise": "Field presence, parseability, and discoverability screening within the selected plan scope only.",
    }
    digest = hashlib.sha256(
        json.dumps(
            {
                "plan_id": plan["id"],
                "urls": [item["url"] for item in page_results],
                "scores": [item["score"] for item in page_results],
                "check_ids": [[c["id"] for c in item["checks"]] for item in page_results],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    payload["report_sha256"] = digest
    return payload


def render_paid_markdown(report: dict[str, Any]) -> str:
    plan = report["plan"]
    lines = [
        f"# CommerceLint {plan['name']} report",
        "",
        f"- **Plan:** {plan['name']} (${plan['price_usd']} USD one-time)",
        f"- **Generated:** {report['generated_at_utc']}",
        f"- **Pages reviewed:** {len(report['pages'])} / {plan['max_public_product_urls']} allowed",
        f"- **Report SHA-256:** `{report['report_sha256']}`",
        "",
        plan["deliverable"],
        "",
    ]
    if report.get("order_id"):
        lines.insert(3, f"- **Order reference:** `{report['order_id']}`")

    for index, page in enumerate(report["pages"], start=1):
        lines += [
            f"## Page {index}: {page['page_title']}",
            "",
            f"- **URL:** {page['url']}",
            f"- **Score:** {page['score']}/100",
            f"- **Pass / warn / fail:** {page['counts']['pass']} / {page['counts']['warning']} / {page['counts']['fail']}",
            "",
            "| Status | Check | Evidence | Repair |",
            "| --- | --- | --- | --- |",
        ]
        order = {"fail": 0, "warning": 1, "pass": 2}
        for check in sorted(page["checks"], key=lambda item: (order[item["status"]], -item["weight"])):
            evidence = str(check["evidence"]).replace("|", "\\|").replace("\n", " ")
            repair = str(check["repair"]).replace("|", "\\|").replace("\n", " ")
            label = str(check["label"]).replace("|", "\\|")
            lines.append(f"| {check['status'].upper()} | {label} | {evidence} | {repair} |")
        lines.append("")

    if report.get("comparison"):
        lines += ["## Cross-page comparison", ""]
        for url, score in report["comparison"]["score_by_url"].items():
            lines.append(f"- `{url}` — {score}/100")
        lines += [
            "",
            f"- Lowest score: `{report['comparison']['lowest_score_url']}`",
            f"- Highest score: `{report['comparison']['highest_score_url']}`",
            "",
        ]

    if report.get("repeated_issues"):
        lines += ["## Repeated issues", ""]
        fails = report["repeated_issues"]["fail_checks_appearing_on_multiple_pages"]
        if fails:
            for item in fails:
                lines.append(f"- FAIL `{item['label']}` on {item['page_count']} pages")
        else:
            lines.append("- No fail checks repeated across multiple pages.")
        lines.append("")

    if report.get("retest_checklist"):
        lines += ["## Retest checklist", "", report["retest_checklist"]["instruction"], ""]
        for item in report["retest_checklist"]["checklist"][:30]:
            lines.append(f"- [{item['status']}] {item['check']} — {item['url']}")
            lines.append(f"  - Repair: {item['repair']}")
        lines.append("")

    lines += ["## Limitations", ""]
    lines += [f"- {item}" for item in report["limitations"]]
    lines += ["", report["promise"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a plan-scoped CommerceLint paid report from local HTML fixtures.")
    parser.add_argument("--plan", required=True, choices=["sample", "lite", "comprehensive"])
    parser.add_argument("--order-id", default=None)
    parser.add_argument("--html", action="append", nargs=2, metavar=("URL", "PATH"), required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args()

    pages = []
    for url, path in args.html:
        pages.append({"url": url, "html": Path(path).read_text(encoding="utf-8")})
    report = page_reports_from_html(args.plan, pages, order_id=args.order_id, resolve_dns=False)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_paid_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "report_sha256": report["report_sha256"], "pages": len(report["pages"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
