import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const script = readFileSync(new URL('../operator/checkout_runtime.js', import.meta.url), 'utf8');
const order = {order_id: 'ord_' + 'a'.repeat(32), report_token: 'b'.repeat(64), checkout_url: 'https://checkout.stripe.com/c/pay/test'};
function open({stored = new Map(), checkout, report, failSet} = {}) {
  const handlers = {}, calls = [], downloads = [];
  const elements = Object.fromEntries(['intake','save','report','restore','status','mode','pay'].map(id => [id, {
    hidden: true, textContent: '', addEventListener: (event, fn) => handlers[id+':'+event] = fn,
    querySelector: () => ({disabled: false}),
  }]));
  const fields = {plan_id:'sample',contact_email:'buyer@example.com',urls:'https://example.com/product'};
  const context = vm.createContext({URL, Blob, TextEncoder, crypto:webcrypto, setTimeout:fn=>fn(),
    document: {getElementById:id=>elements[id],createElement:()=>({click(){downloads.push(this.download);}})},
    sessionStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>{if(failSet?.(k))throw new Error('Storage unavailable');stored.set(k,v);}},
    FormData:class {get(key){return fields[key];}},
    fetch:async(path, options)=>{
      calls.push({path,options});
      const result = path==='/health' ? {mode:'test'} : path==='/inquiry' ? await (checkout?.() ?? order)
        : path==='/report' ? report : {status:'client_receipt_recorded'};
      return {ok:true,json:async()=>result};
    },
  });
  vm.runInContext(script,context);
  return {stored,fields,elements,calls,downloads,submit:()=>handlers['intake:submit']({preventDefault(){},target:elements.intake}),
    check:()=>handlers['report:click'](),save:()=>handlers['save:click']()};
}

test('uncertain checkout and reload retain exact request ID and fields',async()=>{
  let first=true;
  const state=open({checkout:()=>{if(first){first=false;throw new Error('Network lost');}return order;}});
  await state.submit(); await state.submit();
  const calls=state.calls.filter(c=>c.path==='/inquiry');
  assert.equal(calls[0].options.body,calls[1].options.body);
  const restored=open({stored:state.stored}); await restored.submit();
  assert.equal(restored.calls.find(c=>c.path==='/inquiry').options.body,calls[0].options.body);
});

test('changed intake does not silently create another payment',async()=>{
  const state=open(); await state.submit();state.fields.urls='https://example.com/changed';await state.submit();
  assert.equal(state.calls.filter(c=>c.path==='/inquiry').length,1);
  assert.match(state.elements.status.textContent,/Reconcile/);
});

test('report byte verification precedes download and acknowledgement',async()=>{
  const markdown='# CommerceLint test\n<script>untrusted</script>';
  const digest=Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(markdown))),b=>b.toString(16).padStart(2,'0')).join('');
  const state=open({report:{status:'report_available',markdown,artifact_sha256:digest}});
  await state.submit(); await state.check();
  assert.equal(state.downloads.length,1);
  const ack=state.calls.find(c=>c.path==='/acknowledge');
  assert.equal(JSON.parse(ack.options.body).artifact_sha256,digest);
  assert.equal(ack.options.headers.Authorization,'Bearer '+order.report_token);
  assert.match(state.elements.status.textContent,/No email was sent/);
});

test('corrupt report and pending status never claim a download',async()=>{
  for(const report of [{status:'queued'},{status:'report_available',markdown:'bad',artifact_sha256:'a'.repeat(64)}]){
    const state=open({report});await state.submit();await state.check();
    assert.equal(state.downloads.length,0);
    assert.equal(state.calls.filter(c=>c.path==='/acknowledge').length,0);
  }
});

test('private token is only sent in an authorization header',async()=>{
  const state=open({report:{status:'queued'}});await state.submit();await state.check();
  for(const call of state.calls){
    assert.equal(call.path.includes(order.report_token),false);
    assert.equal((call.options?.body||'').includes(order.report_token),false);
  }
  assert.equal(state.elements.pay.href.includes(order.report_token),false);
});

test('access remains saveable if browser storage fills after provider response',async()=>{
  const state=open({failSet:k=>k==='commercelint-private-access'});await state.submit();
  assert.equal(state.elements.save.hidden,false);
  assert.equal(state.elements.report.hidden,false);
  assert.equal(state.elements.pay.href,order.checkout_url);
  state.save();assert.equal(state.downloads[0],'commercelint-private-access.json');
});
