(() => {
  const form = document.getElementById('auditRequestForm');
  const status = document.getElementById('requestStatus');
  const plan = document.getElementById('plan');
  const plans = window.commerceLintPlans;
  const params = new URLSearchParams(window.location.search);
  const selected = params.get('plan');
  if (Object.prototype.hasOwnProperty.call(plans, selected)) plan.value = selected;
  if (params.get('storeUrl')) document.getElementById('storeUrl').value = params.get('storeUrl');
  const context = [['score','Scanner score'],['failed','Failed checks'],['warnings','Warnings'],['pageTitle','Scanned page']].filter(([key]) => params.has(key)).map(([key,label]) => `${label}: ${params.get(key)}`).join('\n');
  if (context) document.getElementById('details').value = context;

  function parseRequestedUrls(storeUrl, details) {
    const fromStore = (storeUrl || '').trim();
    const fromDetails = String(details || '')
      .split(/\r?\n|,/)
      .map((part) => part.trim())
      .filter((part) => /^https?:\/\//i.test(part));
    const urls = [];
    const seen = new Set();
    for (const value of [fromStore, ...fromDetails]) {
      if (!value || seen.has(value)) continue;
      seen.add(value);
      urls.push(value);
    }
    return urls;
  }

  function validateUrlsForPlan(planId, urls) {
    if (!Object.prototype.hasOwnProperty.call(plans, planId)) {
      return { ok: false, message: 'Choose one of the listed plans before preparing your request.' };
    }
    const max = plans[planId].maxPublicUrls;
    if (!urls.length) {
      return { ok: false, message: 'Provide at least one public http(s) product URL before requesting a paid plan.' };
    }
    if (urls.length > max) {
      return {
        ok: false,
        message: `${plans[planId].name} allows at most ${max} public product URL(s). Remove extras before continuing. No payment is started from this page.`,
      };
    }
    for (const url of urls) {
      try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
          return { ok: false, message: `Unsupported URL scheme for ${url}. Only public http(s) URLs are accepted.` };
        }
        if (parsed.username || parsed.password) {
          return { ok: false, message: 'URLs containing credentials are not accepted.' };
        }
        const host = (parsed.hostname || '').toLowerCase();
        if (!host || host === 'localhost' || host.endsWith('.local') || host.endsWith('.internal')) {
          return { ok: false, message: `Private or local hostnames are not accepted (${url}).` };
        }
      } catch (error) {
        return { ok: false, message: `Could not parse URL: ${url}` };
      }
    }
    return { ok: true, message: '' };
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!Object.prototype.hasOwnProperty.call(plans, plan.value)) {
      status.textContent = 'Choose one of the listed plans before preparing your request.';
      return;
    }
    const chosen = plans[plan.value];
    const data = new FormData(form);
    const urls = parseRequestedUrls(data.get('storeUrl'), data.get('details'));
    const validation = validateUrlsForPlan(plan.value, urls);
    if (!validation.ok) {
      status.textContent = validation.message;
      return;
    }
    const subject = `CommerceLint ${chosen.name} request`;
    const body = [
      subject,
      `Plan: ${chosen.name} — $${chosen.price} USD (one-time)`,
      `Scope limit: ${chosen.maxPublicUrls} public product URL(s)`,
      `Requested public product URLs (${urls.length}):`,
      ...urls.map((url, index) => `${index + 1}. ${url}`),
      '',
      ...[['contactEmail', 'Contact email'], ['storeUrl', 'Primary store URL'], ['platform', 'Platform'], ['catalogSize', 'Catalog size'], ['mainConcern', 'Main concern'], ['urgency', 'Desired timing'], ['details', 'Context / additional notes']].map(([key, label]) => `${label}: ${data.get(key) || 'Not supplied'}`),
      '',
      `Acquisition source: ${params.get('source') || 'direct'}`,
      `UTM source: ${params.get('utm_source') || 'not supplied'}`,
      `UTM medium: ${params.get('utm_medium') || 'not supplied'}`,
      `UTM campaign: ${params.get('utm_campaign') || 'not supplied'}`,
      '',
      'Client-side URL checks passed for count and public http(s) form. Server intake still revalidates before any charge. This is an inquiry, not an order or payment. Scope, delivery timing and cancellation/refund terms must be agreed before payment. No indexing, recommendation, traffic or sales result is guaranteed.',
    ].join('\n');
    window.commerceLintTrack?.('audit-request-composed');
    status.textContent = 'Opening your email app. Review and send the draft to make your request; nothing has been submitted or paid on this website. If it does not open, email pchordia@unsubscriber.me directly.';
    window.location.href = `mailto:pchordia@unsubscriber.me?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  window.commerceLintInquiry = Object.freeze({ parseRequestedUrls, validateUrlsForPlan });
})();
