# CommerceLint Decisions

## 2026-08-24 — Continue CommerceLint rather than restart
**Decision:** Consolidate the 90-day business around the existing CommerceLint scanner and audit business rather than fragmenting effort across a second independent launch.

**Why it won:** The product, landing page, scanner, scheduled operator, watchdog, content system, and offer already existed and had passed local and production checks. Current primary-source evidence also supports the underlying need: OpenAI accepts merchant product feeds for shopping discovery, while Google emphasizes accurate Product/Offer/variant data and consistency between pages and feeds. Shopify merchants receive substantial native support, making customized and non-Shopify stores a clearer initial niche.

**Expansion path:** Use structured-catalog remediation—the work initially considered under the SpecRelay concept—as a CommerceLint implementation service when scans expose product data trapped in PDFs, inconsistent attributes, or missing import-ready feeds. This preserves one funnel and one brand while increasing average order value.

**Alternatives rejected for this 90-day test:** generic GEO consulting, accessibility compliance audits, security-questionnaire automation, purchase-order automation, and a separate catalog-conversion brand. They either had weaker differentiation, longer sales cycles, greater liability, or would split the same audience and operating capacity.

Primary references:
- https://openai.com/index/powering-product-discovery-in-chatgpt/
- https://help.openai.com/en/articles/11128490-shopping-with-chatgpt
- https://developers.google.com/search/docs/appearance/structured-data/product
- https://developers.google.com/search/docs/appearance/structured-data/product-variants

## 2026-08-24 — START controls the economic clock
The owner sent `START`. The 90-day clock begins immediately on August 24, 2026 and ends November 21, 2026. The 72-hour burn-in remains a reliability score only.

## 2026-08-24 — Founding offer
Keep the first paid audit at $49 until there is real conversion evidence. The low founding price is designed for speed to first cash, not permanent positioning.

## 2026-08-24 — Evidence standard
Do not sell generic claims that an `llms.txt` file, a score, or a schema change guarantees AI visibility or sales. Every paid finding must identify observed evidence, expected behavior, repair priority, and verification.

## 2026-08-24 — Reinvestment control corrected
After each new verified settled revenue event, one bundled reinvestment cycle may spend no more than 50% of the then-current available cash balance. At least 50% remains untouched. The limit cannot be renewed by splitting purchases, repeatedly spending half of the remainder, using debt, counting pending revenue, or manufacturing transaction events. No revenue or spending occurred before this correction.

## 2026-08-24 — Primandir exclusion
Do not use `primandir.com`, Primandir branding, audiences, infrastructure, CRM contacts, or the Primandir HubSpot portal for CommerceLint. The previously embedded optional HubSpot analytics reference is a scope defect and must be removed from production. Until a separate zero-cost analytics property is available, operate without third-party analytics and rely on verified outreach, replies, scanner evidence shared by prospects, and transaction records.

## 2026-08-24 — Material brand and positioning pivot
**Decision:** Rename the prior business to **CommerceLint** before acquisition.

**Evidence:** Current search results were dominated by an established unrelated machinery marketplace using the prior name. Current competitor research also found several businesses selling broad AI-commerce readiness scans. CommerceLint had no material exact-name search collision in the evidence pass.

**Positioning change:** Keep the working scanner and $49 offer, but focus on developers and agencies who need reproducible product-page defects, exportable evidence, acceptance checks, and repair tickets—not unverifiable ranking promises.

**Reversibility:** Preserve an old-path redirect when production moves. Revenue, traffic, and lead history remain continuous.


## 2026-08-24 — Separate free screening claims from paid verification

- **Decision:** describe the free browser tool as a field-presence and discoverability screen. Reserve selected-variant, visible-versus-structured, cross-page policy, feed, checkout, HTTP, robots, rendered-JavaScript, and full crawlability verification for the paid defect pack.
- **Evidence:** a direct implementation audit found the browser tool checks presence and parseability but does not robustly prove cross-surface accuracy.
- **Reason:** reduce credibility risk before qualified acquisition.


## 2026-08-24 — Add a developer-native distribution surface

- **Decision:** publish a zero-dependency CLI and reusable GitHub Action that mirrors the free browser tool's bounded field-presence promise.
- **Reason:** developers and agencies can adopt a CI check without an account, creating product-led distribution and implementation evidence.
- **Boundary:** selected variants, visible-versus-structured comparisons, policies, feeds, checkout, and live crawlability remain part of the paid defect pack or separately scoped work.

## 2026-08-24 — Consent-gated funnel analytics
**Decision:** Use owner-controlled GA4 measurement ID `G-3TY7EMFMWM` for CommerceLint with explicit opt-in consent, hostname separation, a `cl_` event namespace, and a strict non-content event allowlist.

**Data minimization:** Strip query strings; never send pasted HTML, scanned URLs, scanned page titles, evidence, email addresses, or form contents. Keep advertising storage, Google signals, ad personalization, and ad-user-data consent disabled.

**Reason:** The business needs acquisition and funnel evidence, while scanned commerce content can be sensitive and is unnecessary for aggregate decisions.

## 2026-08-25 — Correct the analytics destination and add a private CRM

**Analytics correction:** The earlier `G-3TY7EMFMWM` value was discovered in another website's public JavaScript; that did not prove it belonged to the connected CommerceLint property. The signed-in GA4 account exposes one property, `Web_App`, whose authoritative measurement ID is `G-MC3PB0Q7EX`. CommerceLint must use the property value, not a scraped public identifier.

**CRM decision:** Use a private Google Sheet for contact email, notes, stages, next actions, activities, and verified payment. Keep only public GitHub references and non-private operational fields in `state/crm.json` so the public repository can automate lead intake without becoming a customer-data store.

**Boundary:** Primandir HubSpot, Primandir contacts, and Primandir infrastructure remain excluded. Gmail-to-Sheets entry is manual until a dedicated credentialed integration can be added without exposing secrets or creating a paid dependency.
