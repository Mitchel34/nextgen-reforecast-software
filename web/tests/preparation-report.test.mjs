/** Bounded imported-report contract tests; synthetic checks, zero forecast runs. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { buildRequest } from '../request.mjs';
import { MAX_PREPARATION_REPORT_BYTES, PREPARATION_POLICY_BYTES_SHA256, validatePreparationReport } from '../preparation-report.mjs';
import { preparationReport, residentAdapterReport, resignReport } from './preparation-report-fixture.mjs';

const request = (overrides = {}) => buildRequest({ identifier_type: 'usgs', identifier: '03479000', mode: 'reforecast', start_date: '2022-01-01', end_date: '2022-01-02', max_lead_hours: 6, ...overrides });
const checkIds = ['location_resolution', 'initialization', 'source_coverage', 'input_bundle', 'runtime_identity', 'reference_set', 'scientific_profile'];
const allPassed = Object.fromEntries(checkIds.map(check => [check, 'passed']));
const rejects = (report, current, code) => assert.rejects(validatePreparationReport(JSON.stringify(report), current), error => error.code === code);

test('import policy byte pin matches browser and packaged backend policy without fetching', () => {
  for (const path of ['../request-policy.json', '../../src/ngen_reforecast/preparation/request-policy.json']) {
    const bytes = readFileSync(new URL(path, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), PREPARATION_POLICY_BYTES_SHA256);
  }
});
test('complete twelve-month backend report validates and remains immutable and blocked', async () => {
  const current = request({ identifier_type: 'watershed', identifier: 'Synthetic Ω watershed 🏞️', end_date: '2022-12-31' });
  const backend = preparationReport(current, { statuses: allPassed });
  const report = await validatePreparationReport(JSON.stringify(backend), current);
  assert.equal(report.requested_population.issues_utc.length, 8760);
  assert.equal(report.requested_population.preview.generated_rows_per_location, 157680);
  assert.equal(report.requested_population.preview.retained_rows_per_location, 52560);
  assert.deepEqual(report.preparation_binding.scope.required_source_leads, { min: 1, max: 18 });
  assert.equal(report.preparation_checks_status, 'all_reported_passed'); assert.equal(report.execution_ready, false); assert.equal(report.release_qualified, false);
  assert.deepEqual(report.blockers.map(item => item.code), ['CAMPAIGN_PROTOCOL_NOT_ADMITTED', 'EXECUTION_SERVICE_UNAVAILABLE']);
  assert.equal(Object.isFrozen(report.checks[0].evidence), true);
});
test('maximum supported issue population fits the import bound without shortening scope', async () => {
  const last = new Date(Date.parse('2022-01-01T00:00:00Z') + (99982 - 1) * 3_600_000);
  const current = request({ end_date: last.toISOString().slice(0, 10), end_hour_utc: last.getUTCHours() });
  const backend = preparationReport(current);
  const text = JSON.stringify(backend); assert.ok(new TextEncoder().encode(text).byteLength < MAX_PREPARATION_REPORT_BYTES);
  const report = await validatePreparationReport(text, current);
  assert.equal(report.requested_population.issues_utc.length, 99982);
  assert.equal(report.preparation_binding.scope.issue_count, 99982);
});
test('escaped lone code units preserve existing cross-runtime request and evidence identities', async () => {
  const current = request({ identifier_type: 'watershed', identifier: 'Synthetic \ud800 watershed' });
  const backend = preparationReport(current, { statuses: { source_coverage: 'failed' }, detail: 'Synthetic escaped code unit \ud800 only.' });
  const report = await validatePreparationReport(JSON.stringify(backend), current);
  assert.equal(report.requested_request.location.submitted_identifier, 'Synthetic \ud800 watershed');
  assert.equal(report.checks[2].evidence.detail, 'Synthetic escaped code unit \ud800 only.');
});
test('real bounded adapter reads tiny synthetic resident bytes and its unchanged report imports', async () => {
  const { request: current, report: backend, adapter_evidence: evidence } = residentAdapterReport();
  const report = await validatePreparationReport(JSON.stringify(backend), current);
  assert.equal(evidence.decoded_content_valid, true); assert.equal(evidence.checks_performed, 3);
  assert.equal(evidence.source_coverage_qualified, false);
  assert.equal(report.checks[2].status, 'failed');
  assert.match(report.checks[2].evidence.detail, /decoded_content_valid=True/);
  assert.match(report.checks[2].evidence.detail, /source_availability_unknown/);
  assert.equal(report.execution_ready, false); assert.equal(report.requested_population.issues_utc.length, 2);
});
test('unknown missing failed passed and mismatched receipts retain distinct actionable outcomes', async () => {
  const current = request();
  const backend = preparationReport(current, { statuses: { location_resolution: 'missing', source_coverage: 'failed', runtime_identity: 'passed', reference_set: 'passed', scientific_profile: 'unknown' }, mismatch: ['reference_set'] });
  const report = await validatePreparationReport(JSON.stringify(backend), current);
  assert.deepEqual(report.checks.map(item => item.status), ['missing', 'unknown', 'failed', 'unknown', 'passed', 'evidence_mismatch', 'unknown']);
  assert.match(report.blockers.find(item => item.requirement === 'source_coverage').next_option, /full 18-hour forcing window/);
  assert.equal(report.checks[5].reported_status, 'passed');
  assert.equal(report.evidence_boundary.verifier_authenticated, false);
});
test('missing initialization and proposed continuous mode are imported without manufactured scope', async () => {
  const current = request();
  const report = await validatePreparationReport(JSON.stringify(preparationReport(current, { noOrigin: true, statuses: allPassed })), current);
  assert.equal(report.preparation_binding.scope.required_history_interval, null);
  assert.equal(report.preparation_checks_status, 'incomplete'); assert.equal(report.blockers[0].code, 'INITIALIZATION_NOT_SELECTED');
  const continuous = request({ mode: 'continuous_simulation' });
  const proposed = await validatePreparationReport(JSON.stringify(preparationReport(continuous)), continuous);
  assert.equal(proposed.requested_population.issues_utc, null); assert.equal(proposed.blockers[0].code, 'MODE_NOT_IMPLEMENTED');
});
test('another site dates leads or mode cannot reuse a report', async () => {
  const current = request(); const backend = preparationReport(current);
  for (const overrides of [{ identifier: '03479001' }, { end_date: '2022-01-03' }, { max_lead_hours: 18 }, { mode: 'continuous_simulation' }]) await rejects(backend, request(overrides), 'PREPARATION_REQUEST_MISMATCH');
});
test('rehashing forged readiness scope population check or blocker cannot satisfy the contract', async () => {
  const current = request(); const backend = preparationReport(current, { statuses: { source_coverage: 'failed' } });
  for (const change of [
    report => { report.execution_ready = true; },
    report => { report.evidence_boundary.artifacts_read_or_verified = true; },
    report => { report.requested_population.issues_utc.pop(); },
    report => { report.blockers.pop(); },
    report => { report.preparation_checks_status = 'all_reported_passed'; },
  ]) { const forged = structuredClone(backend); change(forged); resignReport(forged); await rejects(forged, current, 'PREPARATION_REPORT_CONTENT_MISMATCH'); }
  const scope = structuredClone(backend); scope.preparation_binding.scope.policy_bytes_sha256 = 'b'.repeat(64); resignReport(scope); await rejects(scope, current, 'PREPARATION_SCOPE_MISMATCH');
  const receipt = structuredClone(backend); receipt.checks[2].evidence.detail = 'Changed declaration'; resignReport(receipt); await rejects(receipt, current, 'PREPARATION_RECEIPT_IDENTITY_MISMATCH');
  const status = structuredClone(backend); status.checks[2].status = 'passed'; resignReport(status); await rejects(status, current, 'INVALID_PREPARATION_REPORT');
});
test('bad digest added fields and unsupported schema fail before any report can be used', async () => {
  const current = request(); const backend = preparationReport(current);
  const digest = structuredClone(backend); digest.identities.report_sha256 = 'b'.repeat(64); await rejects(digest, current, 'PREPARATION_REPORT_IDENTITY_MISMATCH');
  const added = structuredClone(backend); added.adapter_trust = true; resignReport(added); await rejects(added, current, 'INVALID_PREPARATION_REPORT');
  const schema = structuredClone(backend); schema.preparation_result_schema_version = 'preparation-result/9'; await rejects(schema, current, 'INVALID_PREPARATION_REPORT');
  await assert.rejects(validatePreparationReport('{', current), error => error.code === 'INVALID_PREPARATION_REPORT_JSON');
});
test('byte depth and unsafe JSON limits are checked before hashing', async () => {
  const current = request();
  await assert.rejects(validatePreparationReport(' '.repeat(MAX_PREPARATION_REPORT_BYTES + 1), current), error => error.code === 'PREPARATION_REPORT_LIMIT_EXCEEDED');
  await assert.rejects(validatePreparationReport(`${'['.repeat(18)}0${']'.repeat(18)}`, current), error => error.code === 'PREPARATION_REPORT_LIMIT_EXCEEDED');
  await assert.rejects(validatePreparationReport('{"__proto__":{}}', current), error => error.code === 'INVALID_PREPARATION_REPORT');
  await assert.rejects(validatePreparationReport('{"status":"blocked","status":"passed"}', current), error => error.code === 'DUPLICATE_PREPARATION_REPORT_KEY');
  await assert.rejects(validatePreparationReport('{"checks":[{"status":"unknown","\\u0073tatus":"passed"}]}', current), error => error.code === 'DUPLICATE_PREPARATION_REPORT_KEY');
});
test('report hash failure and unavailable Web Crypto leave no partially accepted report', async () => {
  const current = request(); const backend = preparationReport(current);
  const saved = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  try {
    Object.defineProperty(globalThis, 'crypto', { configurable: true, value: undefined });
    await rejects(backend, current, 'PREPARATION_IDENTITY_UNAVAILABLE');
  } finally { Object.defineProperty(globalThis, 'crypto', saved); }
});
