# CommerceLint agency prospect cohort — 2026-08-25

## Scope

This is the second bounded cohort for `agency-first-pass-v1`. It uses two unused companies from the previously approved five-company research set. No broad list, paid data, Primandir contacts, personal-contact enrichment, CRM write, or outbound message was used.

## Qualified matches

| Company | Why it fits | Current first-party evidence | Public sample screen | Confidence |
| --- | --- | --- | --- | --- |
| Series 5 Technology | WooCommerce-certified agency with ongoing WebOps, custom plugin, migration, store-repair, and QA work | The official Woo directory says it is accepting clients and builds, fixes, and manages WooCommerce stores; the agency's current work page documents an ongoing WooCommerce relationship and custom fulfillment work | One agency-identified client product page returned 29/100: 5 passes, 5 warnings, and 6 failures. The page exposed visible product and price content, but the HTML contained no Product/ProductGroup or Offer JSON-LD object. | High fit; high-confidence public-page observation, but no inference about indexing, variants, feeds, or checkout |
| WPWooDevs | WooCommerce development, white-label delivery, and maintenance are explicit service lines | The agency's current site advertises white-label WordPress delivery and WooCommerce maintenance; its portfolio identifies a live WooCommerce client example | One portfolio product page returned 98/100: 15 passes, 1 warning, and 0 failures. The only bounded warning was that Product.brand was absent. | High fit; strong page result supports a regression-proof angle instead of invented defect urgency |

## Research-to-outreach decision

- Series 5 should receive a factual defect-evidence angle tied to public code only: the sample page lacked Product and Offer JSON-LD despite visible product content. The message must describe CommerceLint as a field-presence screen, not as proof of ranking or selected-variant correctness.
- WPWooDevs should receive a white-label regression angle. The sampled page was mostly strong, so the message must explicitly avoid presenting one missing brand field as a broken store.
- Each proposed message offers a free first pass on one public product URL, capped at three reproducible findings with no credentials or purchase requirement.
- Dedicated source tags were prepared with `utm_source=manual_email`, `utm_medium=outreach`, `utm_campaign=agency_first_pass`, and company-specific `utm_content` values.
- A read-only Gmail search found no prior message to or from either official business contact route.
- Exact contact addresses and message bodies are kept out of this public repository. A private local draft package was prepared separately.

## Evidence boundary

- No message was sent and no external Gmail draft was created.
- Neither company is a lead. A reply, submitted request, or other verified expression of interest is required before lead status changes.
- The CLI does not verify selected variants, visible-versus-structured consistency, feeds, checkout, robots, rendered JavaScript, indexing, recommendation, traffic, or revenue.
- The current economic score remains unchanged.

## Sources and coverage

- **Used:** https://woocommerce.com/development-services/series-5-technology/249313925/ — current certified-partner status, services, client acceptance, and WooCommerce focus.
- **Used:** https://seriesfive.tech/work — current WooCommerce case-study and WebOps evidence.
- **Used:** https://www.wpwoodevs.com/ and https://www.wpwoodevs.com/portfolio — current WooCommerce, maintenance, white-label, and portfolio evidence.
- **Used:** the two public product pages identified by the agencies' own case-study or portfolio material — bounded CommerceLint CLI field-presence results.
- **Unavailable or limited:** no authorized Sales Intelligence provider was used; discovery remains limited to the existing repository-supplied candidate set.
- **Coverage:** exactly two unused candidates from the five-company cohort; this is not exhaustive market coverage.

## Next trigger

The two private drafts are ready for a separate explicit send decision. If approved and sent, label each message `CommerceLint Outreach`, preserve the company-specific source tag, and do not follow up before the current experiment's 2026-08-31 evaluation deadline.
