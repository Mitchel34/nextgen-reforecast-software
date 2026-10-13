/** Synthetic DOM state tests only: no browser, server, input acquisition or models. */
import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

class Node {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.attributes = new Map(); this.listeners = new Map(); this.hidden = false; this._text = ''; this.value = ''; this.disabled = false; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => typeof child === 'string' ? child : child.textContent).join(''); }
  append(...children) { for (const child of children) { this.children.push(child); if (typeof child !== 'string') child.parent = this; } }
  replaceChildren(...children) { this.children = []; this._text = ''; this.append(...children); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  fire(name, event = {}) { return this.listeners.get(name)?.({ preventDefault() {}, ...event }); }
  focus() { globalThis.document.activeElement = this; }
  click() { globalThis.document.clicks.push(this); return this.fire('click'); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
}
class Document {
  constructor() {
    this.nodes = new Map(); this.clicks = []; this.body = new Node('body');
    for (const id of ['study-form', 'review-content', 'review-empty', 'form-error', 'review-title', 'step-define', 'step-review', 'step-save', 'lead-fields', 'max_lead_hours', 'issue-time-fields', 'period-label', 'date-help', 'use-example', 'use-diagnostic-example', 'review']) this.nodes.set(id, new Node());
    this.form = this.nodes.get('study-form');
    const values = { identifier_type: 'usgs', identifier: '03479000', mode: 'reforecast', start_date: '2022-01-01', end_date: '2022-01-02', max_lead_hours: '6', start_hour_utc: '0', end_hour_utc: '23' };
    this.form.elements = {};
    for (const [name, value] of Object.entries(values)) { const field = new Node('input'); field.value = value; this.form.elements[name] = field; }
    this.nodes.set('max_lead_hours', this.form.elements.max_lead_hours);
    this.form.querySelectorAll = () => Object.values(this.form.elements).filter(field => field.attributes.has('aria-invalid'));
  }
  createElement(tag) { return new Node(tag); }
  querySelector(selector) {
    const id = selector.slice(1); if (this.nodes.has(id)) return this.nodes.get(id);
    const walk = node => { if (node.id === id) return node; for (const child of node.children) { if (typeof child === 'string') continue; const found = walk(child); if (found) return found; } };
    return walk(this.nodes.get('review-content')) ?? null;
  }
  querySelectorAll(selector) { return selector === '.steps span' ? ['step-define', 'step-review', 'step-save'].map(id => this.nodes.get(id)) : []; }
}
let document, blobs, descriptors, urlCreate, urlRevoke, sequence = 0, fetchCalls;
const saveGlobal = name => Object.getOwnPropertyDescriptor(globalThis, name);
beforeEach(() => {
  descriptors = Object.fromEntries(['document', 'FormData', 'crypto', 'fetch', 'setTimeout'].map(name => [name, saveGlobal(name)]));
  document = new Document(); blobs = []; fetchCalls = 0;
  globalThis.document = document;
  globalThis.FormData = class { constructor(form) { this.rows = Object.entries(form.elements).filter(([, field]) => !field.disabled).map(([name, field]) => [name, field.value]); } [Symbol.iterator]() { return this.rows[Symbol.iterator](); } };
  globalThis.fetch = () => { fetchCalls += 1; throw new Error('Network is forbidden in these offline UI tests'); };
  globalThis.setTimeout = callback => { queueMicrotask(callback); return 0; };
  urlCreate = URL.createObjectURL; urlRevoke = URL.revokeObjectURL;
  URL.createObjectURL = blob => { blobs.push(blob); return `blob:inert-test-${blobs.length}`; };
  URL.revokeObjectURL = () => {};
});
afterEach(() => {
  assert.equal(fetchCalls, 0);
  for (const [name, descriptor] of Object.entries(descriptors)) Object.defineProperty(globalThis, name, descriptor ?? { value: undefined, configurable: true, writable: true });
  URL.createObjectURL = urlCreate; URL.revokeObjectURL = urlRevoke;
});
const loadApp = () => import(`../app.mjs?offline-test=${++sequence}`);
const text = () => document.querySelector('#review-content').textContent;
function deferredCrypto() {
  const pending = [];
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { subtle: { digest() { return new Promise((resolve, reject) => pending.push({ resolve, reject })); } } } });
  return pending;
}
const finish = entries => entries.forEach(item => item.resolve(new Uint8Array(32).buffer));

test('whole-day UI and assessment download preserve all48 issues without a run action', async () => {
  await loadApp(); await document.form.fire('submit');
  assert.match(text(), /complete request contains 48 hourly issues/);
  assert.match(text(), /No requested issue has been removed/);
  assert.match(text(), /offline planning/);
  document.querySelector('#download-assessment').click();
  const report = JSON.parse(await blobs[0].text());
  assert.equal(report.requested_population.issue_count, 48); assert.equal(report.requested_population.issues_utc.length, 48);
  assert.equal(report.requested_population.generated_rows_per_location, 864);
  assert.equal(report.requested_population.retained_rows_per_location, 288);
  assert.equal(report.requested_request.preview.issue_count, 48); assert.equal(report.execution_ready, false);
  assert.equal(document.querySelector('#run'), null);
});
test('explicit two-issue example removes artificialdayminimum without granting admission', async () => {
  await loadApp(); document.querySelector('#use-diagnostic-example').click(); await document.form.fire('submit');
  assert.match(text(), /complete request contains 2 hourly issues/);
  assert.match(text(), /not verified input preparation or execution authorization/);
  document.querySelector('#download-assessment').click();
  const report = JSON.parse(await blobs[0].text());
  assert.equal(report.diagnostic_profile_match, true); assert.equal(report.requested_population.issues_utc.length, 2);
  assert.equal(report.execution_ready, false);
  document.querySelector('#use-example').click(); await document.form.fire('submit');
  assert.match(text(), /complete request contains 48 hourly issues/);
});
test('continuousmode renders and downloads without manufacturingissues', async () => {
  await loadApp(); document.form.elements.mode.value = 'continuous_simulation'; document.form.fire('change'); await document.form.fire('submit');
  assert.equal(document.querySelector('#form-error').hidden, true); assert.match(text(), /No forecast issue list/);
  document.querySelector('#download-assessment').click();
  const report = JSON.parse(await blobs[0].text()); assert.equal(report.requested_population.issue_count, null); assert.equal(report.planning_supported, false);
});
test('editing during asyncidentity computation discards the old review and download', async () => {
  const pending = deferredCrypto(); await loadApp(); const old = document.form.fire('submit');
  document.form.elements.identifier.value = '03479001'; document.form.fire('input'); finish(pending); await old;
  assert.equal(document.querySelector('#review-content').hidden, true); assert.equal(document.querySelector('#download-assessment'), null);
});
test('late failure from an oldsubmit cannot invalidate a newer exactwindow review', async () => {
  const pending = deferredCrypto(); await loadApp(); const old = document.form.fire('submit'); const first = pending.slice();
  document.querySelector('#use-diagnostic-example').click(); const newer = document.form.fire('submit');
  finish(pending.slice(first.length)); await newer; first[0].reject(new Error('old failure')); finish(first.slice(1)); await old;
  assert.equal(document.querySelector('#form-error').hidden, true); assert.match(text(), /complete request contains 2 hourly issues/);
});
test('stale downloadclosures cannot combine old48report with new2request', async () => {
  await loadApp(); await document.form.fire('submit'); const oldDownload = document.querySelector('#download-assessment');
  document.querySelector('#use-diagnostic-example').click(); await document.form.fire('submit'); oldDownload.click();
  assert.equal(blobs.length, 0); document.querySelector('#download-assessment').click();
  const report = JSON.parse(await blobs[0].text()); assert.equal(report.requested_request.preview.issue_count, 2); assert.equal(report.requested_population.issue_count, 2);
});
test('identity failure leaves no partialreview or downloadable request', async () => {
  const pending = deferredCrypto(); await loadApp(); const submit = document.form.fire('submit'); pending[0].reject(new Error('identity failed')); finish(pending.slice(1)); await submit;
  assert.equal(document.querySelector('#form-error').hidden, false); assert.equal(document.querySelector('#review-content').hidden, true);
  assert.equal(document.querySelector('#download-request'), null);
});
test('oversizedscope is rejected beforehashing or requestdownload', async () => {
  await loadApp(); document.form.elements.start_date.value = '2000-01-01'; document.form.elements.end_date.value = '2020-01-01'; await document.form.fire('submit');
  assert.equal(document.querySelector('#form-error').hidden, false); assert.match(document.querySelector('#form-error').textContent, /exceeds the offline campaign bounds/);
  assert.equal(document.querySelector('#download-assessment'), null);
});
