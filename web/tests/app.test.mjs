/** Synthetic DOM state tests only: no browser, server, input acquisition or models. */
import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { buildRequest } from '../request.mjs';
import { preparationReport, residentAdapterReport } from './preparation-report-fixture.mjs';

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
const currentRequest = () => buildRequest(Object.fromEntries(Object.entries(document.form.elements).map(([name, field]) => [name, field.value])));
async function importReport(report) {
  const input = document.querySelector('#preparation-file'); const bytes = JSON.stringify(report);
  input.files = [{ size: new TextEncoder().encode(bytes).byteLength, text: async () => bytes }];
  await input.fire('change');
}

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
test('imported report shows complete population declared outcomes actionable blockers and safe text', async () => {
  await loadApp(); document.form.elements.end_date.value = '2022-12-31'; await document.form.fire('submit');
  const report = preparationReport(currentRequest(), { statuses: { source_coverage: 'failed', location_resolution: 'missing' }, detail: '<img src=x onerror=alert(1)> Synthetic failure only.' });
  await importReport(report);
  assert.match(text(), /preserves all 8,760 requested hourly issues/);
  assert.match(text(), /Effective status: failed/); assert.match(text(), /Effective status: missing/);
  assert.match(text(), /Next step: Check initialization\/history/);
  assert.match(text(), /<img src=x onerror=alert\(1\)>/);
  assert.match(text(), /Execution remains blocked/); assert.equal(document.querySelector('#run'), null);
  document.querySelector('#download-preparation-report').click();
  assert.deepEqual(JSON.parse(await blobs[0].text()), report);
});
test('actual bounded adapter report renders its measured outcome and unresolved qualification', async () => {
  const fixture = residentAdapterReport();
  await loadApp(); document.form.elements.end_date.value = '2022-01-01'; document.form.elements.start_hour_utc.value = '1'; document.form.elements.end_hour_utc.value = '2'; await document.form.fire('submit');
  await importReport(fixture.report);
  assert.match(text(), /preserves all 2 requested hourly issues/);
  // A concurrent filesystem metadata change can correctly make the guarded
  // adapter refuse a complete-content claim. Display its actual bound outcome,
  // rather than assuming the host left newly created temporary files stable.
  assert.ok(text().includes(fixture.report.checks[2].evidence.detail));
  if (fixture.adapter_evidence.validations.length) assert.match(text(), /source_availability_unknown/);
  assert.match(text(), /Effective status: failed/); assert.match(text(), /Execution remains blocked/);
  document.querySelector('#download-preparation-report').click();
  assert.deepEqual(JSON.parse(await blobs[0].text()), fixture.report);
});
test('new selection invalidates the old imported-report download even when replacement fails', async () => {
  await loadApp(); await document.form.fire('submit'); await importReport(preparationReport(currentRequest()));
  const oldDownload = document.querySelector('#download-preparation-report');
  const input = document.querySelector('#preparation-file'); input.files = [{ size: 1, text: async () => '{' }]; await input.fire('change');
  oldDownload.click(); assert.equal(blobs.length, 0); assert.equal(document.querySelector('#download-preparation-report'), null);
  assert.match(document.querySelector('#preparation-import-status').textContent, /Report not imported/);
});
test('edits mode changes and new assessments invalidate imported reports and detached downloads', async () => {
  await loadApp(); await document.form.fire('submit'); await importReport(preparationReport(currentRequest()));
  const edited = document.querySelector('#download-preparation-report'); document.form.elements.identifier.value = '03479001'; document.form.fire('input'); edited.click();
  assert.equal(blobs.length, 0); assert.equal(document.querySelector('#preparation-file'), null);
  await document.form.fire('submit'); await importReport(preparationReport(currentRequest()));
  const modeChanged = document.querySelector('#download-preparation-report'); document.form.elements.mode.value = 'continuous_simulation'; document.form.fire('change'); modeChanged.click();
  assert.equal(blobs.length, 0);
  await document.form.fire('submit'); await importReport(preparationReport(currentRequest()));
  const assessedAgain = document.querySelector('#download-preparation-report'); await document.form.fire('submit'); assessedAgain.click();
  assert.equal(blobs.length, 0); assert.equal(document.querySelector('#download-preparation-report'), null);
});
test('late file reads cannot restore a report after request editing or replace a newer import', async () => {
  await loadApp(); await document.form.fire('submit'); const report = preparationReport(currentRequest());
  let release;
  const oldInput = document.querySelector('#preparation-file'); oldInput.files = [{ size: 1, text: () => new Promise(resolve => { release = resolve; }) }];
  const oldImport = oldInput.fire('change'); document.form.fire('input'); release(JSON.stringify(report)); await oldImport;
  assert.equal(document.querySelector('#download-preparation-report'), null);
  await document.form.fire('submit'); const input = document.querySelector('#preparation-file'); input.files = [{ size: 1, text: () => new Promise(resolve => { release = resolve; }) }];
  const firstImport = input.fire('change'); const newer = preparationReport(currentRequest(), { statuses: { source_coverage: 'missing' } }); await importReport(newer);
  release(JSON.stringify(report)); await firstImport; document.querySelector('#download-preparation-report').click();
  assert.deepEqual(JSON.parse(await blobs[0].text()), newer);
});
test('late hash computation cannot restore an imported report after a mode change', async () => {
  await loadApp(); await document.form.fire('submit'); const report = preparationReport(currentRequest());
  const pending = deferredCrypto(); const task = importReport(report);
  // Let File.text resolve and reach the first identity computation.
  await Promise.resolve(); await Promise.resolve();
  document.form.elements.mode.value = 'continuous_simulation'; document.form.fire('change');
  finish(pending); await task;
  assert.equal(document.querySelector('#download-preparation-report'), null);
});
test('oversized file is refused without reading it and failed report leaves request download intact', async () => {
  await loadApp(); await document.form.fire('submit'); let reads = 0;
  const input = document.querySelector('#preparation-file'); input.files = [{ size: 8 * 1024 * 1024 + 1, text: async () => { reads += 1; return '{}'; } }]; await input.fire('change');
  assert.equal(reads, 0); assert.match(document.querySelector('#preparation-import-status').textContent, /at most 8 MiB/);
  await importReport(preparationReport(buildRequest({ identifier_type: 'usgs', identifier: '03479001', mode: 'reforecast', start_date: '2022-01-01', end_date: '2022-01-02', max_lead_hours: 6 })));
  assert.equal(document.querySelector('#download-preparation-report'), null);
  assert.match(document.querySelector('#preparation-import-status').textContent, /another study request/);
  document.querySelector('#download-request').click(); assert.equal(blobs.length, 1);
});
