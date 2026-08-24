# CommerceLint field coverage report — Everyday Linen Shirt

- **Score:** 100/100
- **Pass:** 16
- **Warnings:** 0
- **Failures:** 0
- **Source SHA-256:** `6d8ce211b673e337622c6f63c5e24aacf6677e43872e2b8fe68b5be08890a140`

| Status | Check | Evidence | Repair |
| --- | --- | --- | --- |
| PASS | Product structured data | Found 1 Product/ProductGroup object(s). | Add Product JSON-LD generated from the same catalog data shown to shoppers. |
| PASS | Offer data | 1 offer object(s) found. | Attach an Offer or AggregateOffer built from the live purchasable state. |
| PASS | Offer price | Structured price: 59.00 | Populate Offer.price from the current sell price and verify sale states. |
| PASS | Availability | Structured availability: https://schema.org/InStock | Generate availability from the selected purchasable variant, then verify it against the live page. |
| PASS | Price currency | Structured currency: USD | Set an ISO 4217 currency code that matches the active storefront. |
| PASS | JSON-LD parses cleanly | 3 JSON object(s) parsed from JSON-LD. | Validate every application/ld+json block after theme and app changes. |
| PASS | SKU or global identifier | Found 1 identifier value(s). | Add the real SKU and, when applicable, GTIN or MPN. Do not invent identifiers. |
| PASS | Product name | Structured name: Everyday Linen Shirt | Populate Product.name from the catalog title used on the page. |
| PASS | Product image | Image value present: https://example.com/images/linen-shirt.jpg | Expose one or more absolute product image URLs in Product.image. |
| PASS | Product description | Structured description length: 43 | Add a product-specific description that matches the visible page. |
| PASS | Brand | Brand: Example Goods | Expose the true product brand as text or a Brand object. |
| PASS | Canonical URL | Canonical: https://example.com/products/linen-shirt | Add a self-referential canonical URL for the preferred product page. |
| PASS | Visible product heading | H1: Everyday Linen Shirt | Use one descriptive product H1 that agrees with the structured name. |
| PASS | Shipping information is discoverable | Found a shipping- or delivery-related link. | Link clear shipping information from the product journey. |
| PASS | Returns information is discoverable | Found a return-, refund-, or exchange-related link. | Link a consistent returns policy near the purchase decision. |
| PASS | Meta description | Meta description length: 34 | Add a product-specific meta description without unsupported claims. |

## Limitations

- Does not verify selected-variant state.
- Does not compare visible and structured values.
- Does not reconcile feeds, checkout, or cross-page policy text.
- Does not test live HTTP status, robots directives, or rendered JavaScript.
- Does not guarantee indexing, ranking, recommendation, traffic, purchases, or revenue.

CommerceLint reports technical field coverage. Validate all repairs against the live storefront and current platform documentation.
