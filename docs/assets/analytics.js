(() => {
  "use strict";

  const MEASUREMENT_ID = "G-MC3PB0Q7EX";
  const CONSENT_KEY = "commercelint:analyticsConsent:v1";
  const CONSENT_VERSION = "1";
  const EVENT_PREFIX = "cl_";
  const scriptUrl = document.currentScript && document.currentScript.src
    ? new URL(document.currentScript.src, window.location.href)
    : new URL("assets/analytics.js", window.location.href);
  const privacyUrl = new URL("../privacy.html", scriptUrl).href;

  let runtimeConsent = null;
  let analyticsInitialized = false;

  function privacySignalEnabled() {
    return navigator.globalPrivacyControl === true || navigator.doNotTrack === "1" || window.doNotTrack === "1";
  }

  function readConsent() {
    if (privacySignalEnabled()) return "denied";
    try {
      const value = localStorage.getItem(CONSENT_KEY);
      return value === "granted" || value === "denied" ? value : null;
    } catch (_) {
      return runtimeConsent;
    }
  }

  function writeConsent(value) {
    runtimeConsent = value;
    try { localStorage.setItem(CONSENT_KEY, value); } catch (_) {}
  }

  function sanitizedPageLocation() {
    return `${window.location.origin}${window.location.pathname}`;
  }

  function safeCount(value, maximum = 99) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(maximum, Math.round(number)));
  }

  function safeToken(value, fallback = "unknown") {
    const token = String(value ?? "").toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
    return token.slice(0, 40) || fallback;
  }

  function safeEventName(value) {
    const token = String(value ?? "")
      .toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "");
    return token.slice(0, 37) || "event";
  }

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() { window.dataLayer.push(arguments); };

  function baseParameters(extra = {}) {
    return {
      product_name: "CommerceLint",
      event_source: "commercelint_web",
      site_hostname: window.location.hostname,
      page_path: window.location.pathname,
      consent_version: CONSENT_VERSION,
      ...extra,
    };
  }

  function initializeAnalytics() {
    if (analyticsInitialized || readConsent() !== "granted" || privacySignalEnabled()) return false;
    analyticsInitialized = true;

    window.gtag("consent", "default", {
      analytics_storage: "granted",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
    window.gtag("js", new Date());
    window.gtag("config", MEASUREMENT_ID, {
      send_page_view: false,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_prefix: "clga",
      cookie_expires: 15552000,
      page_location: sanitizedPageLocation(),
      page_path: window.location.pathname,
      page_title: document.title,
    });

    const loader = document.createElement("script");
    loader.async = true;
    loader.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(MEASUREMENT_ID)}`;
    loader.referrerPolicy = "strict-origin-when-cross-origin";
    document.head.appendChild(loader);

    window.gtag("event", "page_view", baseParameters({
      page_location: sanitizedPageLocation(),
      page_title: document.title,
    }));
    window.gtag("event", `${EVENT_PREFIX}consent_granted`, baseParameters());
    return true;
  }

  function track(eventName, parameters = {}) {
    if (readConsent() !== "granted" || privacySignalEnabled()) return false;
    initializeAnalytics();
    const normalized = safeEventName(eventName).replace(/^cl_/, "");
    const name = `${EVENT_PREFIX}${normalized}`.slice(0, 40);
    const allowed = {};

    // Deliberately allow only compact, non-content metadata. Never forward HTML,
    // scanned URLs, scanned page titles, evidence, email addresses, or form text.
    const stringFields = [
      "scan_mode", "score_band", "error_category", "cta_kind", "lead_channel",
      "download_kind", "source_surface", "action_ref", "result_band"
    ];
    for (const key of stringFields) {
      if (parameters[key] !== undefined) allowed[key] = safeToken(parameters[key]);
    }
    const countFields = ["missing_count", "warning_count", "pass_count"];
    for (const key of countFields) {
      if (parameters[key] !== undefined) allowed[key] = safeCount(parameters[key]);
    }

    window.gtag("event", name, baseParameters(allowed));
    return true;
  }

  function removeConsentBanner() {
    document.getElementById("commercelintAnalyticsConsent")?.remove();
  }

  function setConsent(value) {
    if (value === "granted" && privacySignalEnabled()) return false;
    if (value !== "granted" && value !== "denied") return false;
    writeConsent(value);
    removeConsentBanner();
    if (value === "granted") initializeAnalytics();
    else if (analyticsInitialized) {
      window.gtag("consent", "update", {
        analytics_storage: "denied",
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied",
      });
    }
    document.dispatchEvent(new CustomEvent("commercelint:analytics-consent", { detail: { value } }));
    return true;
  }

  function resetConsent() {
    runtimeConsent = null;
    try { localStorage.removeItem(CONSENT_KEY); } catch (_) {}
    removeConsentBanner();
    if (!privacySignalEnabled()) showConsentBanner();
  }

  function showConsentBanner() {
    if (readConsent() !== null || privacySignalEnabled() || document.getElementById("commercelintAnalyticsConsent")) return;
    const panel = document.createElement("aside");
    panel.id = "commercelintAnalyticsConsent";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Optional analytics preference");
    panel.style.cssText = "position:fixed;z-index:9999;left:1rem;right:1rem;bottom:1rem;max-width:44rem;margin:auto;padding:1rem 1.1rem;border:1px solid rgba(148,163,184,.45);border-radius:14px;background:#07111f;color:#f8fafc;box-shadow:0 18px 60px rgba(0,0,0,.35);font:500 14px/1.5 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif";
    panel.innerHTML = `
      <strong style="display:block;font-size:1rem;margin-bottom:.25rem">Help improve CommerceLint?</strong>
      <span>Optional Google Analytics records sanitized page paths and broad funnel events. It never receives pasted HTML, scanned URLs, scan evidence, email addresses, or form contents. </span>
      <a href="${privacyUrl}" style="color:#7dd3fc">Privacy details</a>
      <div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.8rem">
        <button type="button" data-cl-consent="granted" style="border:0;border-radius:999px;padding:.65rem 1rem;background:#7dd3fc;color:#07111f;font-weight:800;cursor:pointer">Allow analytics</button>
        <button type="button" data-cl-consent="denied" style="border:1px solid rgba(226,232,240,.45);border-radius:999px;padding:.65rem 1rem;background:transparent;color:#f8fafc;font-weight:700;cursor:pointer">No thanks</button>
      </div>`;
    document.body.appendChild(panel);
  }

  document.addEventListener("click", event => {
    const consentButton = event.target.closest("[data-cl-consent]");
    if (consentButton) {
      setConsent(consentButton.getAttribute("data-cl-consent"));
      return;
    }

    const target = event.target.closest("a,button");
    if (!target) return;
    const rawHref = target instanceof HTMLAnchorElement ? target.getAttribute("href") || "" : "";
    if (/founding-audit\.html/i.test(rawHref)) {
      track("offer_click", { cta_kind: "defect_pack", source_surface: window.location.pathname });
    } else if (/agency\.html/i.test(rawHref)) {
      track("offer_click", { cta_kind: "agency_qa_pack", source_surface: window.location.pathname });
    } else if (/cli\.html/i.test(rawHref)) {
      track("cli_interest", { source_surface: window.location.pathname });
    } else if (/^mailto:/i.test(rawHref)) {
      track("lead_start", { lead_channel: "email", source_surface: window.location.pathname });
    }
  }, { capture: true });

  window.commerceLintTrack = track;
  window.commerceLintSetAnalyticsConsent = setConsent;
  window.commerceLintResetAnalyticsConsent = resetConsent;
  window.commerceLintAnalyticsStatus = () => ({
    consent: readConsent(),
    initialized: analyticsInitialized,
    measurementId: MEASUREMENT_ID,
    privacySignal: privacySignalEnabled(),
  });

  if (readConsent() === "granted") initializeAnalytics();
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", showConsentBanner, { once: true });
  else showConsentBanner();
})();
