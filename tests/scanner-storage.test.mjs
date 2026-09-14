import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('../docs/scanner.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(text => text.includes('function renderReport'));
assert.ok(script, 'Exercise the actual scanner script');
const key = 'commercelint:lastReport';
const atKey = 'commercelint:lastReportAt';
const countKey = 'commercelint:scannerCompletions';
const report = () => ({ generatedAt: '2026-09-12T22:45:00Z', score: 25, page: { title: 'QA page' }, source: { url: null },
  counts: { pass: 0, warning: 0, fail: 1 }, checks: [{ status: 'fail', weight: 5,
    label: 'Offer', why: 'Required', repair: 'Supply evidence', evidence: '<img onerror=alert(1)>' }] });

function browser(initial = {}, failure = null) {
  const values = new Map(Object.entries(initial));
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) {
      const classes = new Set();
      elements.set(id, { textContent: '', innerHTML: '', value: '', events: {},
        classList: { add: x => classes.add(x), remove: x => classes.delete(x),
          toggle: (x, yes) => yes ? classes.add(x) : classes.delete(x), contains: x => classes.has(x) },
        setAttribute() {}, scrollIntoView() {}, addEventListener(type, fn) { this.events[type] = fn; } });
    }
    return elements.get(id);
  };
  const storage = {
    getItem(k) { if (failure === 'all') throw Error('Storage disabled'); return values.get(k) ?? null; },
    setItem(k, v) { if (failure) throw Error('Quota exceeded'); values.set(k, String(v)); },
    removeItem(k) { if (failure) throw Error('Storage disabled'); values.delete(k); }
  };
  const events = [];
  const context = { document: { getElementById: element }, localStorage: storage,
    URLSearchParams, URL, Date, console, window: { location: { search: '' },
      commerceLintTrack: (...args) => events.push(args) } };
  vm.runInNewContext(script.replace('window.analyzeMarkup = analyzeMarkup;',
    'window.testRender = renderReport; window.analyzeMarkup = analyzeMarkup;'), context);
  return { values, element, events, window: context.window };
}

test('restoring saved evidence preserves scan count and original timestamp', () => {
  const b = browser({ [key]: JSON.stringify(report()), [atKey]: '2026-09-01T10:00:00Z', [countKey]: '7' });
  b.element('restoreLastButton').events.click();
  assert.equal(b.values.get(countKey), '7');
  assert.equal(b.values.get(atKey), '2026-09-01T10:00:00Z');
  assert.match(b.element('savedResultHint').textContent, /2026-09-12T22:45:00Z/);
  assert.match(b.element('scannerMessage').textContent, /Restored/);
  assert.equal(b.events.filter(([name]) => name === 'scanner_complete').length, 0);
  assert.ok(!b.element('resultCards').innerHTML.includes('<img'));
  assert.match(b.element('resultCards').innerHTML, /&lt;img/);
});

test('new report is saved and counted exactly once; restore does not count again', () => {
  const b = browser({ [countKey]: '2' });
  assert.equal(b.window.testRender(report()), true);
  assert.equal(b.values.get(countKey), '3');
  assert.equal(b.values.has(atKey), false, 'New results store their timestamp atomically in the report');
  assert.equal(JSON.parse(b.values.get(key)).generatedAt, report().generatedAt);
  b.element('restoreLastButton').events.click();
  assert.equal(b.values.get(countKey), '3');
});

test('malformed and incompatible saved reports do not break scanner initialization', () => {
  for (const raw of ['{', 'null', '{"checks":{}}', JSON.stringify({ ...report(), checks: [null] }),
    JSON.stringify({ ...report(), counts: { fail: -1, pass: 0, warning: 0 } })]) {
    const b = browser({ [key]: raw });
    assert.equal(b.window.restoreLastReport(), null);
    assert.equal(b.element('restoreLastButton').classList.contains('hidden'), true);
  }
});

test('unavailable or full storage keeps rendered results and reports save failure', () => {
  for (const failure of ['all', 'writes']) {
    const b = browser({}, failure);
    assert.equal(b.window.testRender(report()), false);
    assert.equal(b.element('resultTitle').textContent, 'QA page');
    assert.equal(b.values.has(countKey), false);
  }
});

test('clear removes saved evidence without erasing historical scan counts', () => {
  const b = browser({ [key]: JSON.stringify(report()), [atKey]: 'original', [countKey]: '4' });
  b.element('clearLastButton').events.click();
  assert.equal(b.values.has(key), false);
  assert.equal(b.values.has(atKey), false);
  assert.equal(b.values.get(countKey), '4');
  assert.equal(b.element('results').classList.contains('hidden'), true);
});

test('failed clear does not claim that stored evidence was deleted', () => {
  const b = browser({ [key]: JSON.stringify(report()) }, 'writes');
  b.element('clearLastButton').events.click();
  assert.equal(b.values.has(key), true);
  assert.match(b.element('scannerMessage').textContent, /could not clear/);
});
