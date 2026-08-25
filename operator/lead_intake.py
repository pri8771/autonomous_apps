#!/usr/bin/env python3
"""Ingest a public CommerceLint GitHub request and produce a safe first-pass comment."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    from .crm import empty_crm, upsert_public_github_lead
except ImportError:  # Direct script execution from operator/
    from crm import empty_crm, upsert_public_github_lead

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "state.json"
LEADS_PATH = ROOT / "state" / "leads.json"
CRM_PATH = ROOT / "state" / "crm.json"
MAX_HTML_BYTES = 262_144
TITLE_PREFIX = "[CommerceLint request]"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def form_field(body: str, label: str) -> str:
    pattern = re.compile(
        rf"(?:^|\n)###\s+{re.escape(label)}\s*\n+(.*?)(?=\n+###\s+|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return ""
    value = match.group(1).strip()
    return "" if value == "_No response_" else value


def normalized_public_url(raw: str) -> str:
    raw = raw.strip().strip("<>")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only public HTTP or HTTPS URLs are accepted.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not accepted.")
    if not parsed.hostname:
        raise ValueError("The URL has no hostname.")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("Only standard HTTP and HTTPS ports are accepted.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".home")):
        raise ValueError("Private or local hostnames are not accepted.")
    validate_public_host(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    cleaned = parsed._replace(fragment="")
    return urllib.parse.urlunsplit(cleaned)


def validate_public_host(host: str, port: int) -> None:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"The hostname could not be resolved: {exc}") from exc
    if not addresses:
        raise ValueError("The hostname did not resolve.")
    for info in addresses:
        address = info[4][0].split("%", 1)[0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("The URL resolves to a non-public network address.")


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        normalized_public_url(urllib.parse.urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CommercePageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.in_jsonld = False
        self.current_jsonld: list[str] = []
        self.jsonld_blocks: list[str] = []
        self.canonicals: list[str] = []
        self.meta_robots: list[str] = []
        self.select_count = 0

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self.in_title = True
        elif tag == "script" and "ld+json" in values.get("type", "").lower():
            self.in_jsonld = True
            self.current_jsonld = []
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            if values.get("href"):
                self.canonicals.append(values["href"])
        elif tag == "meta" and values.get("name", "").lower() == "robots":
            self.meta_robots.append(values.get("content", ""))
        elif tag == "select":
            self.select_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_jsonld:
            self.in_jsonld = False
            self.jsonld_blocks.append("".join(self.current_jsonld).strip())
            self.current_jsonld = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_jsonld:
            self.current_jsonld.append(data)


def walk_json(value: Any) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if isinstance(value, dict):
        objects.append(value)
        for child in value.values():
            objects.extend(walk_json(child))
    elif isinstance(value, list):
        for child in value:
            objects.extend(walk_json(child))
    return objects


def type_names(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, str):
        names.add(value.lower())
    elif isinstance(value, list):
        names.update(str(item).lower() for item in value)
    return names


def fetch_public_html(url: str) -> tuple[str, str, int]:
    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CommerceLint-Public-Preview/1.0 (+https://priyanshchordia.com/commercelint/)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        },
    )
    with opener.open(request, timeout=15) as response:
        final_url = normalized_public_url(response.geturl())
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"The URL returned {content_type}, not an HTML page.")
        payload = response.read(MAX_HTML_BYTES + 1)
        if len(payload) > MAX_HTML_BYTES:
            payload = payload[:MAX_HTML_BYTES]
        charset = response.headers.get_content_charset() or "utf-8"
        return final_url, payload.decode(charset, errors="replace"), int(response.status)


def preliminary_findings(url: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    final_url, page, status = fetch_public_html(url)
    parser = CommercePageParser()
    parser.feed(page)

    json_objects: list[dict[str, Any]] = []
    invalid_jsonld = 0
    for block in parser.jsonld_blocks:
        if not block:
            continue
        try:
            json_objects.extend(walk_json(json.loads(block)))
        except json.JSONDecodeError:
            invalid_jsonld += 1

    products = [obj for obj in json_objects if "product" in type_names(obj.get("@type"))]
    offers = [
        obj
        for obj in json_objects
        if type_names(obj.get("@type")) & {"offer", "aggregateoffer"}
    ]
    page_lower = page.lower()
    noindex = any("noindex" in value.lower() for value in parser.meta_robots)
    has_price_signal = bool(re.search(r"(?:[$€£]\s?\d|itemprop=[\"']price|\"price\"\s*:)", page, re.I))
    has_availability_signal = bool(
        re.search(r"(?:instock|outofstock|preorder|itemprop=[\"']availability|\"availability\"\s*:)", page, re.I)
    )
    has_policy_signal = "return" in page_lower and ("shipping" in page_lower or "delivery" in page_lower)
    has_variant_signal = parser.select_count > 0 or any(
        marker in page_lower
        for marker in ("variant", "swatch", "product-option", "variation")
    )

    def finding(check: str, result: str, evidence: str, next_step: str) -> dict[str, str]:
        return {
            "check": check,
            "result": result,
            "evidence": evidence,
            "next_step": next_step,
        }

    findings = [
        finding(
            "Public retrieval",
            "Pass",
            f"HTTP {status}; inspected {final_url}",
            "Keep a stable public product URL for repeatable verification.",
        ),
        finding(
            "Indexability",
            "Review" if noindex else "Pass",
            "A noindex directive was found." if noindex else "No HTML meta noindex directive was detected.",
            "Confirm intentional indexing policy and check HTTP/X-Robots-Tag rules separately.",
        ),
        finding(
            "Canonical URL",
            "Pass" if len(parser.canonicals) == 1 else "Review",
            (
                f"One canonical was found: {parser.canonicals[0]}"
                if len(parser.canonicals) == 1
                else f"Found {len(parser.canonicals)} canonical declarations."
            ),
            "Expose one self-consistent canonical URL for the selected product state.",
        ),
        finding(
            "Product structured data",
            "Pass" if products else "Fail",
            f"Detected {len(products)} Product object(s); {invalid_jsonld} JSON-LD block(s) could not be parsed.",
            "Publish a valid Product object that matches visible product facts.",
        ),
        finding(
            "Offer structured data",
            "Pass" if offers else "Fail",
            f"Detected {len(offers)} Offer or AggregateOffer object(s).",
            "Tie visible price, currency, availability, URL, and selected variant to an Offer.",
        ),
        finding(
            "Visible commerce signals",
            "Pass" if has_price_signal and has_availability_signal else "Review",
            f"Price signal: {has_price_signal}; availability signal: {has_availability_signal}.",
            "Make price and availability explicit and consistent in visible HTML and structured data.",
        ),
        finding(
            "Policies",
            "Pass" if has_policy_signal else "Review",
            "Return plus shipping/delivery language was detected." if has_policy_signal else "Return and shipping evidence was not clearly detected in the sampled HTML.",
            "Expose concise purchase-policy evidence near the buying decision and link complete terms.",
        ),
        finding(
            "Variant evidence",
            "Review" if has_variant_signal else "Not detected",
            "Variant or option signals were detected." if has_variant_signal else "No obvious variant controls or markers were detected.",
            "For variable products, verify every purchasable state has the correct identifier, price, stock, image, and URL behavior.",
        ),
    ]
    metadata = {
        "final_url": final_url,
        "http_status": status,
        "page_title": parser.title,
        "product_objects": len(products),
        "offer_objects": len(offers),
        "invalid_jsonld_blocks": invalid_jsonld,
    }
    return findings, metadata


def table_cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())


def render_comment(
    issue_number: int,
    store_url: str,
    qualified: bool,
    findings: list[dict[str, str]],
    metadata: dict[str, Any],
    error: str,
) -> str:
    lines = [
        "## CommerceLint automated first pass",
        "",
        "Thanks for the public request. This response was generated from public page evidence; no private access was attempted.",
        "",
    ]
    if not qualified:
        lines.extend(
            [
                f"I could not accept the supplied URL for automated retrieval: **{html.escape(error)}**",
                "",
                "Please edit the request with a public HTTP or HTTPS storefront URL. Do not post credentials, private links, customer data, or unpublished information.",
            ]
        )
        return "\n".join(lines) + "\n"

    if error:
        lines.extend(
            [
                f"The request was recorded, but the automated fetch could not complete: **{html.escape(error)}**",
                "",
                "Some stores block automated retrieval. A blocked preview is not evidence that the product page itself is defective.",
            ]
        )
    else:
        title = metadata.get("page_title") or "Untitled page"
        lines.extend(
            [
                f"**Sampled page:** {metadata.get('final_url', store_url)}",
                f"**Page title:** {title}",
                "",
                "| Check | Result | Observed evidence | Recommended next step |",
                "|---|---|---|---|",
            ]
        )
        for item in findings:
            lines.append(
                "| {check} | {result} | {evidence} | {next_step} |".format(
                    **{key: table_cell(str(value)) for key, value in item.items()}
                )
            )

    lines.extend(
        [
            "",
            "### What this preview does not do",
            "",
            "- It samples one public response and may not execute all storefront JavaScript.",
            "- It does not validate every variant, feed row, policy page, checkout state, or search-engine interpretation.",
            "- It does not guarantee indexing, recommendation, traffic, conversion, or sales.",
            "",
            "### Next commercial step",
            "",
            "The $49 founding defect pack expands this into a representative catalog sample, prioritized implementation backlog, acceptance checks, and one clarification round. Scope is confirmed before any payment request.",
            "",
            f"Request reference: GitHub issue #{issue_number}.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--comment-output", type=Path, required=True)
    args = parser.parse_args()

    event = json.loads(args.event.read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    title = str(issue.get("title") or "")
    if not title.startswith(TITLE_PREFIX):
        raise SystemExit("Not a CommerceLint request issue.")

    body = str(issue.get("body") or "")
    issue_number = int(issue["number"])
    store_url_raw = form_field(body, "Public store URL")
    role = form_field(body, "Your role")
    platform = form_field(body, "Platform")
    main_goal = form_field(body, "Main goal")
    catalog_size = form_field(body, "Approximate catalog size")
    context = form_field(body, "What changed, or what should the review answer?")
    username = str((issue.get("user") or {}).get("login") or "unknown")
    issue_url = str(issue.get("html_url") or "")
    created_at = str(issue.get("created_at") or now_iso())

    qualified = False
    normalized_url = ""
    validation_error = ""
    findings: list[dict[str, str]] = []
    metadata: dict[str, Any] = {}
    scan_error = ""
    try:
        normalized_url = normalized_public_url(store_url_raw)
        qualified = True
    except Exception as exc:
        validation_error = str(exc)

    if qualified:
        try:
            findings, metadata = preliminary_findings(normalized_url)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            scan_error = str(exc)
        except Exception as exc:
            scan_error = f"{type(exc).__name__}: {exc}"

    leads = load_json(
        LEADS_PATH,
        {"schema_version": 1, "updated_at_utc": None, "leads": []},
    )
    lead_id = f"github-issue-{issue_number}"
    existing = next(
        (lead for lead in leads.get("leads", []) if lead.get("id") == lead_id),
        None,
    )
    record = {
        "id": lead_id,
        "source": "github_issue_form",
        "issue_number": issue_number,
        "issue_url": issue_url,
        "github_user": username,
        "created_at_utc": created_at,
        "updated_at_utc": now_iso(),
        "role": role,
        "store_url": normalized_url or store_url_raw,
        "platform": platform,
        "main_goal": main_goal,
        "catalog_size": catalog_size,
        "context": context,
        "qualified": qualified,
        "status": "new" if qualified else "needs_public_url",
        "preview_status": "completed" if findings else ("blocked" if qualified else "rejected"),
        "preview_error": scan_error or validation_error,
        "preview_metadata": metadata,
    }
    is_new = existing is None
    if existing is None:
        leads.setdefault("leads", []).append(record)
    else:
        existing.update(record)
    leads["updated_at_utc"] = now_iso()
    write_json(LEADS_PATH, leads)

    crm = load_json(CRM_PATH, empty_crm())
    upsert_public_github_lead(
        crm,
        {
            "id": lead_id,
            "source": "github_issue_form",
            "issue_url": issue_url,
            "github_user": username,
            "created_at_utc": created_at,
            "store_url": normalized_url or store_url_raw,
            "role": role,
            "platform": platform,
            "main_goal": main_goal,
            "qualified": qualified,
        },
        at_utc=record["updated_at_utc"],
    )
    write_json(CRM_PATH, crm)

    state = load_json(STATE_PATH, {})
    metrics = state.setdefault("metrics", {})
    metrics.setdefault("lead_requests", 0)
    metrics.setdefault("qualified_leads", 0)
    if is_new:
        metrics["lead_requests"] += 1
        if qualified:
            metrics["qualified_leads"] += 1
    state["last_lead_event"] = {
        "at_utc": now_iso(),
        "lead_id": lead_id,
        "qualified": qualified,
        "issue_url": issue_url,
    }
    write_json(STATE_PATH, state)

    comment = render_comment(
        issue_number=issue_number,
        store_url=normalized_url or store_url_raw,
        qualified=qualified,
        findings=findings,
        metadata=metadata,
        error=validation_error or scan_error,
    )
    args.comment_output.parent.mkdir(parents=True, exist_ok=True)
    args.comment_output.write_text(comment, encoding="utf-8")

    print(
        json.dumps(
            {
                "issue_number": issue_number,
                "lead_id": lead_id,
                "new": is_new,
                "qualified": qualified,
                "preview_status": record["preview_status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
