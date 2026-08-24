#!/usr/bin/env python3
"""CommerceLint: zero-dependency product-page field coverage linter.

The CLI mirrors the public browser scanner's bounded promise. It checks whether
important Product/Offer fields and page-discoverability signals are present and
parseable. It does not prove that values match selected variants, feeds,
checkout, policy text, rendered JavaScript, or live HTTP behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_MAX_BYTES = 5_000_000
PASS_FACTOR = 1.0
WARNING_FACTOR = 0.45
FAIL_FACTOR = 0.0


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    status: str
    weight: int
    evidence: str
    why: str
    repair: str


class ProductPageParser(HTMLParser):
    """Extract only the bounded signals required by the linter."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.jsonld_blocks: list[str] = []
        self.canonical: str | None = None
        self.meta_description: str | None = None
        self.links: list[tuple[str, str]] = []
        self.h1_parts: list[str] = []
        self.title_parts: list[str] = []
        self._capture_jsonld = False
        self._jsonld_parts: list[str] = []
        self._h1_depth = 0
        self._title_depth = 0

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(key).lower(): value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = self._attrs(attrs)

        if tag == "script" and values.get("type", "").split(";", 1)[0].strip().lower() == "application/ld+json":
            self._capture_jsonld = True
            self._jsonld_parts = []
        elif tag == "link":
            rel_tokens = {token.lower() for token in values.get("rel", "").split()}
            if "canonical" in rel_tokens and values.get("href") and self.canonical is None:
                self.canonical = values["href"].strip()
        elif tag == "meta":
            if values.get("name", "").strip().lower() == "description" and values.get("content") and self.meta_description is None:
                self.meta_description = values["content"].strip()
        elif tag == "a" and values.get("href"):
            self.links.append((values["href"].strip(), ""))
        elif tag == "h1":
            self._h1_depth += 1
        elif tag == "title":
            self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._capture_jsonld:
            self.jsonld_blocks.append("".join(self._jsonld_parts).strip())
            self._capture_jsonld = False
            self._jsonld_parts = []
        elif tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        elif tag == "title" and self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_jsonld:
            self._jsonld_parts.append(data)
        if self._h1_depth:
            self.h1_parts.append(data)
        if self._title_depth:
            self.title_parts.append(data)

    @property
    def h1(self) -> str | None:
        value = " ".join("".join(self.h1_parts).split())
        return value or None

    @property
    def title(self) -> str | None:
        value = " ".join("".join(self.title_parts).split())
        return value or None


def flatten_json(value: Any, output: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Recursively collect JSON objects so Product nodes inside @graph are found."""
    if output is None:
        output = []
    if isinstance(value, list):
        for item in value:
            flatten_json(item, output)
    elif isinstance(value, dict):
        output.append(value)
        for child in value.values():
            if isinstance(child, (dict, list)):
                flatten_json(child, output)
    return output


def type_names(node: dict[str, Any]) -> list[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw] if raw else []
    names: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        names.append(text.rsplit("/", 1)[-1].rsplit("#", 1)[-1])
    return names


def first_by_type(nodes: Iterable[dict[str, Any]], wanted: set[str]) -> tuple[dict[str, Any] | None, int]:
    matches = [node for node in nodes if wanted.intersection(type_names(node))]
    return (matches[0] if matches else None, len(matches))


def value_present(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None and bool(str(value).strip())


def first_value(value: Any) -> Any:
    if isinstance(value, list):
        return first_value(value[0]) if value else None
    if isinstance(value, dict):
        for key in ("name", "url", "@id"):
            if value_present(value.get(key)):
                return value[key]
        return json.dumps(value, ensure_ascii=False, sort_keys=True)[:180]
    return value


def collect_offers(product: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not product:
        return []
    raw = product.get("offers")
    values = raw if isinstance(raw, list) else [raw] if raw else []
    return [item for item in values if isinstance(item, dict)]


def policy_link_present(links: Iterable[tuple[str, str]], words: Iterable[str]) -> bool:
    wanted = tuple(word.lower() for word in words)
    for href, text in links:
        haystack = f"{href} {text}".lower()
        if any(word in haystack for word in wanted):
            return True
    return False


def add_check(
    checks: list[Check],
    *,
    id: str,
    label: str,
    status: str,
    weight: int,
    evidence: str,
    why: str,
    repair: str,
) -> None:
    if status not in {"pass", "warning", "fail"}:
        raise ValueError(f"Unsupported check status: {status}")
    checks.append(Check(id, label, status, weight, evidence, why, repair))


def analyze_html(markup: str, *, source: str = "stdin") -> dict[str, Any]:
    parser = ProductPageParser()
    parser.feed(markup)
    parser.close()

    nodes: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for index, raw in enumerate(parser.jsonld_blocks, start=1):
        if not raw:
            continue
        try:
            flatten_json(json.loads(raw), nodes)
        except json.JSONDecodeError as exc:
            parse_errors.append(f"JSON-LD block {index}: {exc.msg} at line {exc.lineno}, column {exc.colno}")

    product, product_count = first_by_type(nodes, {"Product", "ProductGroup"})
    offers = collect_offers(product)
    offer = offers[0] if offers else None
    checks: list[Check] = []

    add_check(
        checks,
        id="product-object",
        label="Product structured data",
        status="pass" if product else "fail",
        weight=14,
        evidence=f"Found {product_count} Product/ProductGroup object(s)." if product else "No Product or ProductGroup JSON-LD object found.",
        why="A machine-readable product object provides an explicit product record.",
        repair="Add Product JSON-LD generated from the same catalog data shown to shoppers.",
    )
    add_check(
        checks,
        id="valid-jsonld",
        label="JSON-LD parses cleanly",
        status="fail" if parse_errors else "pass" if nodes else "warning",
        weight=7,
        evidence=" | ".join(parse_errors) if parse_errors else f"{len(nodes)} JSON object(s) parsed from JSON-LD.",
        why="Malformed JSON-LD can make useful commerce data unreadable.",
        repair="Validate every application/ld+json block after theme and app changes.",
    )

    product_name = first_value(product.get("name")) if product else None
    add_check(
        checks,
        id="product-name",
        label="Product name",
        status="pass" if value_present(product_name) else "fail",
        weight=6,
        evidence=f"Structured name: {str(product_name)[:220]}" if value_present(product_name) else "Product.name is missing.",
        why="The product needs a stable human-readable identity.",
        repair="Populate Product.name from the catalog title used on the page.",
    )

    images = product.get("image") if product else None
    add_check(
        checks,
        id="product-image",
        label="Product image",
        status="pass" if value_present(images) else "warning",
        weight=5,
        evidence=f"Image value present: {str(first_value(images))[:220]}" if value_present(images) else "Product.image is missing.",
        why="Images are central to product understanding and result presentation.",
        repair="Expose one or more absolute product image URLs in Product.image.",
    )

    description = product.get("description") if product else None
    add_check(
        checks,
        id="product-description",
        label="Product description",
        status="pass" if value_present(description) else "warning",
        weight=4,
        evidence=f"Structured description length: {len(str(description))}" if value_present(description) else "Product.description is missing.",
        why="A concise factual description reduces ambiguity.",
        repair="Add a product-specific description that matches the visible page.",
    )

    identifiers = []
    if product:
        identifiers = [
            product.get(key)
            for key in ("sku", "gtin", "gtin8", "gtin12", "gtin13", "gtin14", "mpn")
            if value_present(product.get(key))
        ]
    add_check(
        checks,
        id="identifiers",
        label="SKU or global identifier",
        status="pass" if identifiers else "warning",
        weight=7,
        evidence=f"Found {len(identifiers)} identifier value(s)." if identifiers else "No SKU, GTIN, or MPN found on the Product object.",
        why="Stable identifiers help systems reconcile the same item across pages and feeds.",
        repair="Add the real SKU and, when applicable, GTIN or MPN. Do not invent identifiers.",
    )

    brand = product.get("brand") if product else None
    add_check(
        checks,
        id="brand",
        label="Brand",
        status="pass" if value_present(brand) else "warning",
        weight=4,
        evidence=f"Brand: {str(first_value(brand))[:160]}" if value_present(brand) else "Product.brand is missing.",
        why="Brand is a common product identity and comparison attribute.",
        repair="Expose the true product brand as text or a Brand object.",
    )

    add_check(
        checks,
        id="offer-object",
        label="Offer data",
        status="pass" if offer else "fail",
        weight=12,
        evidence=f"{len(offers)} offer object(s) found." if offer else "Product.offers is missing.",
        why="Price and availability need an explicit purchasable offer.",
        repair="Attach an Offer or AggregateOffer built from the live purchasable state.",
    )

    price = offer.get("price") if offer else None
    if not value_present(price) and offer:
        price = offer.get("lowPrice")
    add_check(
        checks,
        id="price",
        label="Offer price",
        status="pass" if value_present(price) else "fail",
        weight=10,
        evidence=f"Structured price: {price}" if value_present(price) else "Offer price/lowPrice is missing.",
        why="Price is a core purchase fact and must be verified against the storefront.",
        repair="Populate Offer.price from the current sell price and verify sale states.",
    )

    currency = offer.get("priceCurrency") if offer else None
    add_check(
        checks,
        id="currency",
        label="Price currency",
        status="pass" if value_present(currency) else "fail",
        weight=8,
        evidence=f"Structured currency: {currency}" if value_present(currency) else "Offer.priceCurrency is missing.",
        why="A number without currency is not a complete commercial price.",
        repair="Set an ISO 4217 currency code that matches the active storefront.",
    )

    availability = offer.get("availability") if offer else None
    add_check(
        checks,
        id="availability",
        label="Availability",
        status="pass" if value_present(availability) else "fail",
        weight=10,
        evidence=f"Structured availability: {str(availability)[:220]}" if value_present(availability) else "Offer.availability is missing.",
        why="Stock state changes whether a product can be purchased.",
        repair="Generate availability from the selected purchasable variant, then verify it against the live page.",
    )

    add_check(
        checks,
        id="canonical",
        label="Canonical URL",
        status="pass" if value_present(parser.canonical) else "warning",
        weight=4,
        evidence=f"Canonical: {parser.canonical}" if parser.canonical else "No canonical link found.",
        why="A stable canonical URL helps consolidate product identity.",
        repair="Add a self-referential canonical URL for the preferred product page.",
    )
    add_check(
        checks,
        id="visible-heading",
        label="Visible product heading",
        status="pass" if value_present(parser.h1) else "warning",
        weight=3,
        evidence=f"H1: {parser.h1[:220]}" if parser.h1 else "No H1 found.",
        why="The visible page should clearly identify the product.",
        repair="Use one descriptive product H1 that agrees with the structured name.",
    )
    add_check(
        checks,
        id="meta-description",
        label="Meta description",
        status="pass" if value_present(parser.meta_description) else "warning",
        weight=2,
        evidence=f"Meta description length: {len(parser.meta_description)}" if parser.meta_description else "No meta description found.",
        why="A concise summary helps discovery systems understand page purpose.",
        repair="Add a product-specific meta description without unsupported claims.",
    )

    shipping = policy_link_present(parser.links, ("shipping", "delivery", "dispatch"))
    add_check(
        checks,
        id="shipping-policy",
        label="Shipping information is discoverable",
        status="pass" if shipping else "warning",
        weight=3,
        evidence="Found a shipping- or delivery-related link." if shipping else "No obvious shipping or delivery link found.",
        why="Delivery terms affect whether a product is suitable for a shopper.",
        repair="Link clear shipping information from the product journey.",
    )

    returns = policy_link_present(parser.links, ("return", "refund", "exchange"))
    add_check(
        checks,
        id="return-policy",
        label="Returns information is discoverable",
        status="pass" if returns else "warning",
        weight=3,
        evidence="Found a return-, refund-, or exchange-related link." if returns else "No obvious returns or refund link found.",
        why="Return terms are an important purchase constraint.",
        repair="Link a consistent returns policy near the purchase decision.",
    )

    factors = {"pass": PASS_FACTOR, "warning": WARNING_FACTOR, "fail": FAIL_FACTOR}
    max_score = sum(check.weight for check in checks)
    earned = sum(check.weight * factors[check.status] for check in checks)
    score = round((earned / max_score) * 100) if max_score else 0
    counts = {
        status: sum(1 for check in checks if check.status == status)
        for status in ("pass", "warning", "fail")
    }

    return {
        "schema_version": 1,
        "tool": "CommerceLint CLI",
        "promise": "Field presence, parseability, and discoverability screening only.",
        "source": {
            "name": source,
            "bytes": len(markup.encode("utf-8")),
            "sha256": hashlib.sha256(markup.encode("utf-8")).hexdigest(),
        },
        "page": {
            "title": parser.title or product_name or source,
            "canonical": parser.canonical,
        },
        "structured_data": {
            "jsonld_block_count": len(parser.jsonld_blocks),
            "object_count": len(nodes),
            "product_count": product_count,
            "parse_errors": parse_errors,
        },
        "score": score,
        "counts": counts,
        "checks": [asdict(check) for check in checks],
        "limitations": [
            "Does not verify selected-variant state.",
            "Does not compare visible and structured values.",
            "Does not reconcile feeds, checkout, or cross-page policy text.",
            "Does not test live HTTP status, robots directives, or rendered JavaScript.",
            "Does not guarantee indexing, ranking, recommendation, traffic, purchases, or revenue.",
        ],
    }


def markdown_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: dict[str, Any]) -> str:
    title = markdown_escape(report["page"]["title"])
    lines = [
        f"# CommerceLint field coverage report — {title}",
        "",
        f"- **Score:** {report['score']}/100",
        f"- **Pass:** {report['counts']['pass']}",
        f"- **Warnings:** {report['counts']['warning']}",
        f"- **Failures:** {report['counts']['fail']}",
        f"- **Source SHA-256:** `{report['source']['sha256']}`",
        "",
        "| Status | Check | Evidence | Repair |",
        "| --- | --- | --- | --- |",
    ]
    order = {"fail": 0, "warning": 1, "pass": 2}
    for check in sorted(report["checks"], key=lambda item: (order[item["status"]], -item["weight"])):
        lines.append(
            f"| {check['status'].upper()} | {markdown_escape(check['label'])} | "
            f"{markdown_escape(check['evidence'])} | {markdown_escape(check['repair'])} |"
        )
    lines += ["", "## Limitations", ""]
    lines += [f"- {markdown_escape(item)}" for item in report["limitations"]]
    lines += [
        "",
        "CommerceLint reports technical field coverage. Validate all repairs against the live storefront and current platform documentation.",
        "",
    ]
    return "\n".join(lines)


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"CommerceLint field coverage: {report['score']}/100",
        f"pass={report['counts']['pass']} warning={report['counts']['warning']} fail={report['counts']['fail']}",
    ]
    order = {"fail": 0, "warning": 1, "pass": 2}
    for check in sorted(report["checks"], key=lambda item: (order[item["status"]], -item["weight"])):
        lines.append(f"[{check['status'].upper()}] {check['label']}: {check['evidence']}")
    return "\n".join(lines) + "\n"


def read_markup(path_text: str, max_bytes: int) -> tuple[str, str]:
    if max_bytes < 100:
        raise ValueError("--max-bytes must be at least 100.")
    if path_text == "-":
        raw = sys.stdin.buffer.read(max_bytes + 1)
        source = "stdin"
    else:
        path = Path(path_text)
        if not path.is_file():
            raise FileNotFoundError(f"Input file does not exist: {path}")
        if path.stat().st_size > max_bytes:
            raise ValueError(f"Input exceeds --max-bytes ({max_bytes}): {path.stat().st_size} bytes.")
        raw = path.read_bytes()
        source = str(path)
    if len(raw) > max_bytes:
        raise ValueError(f"Input exceeds --max-bytes ({max_bytes}).")
    try:
        return raw.decode("utf-8"), source
    except UnicodeDecodeError as exc:
        raise ValueError("Input must be UTF-8 HTML.") from exc


def exit_for_findings(report: dict[str, Any], *, fail_on: str, min_score: int) -> int:
    if report["score"] < min_score:
        return 1
    if fail_on == "fail" and report["counts"]["fail"] > 0:
        return 1
    if fail_on == "warning" and (report["counts"]["fail"] > 0 or report["counts"]["warning"] > 0):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Screen product-page HTML for commerce field presence and discoverability.",
        epilog="This tool does not prove cross-surface accuracy or guarantee search/agent outcomes.",
    )
    parser.add_argument("input", nargs="?", default="-", help="UTF-8 HTML file, or - for stdin.")
    parser.add_argument("--format", choices=("json", "markdown", "text"), default="json")
    parser.add_argument("--output", help="Write the report to this file instead of stdout.")
    parser.add_argument("--min-score", type=int, default=0, help="Exit 1 when the score is below this value.")
    parser.add_argument(
        "--fail-on",
        choices=("never", "fail", "warning"),
        default="never",
        help="Exit 1 for failed checks, or for warnings and failures.",
    )
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--quiet", action="store_true", help="Suppress the output-file confirmation.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 0 <= args.min_score <= 100:
        parser.error("--min-score must be between 0 and 100.")

    try:
        markup, source = read_markup(args.input, args.max_bytes)
        report = analyze_html(markup, source=source)
    except (OSError, ValueError) as exc:
        print(f"CommerceLint input error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "markdown":
        rendered = render_markdown(report)
    else:
        rendered = render_text(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        if not args.quiet:
            print(f"Wrote CommerceLint report to {output_path}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)

    return exit_for_findings(report, fail_on=args.fail_on, min_score=args.min_score)


if __name__ == "__main__":
    raise SystemExit(main())
