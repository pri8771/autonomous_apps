# AI-Shopping Readiness Audit

**Client:**  
**Store:**  
**Platform:**  
**Audit date:**  
**Prepared by:**  
**Version:**  

## Executive summary

Summarize the highest-risk commerce defects, the most important implementation opportunity, and the recommended repair sequence. Do not promise indexing, ranking, recommendation, purchase, traffic, or revenue.

## Scope and sampling

- Public surfaces reviewed:
- Product templates reviewed:
- Representative product states reviewed:
  - [ ] In stock
  - [ ] Out of stock
  - [ ] Discounted
  - [ ] Variable product
  - [ ] Multiple images
  - [ ] Category- or template-specific state
- Feeds or exports compared:
- Policies reviewed:
- Explicit exclusions:

## Readiness scorecard

| Dimension | Status | Evidence summary | Highest-priority action |
|---|---|---|---|
| Product identity and identifiers |  |  |  |
| Offer price and currency |  |  |  |
| Availability |  |  |  |
| Variants |  |  |  |
| Canonical and crawlable state |  |  |  |
| Shipping |  |  |  |
| Returns |  |  |  |
| Feed versus storefront consistency |  |  |  |
| Checkout and trust |  |  |  |

## Findings

Repeat this section for every finding.

### MC-001 — Finding title

- **Severity:** Critical / High / Medium / Low
- **Type:** Defect / Opportunity
- **Affected URL:**
- **Product/page state:**
- **Surface:** Visible page / JSON-LD / feed / policy / checkout / other
- **Observed value:**
- **Expected value:**
- **Reproduction steps:**
- **Customer risk:**
- **Distribution risk:**
- **Probable source:**
- **Recommended repair owner:**
- **Recommended repair:**
- **Verification procedure:**
- **Evidence link or attachment:**
- **Status:** Open / In progress / Ready to verify / Verified / Accepted risk

## Prioritized implementation backlog

| Order | Finding ID | Severity | Owner | Repair | Dependency | Verification | Status |
|---:|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |

## Regression checklist

- [ ] Visible title agrees with Product.name.
- [ ] Selected variant has the correct SKU or identifier.
- [ ] Selected variant price agrees across visible page, structured data, feed, cart, and checkout.
- [ ] Currency is explicit and consistent.
- [ ] Selected variant availability agrees across every surface.
- [ ] Canonical URL represents the intended product or variant state.
- [ ] In-stock, out-of-stock, discounted, and variable-product states were retested.
- [ ] Shipping terms are clear and consistent.
- [ ] Return terms are clear and consistent.
- [ ] Feed records were sampled against the live storefront.
- [ ] Corrected JSON-LD parses successfully.
- [ ] No repair introduced a contradictory customer-visible value.

## Assumptions and limitations

Document incomplete access, dynamic rendering, regional or logged-in behavior, feed latency, unavailable checkout states, and any other constraint. This audit is a technical diagnostic and does not guarantee indexing, ranking, recommendation, purchase, traffic, or revenue.

## Sign-off

**Repairs verified by:**  
**Verification date:**  
**Remaining accepted risks:**  
**Next review trigger:** Theme change / catalog migration / feed change / policy change / scheduled review
