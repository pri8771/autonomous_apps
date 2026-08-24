#!/usr/bin/env python3
"""Extend MachineCart's evidence-led content runway beyond 90 days.

The generator is deterministic, idempotent, and intentionally conservative: it
creates platform/topic audit playbooks, not fabricated news or customer claims.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "content" / "queue.json"
STATE_PATH = ROOT / "state" / "catalog_state.json"


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


PLATFORMS = [
    ("woocommerce", "WooCommerce", "WooCommerce merchants and agencies", "Audit theme output, SEO and feed plugins, product extensions, caching, and the selected variable-product state. Treat every plugin that rewrites commerce facts as a separate data owner."),
    ("shopify-custom", "Shopify Custom Themes and Apps", "Shopify merchants with customized storefronts", "Platform defaults do not eliminate theme, app, Markets, bundle, subscription, or headless inconsistencies. Test the customer-visible storefront and every customized purchase state."),
    ("wix-stores", "Wix Stores", "Wix merchants and implementers", "Inspect the published template after app and custom-code changes. Do not assume a platform-generated field remains accurate after catalog customization."),
    ("squarespace-commerce", "Squarespace Commerce", "Squarespace merchants and designers", "Review the live template, product blocks, extensions, and injected code. Preserve evidence from the actual public product journey."),
    ("bigcommerce", "BigCommerce", "BigCommerce teams and agencies", "Sample themes, channels, price lists, customer groups, and variant states. Channel-specific presentation can diverge from the canonical catalog."),
    ("adobe-commerce", "Adobe Commerce", "Adobe Commerce and Magento teams", "Treat store views, configurable products, indexing, themes, extensions, and scheduled catalog rules as independent failure surfaces."),
    ("headless-commerce", "Headless Commerce", "Headless commerce product and engineering teams", "Verify server output, hydration, client state, catalog APIs, feeds, and checkout services as one end-to-end offer rather than isolated systems."),
    ("prestashop", "PrestaShop", "PrestaShop merchants and agencies", "Test theme overrides, modules, combinations, localization, and catalog imports. Module ownership should be documented before repair work begins."),
    ("shopware", "Shopware", "Shopware merchants and solution partners", "Review sales-channel output, variants, rules, extensions, and storefront rendering. A correct administration record is not proof that the public offer is correct."),
    ("salesforce-b2c-commerce", "Salesforce B2C Commerce", "Salesforce B2C Commerce teams", "Sample sites, locales, price books, promotions, variation groups, cartridges, and integrations. Capture evidence at the public storefront and checkout boundary."),
]

TOPICS: list[dict[str, Any]] = [
    {
        "slug": "feed-page-reconciliation",
        "title": "Feed-to-Page Reconciliation Playbook",
        "description": "A repeatable method for finding drift among catalog feeds, public product pages, structured data, and checkout.",
        "keywords": ["merchant feed audit", "catalog data reconciliation", "product page consistency"],
        "sections": [
            ("Choose a representative sample", [
                "Include simple, variable, discounted, unavailable, recently imported, and region-specific products. Record every identifier needed to join the page, feed, and catalog record.",
                "{context}",
            ]),
            ("Compare purchase-critical fields", [
                "Compare title, canonical URL, SKU or GTIN, selected attributes, image, price, currency, availability, and destination eligibility. Keep the raw value from each surface rather than recording only pass or fail.",
            ]),
            ("Classify the source of drift", [
                "Separate stale exports, delayed synchronization, transformation rules, theme rendering, localization, and checkout calculation. Assign one authoritative owner to each field.",
            ]),
            ("Verify the repair over time", [
                "Repeat the same fixtures after catalog imports, releases, promotion changes, and scheduled jobs. Monitor the fields most likely to become stale rather than rerunning an unprioritized crawl.",
            ]),
        ],
        "sources": [
            ("Schema.org Product", "https://schema.org/Product"),
            ("Google product structured data", "https://developers.google.com/search/docs/appearance/structured-data/product"),
        ],
    },
    {
        "slug": "crawlability-canonical-identity",
        "title": "Crawlability and Canonical Identity Audit",
        "description": "Check whether public product states can be discovered, revisited, and consolidated without contradictory URLs.",
        "keywords": ["ecommerce crawlability", "product canonical URL", "duplicate product pages"],
        "sections": [
            ("Map every product URL state", [
                "List canonical product URLs, parameterized variants, filtered collection routes, regional paths, preview links, and legacy redirects. Decide which URLs are indexable and which are only navigation states.",
                "{context}",
            ]),
            ("Compare declared and observed identity", [
                "Check canonical links, redirects, internal links, sitemaps, Product.url, Offer.url, and shareable selected-variant states. A canonical tag cannot repair a checkout link that points to a different product state.",
            ]),
            ("Inspect blocking and rendering", [
                "Review robots rules, meta directives, authentication, JavaScript-only facts, error responses, and content that appears only after interaction. Essential purchase facts should be available in a stable public response when practical.",
            ]),
            ("Retest after routing changes", [
                "Keep fixtures for old URLs, locale switches, removed products, and variant parameters. Verify status codes and final canonical identity after every routing or platform migration.",
            ]),
        ],
        "sources": [
            ("Google canonical guidance", "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"),
            ("Google robots meta guidance", "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag"),
        ],
    },
    {
        "slug": "identifier-deduplication",
        "title": "Product Identifier and Deduplication Audit",
        "description": "Reconcile SKU, GTIN, MPN, brand, parent-child relationships, and duplicate catalog records.",
        "keywords": ["GTIN audit", "SKU deduplication", "product identity quality"],
        "sections": [
            ("Inventory the identifiers you actually own", [
                "Record SKU, GTIN, MPN, brand, supplier identifier, parent product, child variant, and channel-specific IDs. Mark legitimate absence explicitly and never create a placeholder that looks real.",
                "{context}",
            ]),
            ("Find collisions and fragmentation", [
                "Search for duplicate SKUs, one GTIN assigned to multiple products, variants sharing a parent identifier incorrectly, and the same item split across imported records.",
            ]),
            ("Compare every exposed surface", [
                "Check visible pages, structured data, feeds, internal APIs, exports, and checkout line items. Identity should survive the entire purchase path.",
            ]),
            ("Create durable reconciliation rules", [
                "Document matching precedence, merge rules, retired identifiers, and exception handling. Add tests before the next supplier or catalog migration.",
            ]),
        ],
        "sources": [
            ("Schema.org Product identifiers", "https://schema.org/Product"),
            ("Schema.org GTIN", "https://schema.org/gtin"),
        ],
    },
    {
        "slug": "image-media-readiness",
        "title": "Product Image and Media Readiness Audit",
        "description": "Evaluate whether product media correctly represents the selected item and remains usable across discovery surfaces.",
        "keywords": ["product image audit", "ecommerce media quality", "variant image consistency"],
        "sections": [
            ("Connect media to the purchasable state", [
                "For each fixture, record the primary image, gallery, selected-variant image, alt text, dimensions, URL, and any video or 3D asset. The selected item should not inherit misleading parent media.",
                "{context}",
            ]),
            ("Check access and stability", [
                "Verify absolute public URLs, successful responses, suitable formats, stable caching behavior, and the absence of session-bound or temporary asset links.",
            ]),
            ("Compare visible and structured media", [
                "Check Product.image, social metadata, feeds, page galleries, and variant selection. Flag broken, duplicate, low-resolution, or inconsistent assets with the affected URL.",
            ]),
            ("Retest transformation pipelines", [
                "Include image CDN changes, crop presets, imports, lazy loading, and responsive sources in release checks. Preserve at least one fixture for each media path.",
            ]),
        ],
        "sources": [
            ("Schema.org ImageObject", "https://schema.org/ImageObject"),
            ("Google image guidance", "https://developers.google.com/search/docs/appearance/google-images"),
        ],
    },
    {
        "slug": "international-market-consistency",
        "title": "International Market Consistency Audit",
        "description": "Test locale, currency, price, availability, URL, policy, and fulfillment behavior across markets.",
        "keywords": ["international ecommerce audit", "multi currency product data", "regional storefront consistency"],
        "sections": [
            ("Define the market matrix", [
                "List supported countries, languages, currencies, tax modes, price sources, fulfillment restrictions, domains or paths, and fallback behavior. Select fixtures that differ materially by market.",
                "{context}",
            ]),
            ("Verify the complete localized offer", [
                "Compare visible price, priceCurrency, availability, selected variant, shipping eligibility, return terms, canonical URL, and language signals. A translated title with the wrong commercial offer is not a valid localized page.",
            ]),
            ("Exercise switching and direct entry", [
                "Test locale selectors, geolocation fallbacks, cookies, clean sessions, shared links, and direct visits from another market. Record whether the shopper can reproduce the same offer.",
            ]),
            ("Monitor cross-market drift", [
                "Repeat the matrix after price-list, tax, translation, logistics, and catalog changes. Prioritize contradictions that affect eligibility or total purchase cost.",
            ]),
        ],
        "sources": [
            ("Google multi-regional site guidance", "https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites"),
            ("Schema.org Offer", "https://schema.org/Offer"),
        ],
    },
    {
        "slug": "promotion-lifecycle",
        "title": "Promotion and Sale Lifecycle Audit",
        "description": "Find stale or contradictory sale pricing before, during, and after scheduled promotions.",
        "keywords": ["sale price audit", "ecommerce promotion testing", "Offer price validity"],
        "sections": [
            ("Map the price calculation chain", [
                "Document base price, sale rules, coupons, bundles, subscriptions, customer groups, regions, taxes, and checkout adjustments. Identify where each value becomes final.",
                "{context}",
            ]),
            ("Test transition boundaries", [
                "Capture fixtures before launch, at activation, during the promotion, at expiration, and after cache or feed refresh. Include time zones and scheduled-job delays.",
            ]),
            ("Compare every published offer", [
                "Check visible price, strike-through price, structured data, feed, cart, checkout, email or ad destination, and selected variants. Flag any surface that retains an expired value.",
            ]),
            ("Add rollback and expiration checks", [
                "Define the expected post-promotion state and verify it automatically. A successful launch is incomplete if expiration leaves stale sale data behind.",
            ]),
        ],
        "sources": [
            ("Schema.org Offer", "https://schema.org/Offer"),
            ("Google product structured data", "https://developers.google.com/search/docs/appearance/structured-data/product"),
        ],
    },
    {
        "slug": "checkout-trust-signals",
        "title": "Checkout Trust and Policy Consistency Audit",
        "description": "Connect product promises with shipping, returns, support, payment, and final checkout behavior.",
        "keywords": ["checkout trust audit", "return policy consistency", "ecommerce purchase clarity"],
        "sections": [
            ("List the promises made before checkout", [
                "Record shipping estimates, thresholds, return window, exclusions, warranty, payment methods, taxes, recurring terms, contact routes, and destination restrictions shown on the product journey.",
                "{context}",
            ]),
            ("Compare policy and transaction surfaces", [
                "Check product pages, cart, checkout, FAQ, legal policies, confirmation messages, and structured data. Treat conflicting terms as defects even when each page is individually well written.",
            ]),
            ("Exercise failure and edge paths", [
                "Test unavailable destinations, declined methods, out-of-stock changes, subscription cancellation terms, returns exclusions, and support links. The failure state should explain what the buyer can do next.",
            ]),
            ("Verify ownership and freshness", [
                "Assign each promise to a source system and review date. Re-run the fixtures after logistics, payment, policy, or checkout releases.",
            ]),
        ],
        "sources": [
            ("Schema.org MerchantReturnPolicy", "https://schema.org/MerchantReturnPolicy"),
            ("Schema.org OfferShippingDetails", "https://schema.org/OfferShippingDetails"),
        ],
    },
    {
        "slug": "release-regression-monitoring",
        "title": "Commerce Data Release Regression Plan",
        "description": "Build a compact, evidence-backed test set for theme, app, catalog, feed, and checkout releases.",
        "keywords": ["ecommerce regression testing", "catalog monitoring", "structured data release checks"],
        "sections": [
            ("Build a small high-value fixture catalog", [
                "Select products that exercise simple, variable, sale, unavailable, localized, restricted, and recently imported states. Keep stable identifiers and expected values for each fixture.",
                "{context}",
            ]),
            ("Define checks at every boundary", [
                "Verify server response, rendered page, structured data, feed record, cart, checkout, policy links, status codes, and selected-variant behavior. Record raw evidence so failures can be reproduced.",
            ]),
            ("Run risk-based gates", [
                "Block releases for incorrect identity, price, currency, availability, or checkout eligibility. Report lower-severity completeness issues without hiding the critical failures.",
            ]),
            ("Learn from production defects", [
                "Every escaped defect should add or improve a fixture, ownership rule, or verification step. Remove redundant checks only when evidence shows they no longer detect meaningful risk.",
            ]),
        ],
        "sources": [
            ("Schema.org Product", "https://schema.org/Product"),
            ("Google product structured data", "https://developers.google.com/search/docs/appearance/structured-data/product"),
        ],
    },
]


def item_for(platform: tuple[str, str, str, str], topic: dict[str, Any], priority: int) -> dict[str, Any]:
    platform_slug, platform_name, audience, context = platform
    sections = [
        {"heading": heading, "paragraphs": [paragraph.format(context=context) for paragraph in paragraphs]}
        for heading, paragraphs in topic["sections"]
    ]
    return {
        "id": f"{platform_slug}-{topic['slug']}",
        "slug": f"{platform_slug}-{topic['slug']}",
        "title": f"{platform_name} {topic['title']}",
        "description": topic["description"],
        "audience": audience,
        "status": "queued",
        "priority": priority,
        "keywords": [platform_name, *topic["keywords"]],
        "sections": sections,
        "sources": [{"label": label, "url": url} for label, url in topic["sources"]],
        "planned_by": "ninety-day-content-expander-v1",
    }


def main() -> int:
    content = load(CONTENT_PATH, {"schema_version": 1, "items": []})
    state = load(STATE_PATH, {"schema_version": 1, "total_runs": 0, "history": []})
    existing = {entry.get("id") for entry in content.setdefault("items", [])}
    added = 0
    priority = 34
    for platform in PLATFORMS:
        for topic in TOPICS:
            candidate = item_for(platform, topic, priority)
            priority = max(priority - 1, 20)
            if candidate["id"] in existing:
                continue
            content["items"].append(candidate)
            existing.add(candidate["id"])
            added += 1

    queued = sum(entry.get("status") == "queued" for entry in content["items"])
    published = sum(entry.get("status") == "published" for entry in content["items"])
    at = timestamp()
    state["total_runs"] = int(state.get("total_runs", 0)) + 1
    state["last_run_at_utc"] = at
    state["catalog"] = {
        "platforms": len(PLATFORMS),
        "topics": len(TOPICS),
        "matrix_capacity": len(PLATFORMS) * len(TOPICS),
        "added_this_run": added,
        "queued_total": queued,
        "published_total": published,
        "estimated_runway_days_at_one_guide_per_day": queued,
    }
    state.setdefault("history", []).append({"at_utc": at, "added": added, "queued": queued, "published": published})
    state["history"] = state["history"][-52:]
    write(CONTENT_PATH, content)
    write(STATE_PATH, state)
    print(json.dumps(state["catalog"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
