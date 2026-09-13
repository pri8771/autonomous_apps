import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const plans = readFileSync(new URL('../docs/assets/plans.js', import.meta.url), 'utf8');
const inquiry = readFileSync(new URL('../docs/assets/inquiry.js', import.meta.url), 'utf8');
function open(query, valid=true) {
  let submit;
  const elements = {plan:{value:''},requestStatus:{textContent:''},storeUrl:{value:''},details:{value:''},auditRequestForm:{reportValidity:()=>valid,addEventListener:(_,fn)=>submit=fn}};
  const window = {location:{search:query,href:''}};
  const context = vm.createContext({
    window,
    URL,
    URLSearchParams,
    document:{getElementById:id=>elements[id]},
    FormData:class {get(key){return key==='storeUrl' ? 'https://example.com/product' : key==='details' ? 'Check a currency & <value> mismatch' : 'Provided';}},
  });
  vm.runInContext(plans,context);vm.runInContext(inquiry,context);
  return {elements,window,context,submit:()=>submit({preventDefault(){}})};
}
for (const [id,name,price] of [['sample','Sample','1.99'],['lite','Lite','9.99'],['comprehensive','Comprehensive','19.99']]) {
 test(`${name} deep link prepares the correct named inquiry, not an order`,()=>{
  const state=open(`?plan=${id}&price=0.01`);state.submit();
  const url=new URL(state.window.location.href);const body=url.searchParams.get('body');
  assert.equal(url.protocol,'mailto:');assert.equal(url.pathname,'pchordia@unsubscriber.me');
  assert.match(body,new RegExp(`Plan: ${name} — \\$${price.replace('.','\\.')}`));
  assert.match(body,/inquiry, not an order or payment/);assert.match(body,/& <value>/);
  assert.match(body,/Requested public product URLs \(1\)/);
  assert.match(state.elements.requestStatus.textContent,/nothing has been submitted or paid/);
 });
}
test('unknown or prototype query values do not select a purchasable plan',()=>{
 for(const id of ['unexpected','__proto__','constructor']){const state=open(`?plan=${id}`);assert.equal(state.elements.plan.value,'');state.submit();assert.equal(state.window.location.href,'');}
});
test('invalid form cannot compose a request; scanner context survives',()=>{
 const state=open('?plan=lite&score=44&storeUrl=https%3A%2F%2Fexample.com%2Fp',false);state.submit();assert.equal(state.window.location.href,'');assert.match(state.elements.details.value,/44/);assert.equal(state.elements.storeUrl.value,'https://example.com/p');
});
test('changing the selection changes the quoted plan',()=>{
 const state=open('?plan=sample');state.elements.plan.value='comprehensive';state.submit();assert.match(new URL(state.window.location.href).searchParams.get('body'),/Comprehensive — \$19\.99/);
});
test('sample plan rejects more URLs than allowed before composing mailto',()=>{
  let submit;
  const elements = {plan:{value:''},requestStatus:{textContent:''},storeUrl:{value:''},details:{value:''},auditRequestForm:{reportValidity:()=>true,addEventListener:(_,fn)=>submit=fn}};
  const window = {location:{search:'?plan=sample',href:''}};
  const context = vm.createContext({
    window,
    URL,
    URLSearchParams,
    document:{getElementById:id=>elements[id]},
    FormData:class {get(key){
      if (key==='storeUrl') return 'https://example.com/a';
      if (key==='details') return 'https://example.com/b\nhttps://example.com/c';
      return 'Provided';
    }},
  });
  vm.runInContext(plans,context);vm.runInContext(inquiry,context);
  submit({preventDefault(){}});
  assert.equal(window.location.href,'');
  assert.match(elements.requestStatus.textContent,/at most 1 public product URL/);
});
