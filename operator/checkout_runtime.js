'use strict';
const byId = id => document.getElementById(id);
const status = message => { byId('status').textContent = message; };
let access = null;
let pending = null;
function showAccess() {
  byId('save').hidden = !access;
  byId('report').hidden = !access;
}
async function post(path, data, token) {
  const response = await fetch(path, {method: 'POST', cache: 'no-store', credentials: 'omit',
    headers: {'Content-Type': 'application/json', ...(token ? {'Authorization': `Bearer ${token}`} : {})},
    body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed. Retry the same checkout.');
  return result;
}
function download(name, value, type) {
  const url = URL.createObjectURL(new Blob([value], {type}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
try {
  access = JSON.parse(sessionStorage.getItem('commercelint-private-access') || 'null');
  pending = JSON.parse(sessionStorage.getItem('commercelint-pending-checkout') || 'null');
} catch { status('Session storage unavailable. Save the private access file before payment.'); }
showAccess();
fetch('/health', {cache: 'no-store'}).then(r => r.json()).then(r => {
  byId('mode').textContent = r.mode === 'test' ? 'Stripe TEST mode. Test activity is not a sale or settled revenue.' : 'Stripe LIVE mode. Continuing to payment can create a real charge.';
}).catch(() => { byId('mode').textContent = 'Service unavailable. Do not start a new checkout.'; });
byId('intake').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.target.querySelector('button'); button.disabled = true;
  try {
    const form = new FormData(event.target);
    const fields = {plan_id: form.get('plan_id'), contact_email: form.get('contact_email').trim(),
      urls: form.get('urls').split('\n').map(s => s.trim()).filter(Boolean)};
    // Retain the exact uncertain request across reloads; changed intake needs a fresh tab after reconciliation.
    if (pending && JSON.stringify(pending.fields) !== JSON.stringify(fields)) throw new Error('A previous checkout exists in this tab. Reconcile it and save its access file before starting a different purchase in a new tab.');
    pending ||= {request_id: crypto.randomUUID(), fields};
    sessionStorage.setItem('commercelint-pending-checkout', JSON.stringify(pending));
    const result = await post('/inquiry', {...pending.fields, request_id: pending.request_id});
    access = {order_id: result.order_id, report_token: result.report_token};
    showAccess();
    try { sessionStorage.setItem('commercelint-private-access', JSON.stringify(access)); }
    catch { /* In-memory access and the save button remain available. */ }
    if (result.checkout_url) {
      const url = new URL(result.checkout_url);
      if (url.origin !== 'https://checkout.stripe.com') throw new Error('Unsupported checkout URL. Contact support.');
      byId('pay').href = url.href; byId('pay').hidden = false;
    }
    status(`Order ${access.order_id}. Save your access file, then continue to Stripe. Keep this tab open for your report.`);
  } catch (error) { status(error.message); } finally { button.disabled = false; }
});
byId('save').addEventListener('click', () => download('commercelint-private-access.json', JSON.stringify(access), 'application/json'));
byId('restore').addEventListener('change', async event => {
  try {
    const file = event.target.files[0];
    if (!file || file.size > 4096) throw new Error('Choose a valid private access file.');
    const data = JSON.parse(await file.text());
    if (!/^ord_[a-f0-9]{32}$/.test(data.order_id) || !/^[a-f0-9]{64}$/.test(data.report_token)) throw new Error('Invalid private access file.');
    access = {order_id: data.order_id, report_token: data.report_token};
    showAccess();
    try { sessionStorage.setItem('commercelint-private-access', JSON.stringify(access)); }
    catch { /* The restored access file remains usable in this tab. */ }
    status('Private access restored. Check for your report.');
  } catch (error) { status(error.message); }
});
byId('report').addEventListener('click', async () => {
  try {
    const report = await post('/report', {order_id: access.order_id}, access.report_token);
    if (report.status !== 'report_available') { status(`Report status: ${report.status}. Try again later or contact support with your order reference.`); return; }
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(report.markdown))), b => b.toString(16).padStart(2, '0')).join('');
    if (digest !== report.artifact_sha256) throw new Error('Report integrity check failed. Contact support.');
    download(`commercelint-${access.order_id}.md`, report.markdown, 'text/markdown;charset=utf-8');
    await post('/acknowledge', {order_id: access.order_id, artifact_sha256: digest}, access.report_token);
    status('Report received by this browser. Your browser started the download; check your downloads folder. No email was sent.');
  } catch (error) { status(error.message); }
});
