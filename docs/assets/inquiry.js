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
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!Object.prototype.hasOwnProperty.call(plans, plan.value)) { status.textContent = 'Choose one of the listed plans before preparing your request.'; return; }
    const chosen = plans[plan.value];
    const data = new FormData(form);
    const subject = `CommerceLint ${chosen.name} request`;
    const body = [subject, `Plan: ${chosen.name} — $${chosen.price} USD (one-time)`, `Scope limit: ${chosen.maxPublicUrls} public product URL(s)`, '', ...[['contactEmail','Contact email'],['storeUrl','Store URL'],['platform','Platform'],['catalogSize','Catalog size'],['mainConcern','Main concern'],['urgency','Desired timing'],['details','Context / requested URLs']].map(([key,label]) => `${label}: ${data.get(key) || 'Not supplied'}`), '', `Acquisition source: ${params.get('source') || 'direct'}`, `UTM source: ${params.get('utm_source') || 'not supplied'}`, `UTM medium: ${params.get('utm_medium') || 'not supplied'}`, `UTM campaign: ${params.get('utm_campaign') || 'not supplied'}`, '', 'This is an inquiry, not an order or payment. Scope, delivery timing and cancellation/refund terms must be agreed before payment. No indexing, recommendation, traffic or sales result is guaranteed.'].join('\n');
    window.commerceLintTrack?.('audit-request-composed');
    status.textContent = 'Opening your email app. Review and send the draft to make your request; nothing has been submitted or paid on this website. If it does not open, email pchordia@unsubscriber.me directly.';
    window.location.href = `mailto:pchordia@unsubscriber.me?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });
})();
