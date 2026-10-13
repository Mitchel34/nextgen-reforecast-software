import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { buildRequest, REQUEST_POLICY } from '../request.mjs';
import { assessRequest, evaluateRequest, AssessmentError, ASSESSMENT_SCHEMA_VERSION,
  DIAGNOSTIC_PROFILE_METADATA, MAX_REQUEST_BYTES, MAX_REQUEST_DEPTH, MAX_REQUEST_NODES,
  MAX_ASSESSMENT_ISSUES } from '../assessment.mjs';

const base = { identifier_type: 'usgs', identifier: '03479000', mode: 'reforecast', start_date: '2022-01-01', end_date: '2022-01-02', max_lead_hours: 6 };
const request = changes => buildRequest({ ...base, ...changes });
const codes = report => report.blockers.map(blocker => blocker.code);
function rejected(input, code, field) {
  assert.throws(() => evaluateRequest(input), error => error instanceof AssessmentError && error.code === code && (!field || error.field === field));
}
const clone = value => JSON.parse(JSON.stringify(value));
const reorder = value => Array.isArray(value) ? value.map(reorder) : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).reverse().map(([key, child]) => [key, reorder(child)])) : value;
const sortedJson = value => JSON.stringify(value, function (_key, child) {
  return child && !Array.isArray(child) && typeof child === 'object' ? Object.fromEntries(Object.keys(child).sort().map(key => [key, child[key]])) : child;
});

test('two-day study retains all 48 issues and distinct generated/export populations', () => {
  const input = request(); const report = evaluateRequest(input); const p = report.requested_population;
  assert.equal(report.assessment_schema_version, ASSESSMENT_SCHEMA_VERSION);
  assert.equal(report.status, 'blocked'); assert.equal(report.execution_ready, false); assert.equal(report.release_qualified, false);
  assert.equal(report.planning_supported, true); assert.equal(report.diagnostic_profile_match, false);
  assert.deepEqual(report.requested_request, input); assert.notEqual(report.requested_request, input);
  assert.equal(p.issue_count, 48); assert.equal(p.issues_utc.length, 48);
  assert.equal(p.issues_utc[0], '2022-01-01T00:00:00Z'); assert.equal(p.issues_utc.at(-1), '2022-01-02T23:00:00Z');
  for (let i = 1; i < p.issues_utc.length; i++) assert.equal(Date.parse(p.issues_utc[i]) - Date.parse(p.issues_utc[i - 1]), 3_600_000);
  assert.equal(p.generated_rows_per_location, 864); assert.equal(p.retained_rows_per_location, 288);
  assert.equal(p.horizon_hours, 18); assert.equal(p.retained_leads.projection, 'export');
  assert.equal(p.last_physical_valid_time_utc, '2022-01-03T17:00:00Z');
  assert.equal(report.diagnostic_profile.issue_count, 2); assert.equal(report.diagnostic_profile.generated_rows_per_location, 36);
  assert.equal(report.diagnostic_profile.historical_export_example.retained_rows_per_location, 12);
  assert.equal(report.compatibility.retention.diagnostic_rows_with_requested_projection, 12);
  assert.ok(codes(report).includes('DIAGNOSTIC_SCHEDULE_MISMATCH'));
  assert.ok(codes(report).includes('DIAGNOSTIC_TARGET_OUTSIDE_PREPARED_INTERVAL'));
  assert.equal(report.compatibility.final_target.establishes_source_coverage, false);
});

test('explicit UTC issue hours represent the exact two-issue diagnostic without reducing whole-day requests', () => {
  const input = request({ start_hour_utc: 23, end_hour_utc: 0 }); const report = evaluateRequest(input);
  assert.deepEqual(report.requested_request, input); assert.equal(input.request_schema_version, '0.2');
  assert.deepEqual(report.requested_population.issues_utc, ['2022-01-01T23:00:00Z', '2022-01-02T00:00:00Z']);
  assert.equal(report.requested_population.issue_count, 2); assert.equal(report.requested_population.generated_rows_per_location, 36);
  assert.equal(report.requested_population.retained_rows_per_location, 12); assert.equal(report.requested_population.last_physical_valid_time_utc, '2022-01-02T18:00:00Z');
  assert.equal(report.planning_supported, true); assert.equal(report.diagnostic_profile_match, true);
  assert.equal(report.compatibility.diagnostic_profile_match, true);
  assert.equal(report.compatibility.match_scope, 'declared_issue_clocks_identifier_and_horizon_only');
  assert.equal(report.compatibility.origin_and_history_bound, false); assert.equal(report.compatibility.assets_runtime_reference_verified, false);
  assert.equal(report.compatibility.fresh_execution_authorized, false); assert.equal(report.compatibility.establishes_admission, false);
  assert.equal(report.execution_ready, false); assert.equal(report.release_qualified, false);
  assert.ok(!codes(report).includes('DIAGNOSTIC_SCHEDULE_MISMATCH')); assert.ok(!codes(report).includes('DIAGNOSTIC_TARGET_OUTSIDE_PREPARED_INTERVAL'));
  for (const code of ['LOCATION_NOT_RESOLVED', 'COVERAGE_UNKNOWN', 'INITIALIZATION_NOT_SELECTED', 'SCIENTIFIC_PROFILE_UNQUALIFIED', 'INPUT_BUNDLE_NOT_PREPARED', 'CAMPAIGN_PROTOCOL_NOT_ADMITTED', 'EXECUTION_SERVICE_UNAVAILABLE']) assert.ok(codes(report).includes(code));
  assert.equal(evaluateRequest(request()).requested_population.issue_count, 48);
});

test('a single explicitly chosen hour produces one complete issue and preserves the full horizon', () => {
  const report = evaluateRequest(request({ start_date: '2022-01-02', end_date: '2022-01-02', start_hour_utc: 0, end_hour_utc: 0, max_lead_hours: 1 }));
  assert.equal(report.requested_population.issue_count, 1); assert.deepEqual(report.requested_population.issues_utc, ['2022-01-02T00:00:00Z']);
  assert.equal(report.requested_population.generated_rows_per_location, 18); assert.equal(report.requested_population.retained_rows_per_location, 1);
  assert.equal(report.requested_population.last_physical_valid_time_utc, '2022-01-02T18:00:00Z');
  assert.equal(report.planning_supported, true); assert.equal(report.diagnostic_profile_match, false);
  assert.ok(codes(report).includes('DIAGNOSTIC_SCHEDULE_MISMATCH'));
});

test('exact diagnostic schedule supports every export retention 1–18 without qualifying or shortening integration', () => {
  for (const maximum of [1, 6, 18]) {
    const report = evaluateRequest(request({ start_hour_utc: 23, end_hour_utc: 0, max_lead_hours: maximum }));
    assert.equal(report.diagnostic_profile_match, true); assert.equal(report.requested_population.issue_count, 2);
    assert.equal(report.requested_population.generated_rows_per_location, 36); assert.equal(report.requested_population.retained_rows_per_location, maximum * 2);
    assert.equal(report.requested_population.last_physical_valid_time_utc, '2022-01-02T18:00:00Z');
    assert.equal(report.diagnostic_profile.historical_export_example.retained_rows_per_location, 12);
    assert.equal(report.execution_ready, false);
  }
});

test('one whole day preserves 24 issues rather than taking the overlapping diagnostic hour', () => {
  const report = evaluateRequest(request({ end_date: '2022-01-01' }));
  assert.equal(report.requested_population.issue_count, 24);
  assert.equal(report.requested_population.issues_utc.at(-1), '2022-01-01T23:00:00Z');
  assert.equal(report.compatibility.schedule.matches, false);
  assert.equal(report.compatibility.schedule.request_preserved, true);
  assert.ok(codes(report).includes('DIAGNOSTIC_SCHEDULE_MISMATCH'));
});

test('declared diagnostic clocks, identities and example retention never assert fresh verification', () => {
  const p = DIAGNOSTIC_PROFILE_METADATA;
  assert.equal(p.evidence_class, 'declared_diagnostic_metadata'); assert.equal(p.current_assets_verified, false);
  assert.equal(p.origin_time_utc, '2021-12-01T00:00:00Z'); assert.equal(p.history_stop_time_utc, '2022-01-02T18:00:00Z');
  assert.deepEqual(p.issue_times_utc, ['2022-01-01T23:00:00Z', '2022-01-02T00:00:00Z']);
  assert.equal(p.location.usgs_gauge, '03479000'); assert.equal(p.location.nwm_reach, '1017693'); assert.equal(p.horizon_hours, 18);
  assert.equal(p.release_qualified, false); assert.equal(p.supported_export_retention.max_lead_hours, 18);
  for (const key of ['scientific_configuration_identity_sha256', 'runtime_identity_sha256', 'input_assembly_identity_sha256', 'reference_set_identity_sha256']) assert.match(p[key], /^[a-f0-9]{64}$/);
  assert.throws(() => { p.issue_times_utc.pop(); }, TypeError);
});

test('declared metadata remains exactly bound to the frozen packaged diagnostic profile', async () => {
  const source = JSON.parse(await readFile(new URL('../../src/ngen_reforecast/_profiles/watauga-v2.json', import.meta.url), 'utf8'));
  const declared = DIAGNOSTIC_PROFILE_METADATA;
  const cases = source.protocol.cases;
  const history = cases.find(item => item.case_id === 'history');
  const forecasts = cases.filter(item => item.issue_time_utc !== null);
  assert.equal(declared.origin_time_utc, history.origin_time_utc);
  assert.equal(declared.history_stop_time_utc, history.stop_time_utc_exclusive);
  assert.deepEqual(declared.issue_times_utc, forecasts.map(item => item.issue_time_utc));
  for (const item of forecasts) { assert.equal(item.origin_time_utc, declared.origin_time_utc); assert.equal(item.lead_hours, declared.horizon_hours); }
  assert.equal(declared.location.usgs_gauge, source.protocol.usgs_id);
  assert.equal(`wb-${declared.location.nwm_reach}`, source.protocol.selected_routing_feature_id);
  assert.equal(declared.location.catchment_count, source.protocol.catchment_ids.length);
  assert.equal(declared.scientific_configuration_identity_sha256, source.admission.scientific_configuration_identity_sha256);
  assert.equal(declared.runtime_identity_sha256, source.runtime.runtime_identity_sha256);
  assert.equal(declared.input_assembly_identity_sha256, source.admission.assembly_identity_sha256);
  assert.equal(declared.reference_set_identity_sha256, source.reference_set.reference_set_identity_sha256);
  assert.equal(declared.release_qualified, source.admission.release_qualified);
});

test('retaining leads 1, 6 or 18 leaves every complete 18-hour integration target unchanged', () => {
  for (const maximum of [1, 6, 18]) {
    const report = evaluateRequest(request({ max_lead_hours: maximum }));
    assert.equal(report.requested_population.generated_rows_per_location, 864);
    assert.equal(report.requested_population.retained_rows_per_location, 48 * maximum);
    assert.equal(report.requested_population.last_physical_valid_time_utc, '2022-01-03T17:00:00Z');
    assert.equal(report.compatibility.retention.supported_export_projection, true);
    assert.equal(report.compatibility.retention.reduces_integration_horizon, false);
    assert.equal(report.compatibility.retention.diagnostic_rows_with_requested_projection, 2 * maximum);
    assert.equal(report.diagnostic_profile.historical_export_example.retained_rows_per_location, 12);
  }
});

test('matching numeric gauge or reach metadata does not resolve a location or prepare data', () => {
  for (const location of [{ identifier_type: 'usgs', identifier: '03479000' }, { identifier_type: 'nwm', identifier: '1017693' }]) {
    const report = evaluateRequest(request(location));
    assert.equal(report.compatibility.location_identifier.matches_declared_identifier, true);
    assert.equal(report.compatibility.location_identifier.establishes_resolution, false);
    assert.equal(report.location_resolution.status, 'unresolved'); assert.equal(report.location_resolution.verified_gauge_reach_mapping, null);
    assert.equal(report.coverage_preparation.coverage_status, 'unknown'); assert.equal(report.coverage_preparation.source_check_performed, false);
    assert.equal(report.coverage_preparation.initialization_origin_utc, null); assert.equal(report.coverage_preparation.required_history_interval, null);
    assert.equal(report.coverage_preparation.current_input_identity, null);
    assert.equal(report.prior_result.status, 'not_inspected'); assert.equal(report.prior_result.completion_established, false);
    assert.ok(codes(report).includes('LOCATION_NOT_RESOLVED')); assert.ok(codes(report).includes('INPUT_BUNDLE_NOT_PREPARED'));
  }
});

test('different gauge, reach or watershed is not replaced with a Watauga demonstration', () => {
  for (const location of [{ identifier_type: 'usgs', identifier: '00000000' }, { identifier_type: 'nwm', identifier: '9999999' }, { identifier_type: 'watershed', identifier: 'Watauga' }]) {
    const input = request(location); const report = evaluateRequest(input);
    assert.deepEqual(report.requested_request.location, input.location);
    assert.equal(report.compatibility.location_identifier.matches_declared_identifier, false);
    assert.equal(report.location_resolution.status, 'unresolved');
    assert.ok(codes(report).includes('DIAGNOSTIC_LOCATION_MISMATCH'));
  }
});

test('dates inside or outside metadata endpoints never fabricate source availability', () => {
  for (const [date, relation] of [['1900-01-01', 'before_declared_interval'], ['2021-12-15', 'at_or_before_declared_endpoint'], ['2090-01-01', 'beyond_declared_endpoint']]) {
    const report = evaluateRequest(request({ start_date: date, end_date: date }));
    assert.equal(report.compatibility.final_target.relation, relation);
    assert.equal(report.coverage_preparation.coverage_status, 'unknown');
    assert.equal(report.coverage_preparation.qualified_profile, null);
    assert.equal(report.compatibility.establishes_admission, false);
    assert.ok(codes(report).includes('COVERAGE_UNKNOWN'));
    assert.ok(codes(report).includes('DIAGNOSTIC_SCHEDULE_MISMATCH'));
  }
});

test('continuous simulation preserves its request without manufacturing forecast issues or zero-hour leads', () => {
  const input = request({ mode: 'continuous_simulation', max_lead_hours: undefined }); const report = evaluateRequest(input);
  assert.deepEqual(report.requested_request, input); assert.equal(report.requested_population.mode, 'continuous_simulation');
  assert.deepEqual(report.requested_population.issues_utc, []); assert.equal(report.requested_population.issue_count, null);
  assert.equal(report.requested_population.horizon_hours, null); assert.equal(report.requested_population.retained_leads, null);
  assert.equal(report.requested_population.generated_rows_per_location, null); assert.equal(report.compatibility.final_target.relation, 'not_applicable');
  assert.equal(report.planning_supported, false); assert.equal(report.diagnostic_profile_match, false);
  assert.ok(codes(report).includes('MODE_NOT_IMPLEMENTED')); assert.equal(report.execution_ready, false);
});

test('forged readiness, preview, translation, resolution and preparation are explicitly rejected', () => {
  const mutations = [
    value => { value.execution_ready = true; },
    value => { value.preview.issue_count = 2; },
    value => { value.preview.generated_rows_per_location = 36; },
    value => { value.preview.last_physical_valid_time_utc = '2022-01-02T18:00:00Z'; },
    value => { value.campaign_translation_proposal.issue_schedule.start_time_utc = '2022-01-01T23:00:00Z'; },
    value => { value.campaign_translation_proposal.issue_schedule.cadence_hours = 24; },
    value => { value.campaign_translation_proposal.horizon_hours = 6; },
    value => { value.campaign_translation_proposal.retained_leads.projection = 'integrate'; },
    value => { value.study.date_semantics = 'inclusive_valid_dates'; },
    value => { value.study.first_issue_hour_utc = 23; },
    value => { value.study.last_issue_time_utc = '2022-01-02T00:00:00Z'; },
    value => { value.study.time_zone = 'America/Chicago'; },
    value => { value.location.resolution_status = 'resolved'; },
    value => { value.location.demonstration.is_live_resolution = true; },
    value => { value.preparation.coverage_status = 'complete'; },
    value => { value.preparation.qualified_profile = 'watauga-v2'; },
    value => { value.preparation.initialization_origin_utc = '2021-12-01T00:00:00Z'; },
    value => { value.preparation.runtime_estimate = 14; },
    value => { value.preparation.blockers = []; },
    value => { value.additional_evidence = { ready: true }; },
    value => { value[''] = { ready: true }; },
    value => { value.preview[''] = { issue_count: 2 }; },
    value => { delete value.preview; },
  ];
  for (const mutate of mutations) { const input = request(); mutate(input); rejected(input, 'INCONSISTENT_REQUEST'); }
});

test('unsupported schema and invalid canonical study fields fail before issue expansion', () => {
  const schema = request(); schema.request_schema_version = 'future'; rejected(schema, 'UNSUPPORTED_REQUEST_SCHEMA');
  const kind = request(); kind.artifact_type = 'campaign'; rejected(kind, 'UNSUPPORTED_REQUEST_SCHEMA');
  const missing = request(); delete missing.study; rejected(missing, 'MALFORMED_REQUEST');
  for (const [key, value] of [['first_date', '2023-02-29'], ['last_date', '2020-01-01'], ['first_issue_hour_utc', 24], ['last_issue_hour_utc', -1], ['requested_max_lead_hours', 19], ['mode', 'forecast']]) {
    const input = request(); input.study[key] = value; rejected(input, 'INVALID_STUDY');
  }
  for (const input of [null, [], true, 'not a request']) rejected(input, 'MALFORMED_REQUEST');
});

test('legacy whole-date artifacts remain unchanged and require explicit rebuilding rather than automatic migration', () => {
  const legacy = request(); legacy.request_schema_version = '0.1';
  legacy.study.date_semantics = 'inclusive_utc_issue_dates_proposal';
  for (const key of ['first_issue_hour_utc', 'last_issue_hour_utc', 'first_issue_time_utc', 'last_issue_time_utc']) Reflect.deleteProperty(legacy.study, key);
  const before = clone(legacy); rejected(legacy, 'REQUEST_SCHEMA_MIGRATION_REQUIRED', '$.request_schema_version');
  assert.deepEqual(legacy, before); assert.equal(legacy.preview.issue_count, 48);
});

test('plain JSON bounds reject cycles, nonfinite values, unsupported types and executable properties', () => {
  const cycle = request(); cycle.other = cycle; rejected(cycle, 'MALFORMED_REQUEST');
  for (const other of [NaN, Infinity, undefined, 1n, () => {}, new Date(), new Map()]) { const input = request(); input.other = other; rejected(input, 'MALFORMED_REQUEST'); }
  const symbol = request(); symbol[Symbol('hidden')] = true; rejected(symbol, 'MALFORMED_REQUEST');
  const hole = request(); hole.other = new Array(2); rejected(hole, 'MALFORMED_REQUEST');
  const array = request(); array.other = []; array.other.named = 1; rejected(array, 'MALFORMED_REQUEST');
  let getterCalls = 0; const accessor = request(); Object.defineProperty(accessor, 'other', { enumerable: true, get() { getterCalls++; return true; } });
  rejected(accessor, 'MALFORMED_REQUEST'); assert.equal(getterCalls, 0);
  const hidden = request(); Object.defineProperty(hidden, 'other', { value: true }); rejected(hidden, 'MALFORMED_REQUEST');
  const unsafe = request(); Object.defineProperty(unsafe, '__proto__', { enumerable: true, value: {} }); rejected(unsafe, 'MALFORMED_REQUEST');
});

test('JSON byte, depth and member bounds fail without partial population assessment', () => {
  const huge = request(); huge.other = 'x'.repeat(MAX_REQUEST_BYTES + 1); rejected(huge, 'REQUEST_LIMIT_EXCEEDED');
  const unicode = request(); unicode.other = '水'.repeat(Math.ceil(MAX_REQUEST_BYTES / 3)); rejected(unicode, 'REQUEST_LIMIT_EXCEEDED');
  const many = request(); many.other = Array(MAX_REQUEST_NODES + 1).fill(null); rejected(many, 'REQUEST_LIMIT_EXCEEDED');
  const deep = request(); let cursor = deep; for (let i = 0; i <= MAX_REQUEST_DEPTH; i++) { cursor.other = {}; cursor = cursor.other; } rejected(deep, 'REQUEST_LIMIT_EXCEEDED');
});

test('maximum whole-day population is complete and larger malformed studies are rejected before expansion', () => {
  const date = days => new Date(Date.parse('2000-01-01T00:00:00Z') + (days - 1) * 86400000).toISOString().slice(0, 10);
  const report = evaluateRequest(request({ start_date: '2000-01-01', end_date: date(4165) }));
  assert.equal(report.requested_population.issue_count, 99960); assert.equal(report.requested_population.issues_utc.length, 99960);
  assert.ok(report.requested_population.issue_count <= MAX_ASSESSMENT_ISSUES);
  assert.equal(report.requested_population.issues_utc.at(-1), `${date(4165)}T23:00:00Z`);
  const invalid = request(); invalid.study.first_date = '2000-01-01'; invalid.study.last_date = date(4167); rejected(invalid, 'INVALID_STUDY');
});

test('explicit issue windows retain the full 99,982-issue bounded population and calendar endpoints', () => {
  const lastDay = new Date(Date.parse('2000-01-01T00:00:00Z') + 4165 * 86400000).toISOString().slice(0, 10);
  const input = request({ start_date: '2000-01-01', end_date: lastDay, start_hour_utc: 0, end_hour_utc: 21 });
  const report = evaluateRequest(input); assert.equal(report.requested_population.issue_count, 99982);
  assert.equal(report.requested_population.issues_utc.length, 99982); assert.equal(report.requested_population.last_issue_utc, `${lastDay}T21:00:00Z`);
  const tooMany = clone(input); tooMany.study.last_issue_hour_utc = 22; rejected(tooMany, 'INVALID_STUDY');
  const early = evaluateRequest(request({ start_date: '0001-01-01', end_date: '0001-01-01', start_hour_utc: 1, end_hour_utc: 1 }));
  assert.deepEqual(early.requested_population.issues_utc, ['0001-01-01T01:00:00Z']);
  const latest = evaluateRequest(request({ start_date: '9999-12-31', end_date: '9999-12-31', start_hour_utc: 5, end_hour_utc: 5 }));
  assert.equal(latest.requested_population.last_physical_valid_time_utc, '9999-12-31T23:00:00Z');
});

test('immutable request and assessment identities are deterministic across object key order', async () => {
  const input = request(); const before = clone(input); const a = await assessRequest(input); const b = await assessRequest(reorder(input));
  assert.deepEqual(input, before); assert.deepEqual(a, b);
  assert.equal(a.identities.algorithm, 'SHA-256'); assert.equal(a.identities.canonicalization, 'sorted-json-utf8-v1');
  assert.equal(a.identities.request_sha256, createHash('sha256').update(sortedJson(input), 'utf8').digest('hex'));
  assert.deepEqual(a.request_policy, REQUEST_POLICY);
  assert.equal(a.identities.policy_sha256, createHash('sha256').update(sortedJson(REQUEST_POLICY), 'utf8').digest('hex'));
  const withoutIdentity = { ...a }; delete withoutIdentity.identities;
  assert.equal(a.identities.assessment_sha256, createHash('sha256').update(sortedJson(withoutIdentity), 'utf8').digest('hex'));
  assert.equal(a.identities.establishes_admission, false); assert.deepEqual(a.identities.assessment_hash_excludes, ['identities']);
  assert.deepEqual(clone(a), a); assert.throws(() => { a.requested_population.issues_utc.pop(); }, TypeError);
  assert.throws(() => { a.requested_request.execution_ready = true; }, TypeError);
  assert.throws(() => { a.identities.request_sha256 = 'forged'; }, TypeError);
});

test('snapshot is frozen before asynchronous digest so later caller changes cannot race its binding', async () => {
  const input = request(); const expected = clone(input); const pending = assessRequest(input);
  input.study.first_date = '2090-01-01'; input.preview.issue_count = 2; input.execution_ready = true;
  const report = await pending;
  assert.deepEqual(report.requested_request, expected); assert.equal(report.requested_population.issue_count, 48);
  assert.equal(report.identities.request_sha256, createHash('sha256').update(sortedJson(expected), 'utf8').digest('hex'));
  const altered = await assessRequest(request({ max_lead_hours: 18 }));
  assert.notEqual(report.identities.request_sha256, altered.identities.request_sha256);
  assert.notEqual(report.identities.assessment_sha256, altered.identities.assessment_sha256);
});

test('missing standard Web Crypto fails closed with no homemade or unbound identity fallback', async () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: undefined });
  try {
    assert.equal(evaluateRequest(request()).status, 'blocked');
    await assert.rejects(assessRequest(request()), error => error instanceof AssessmentError && error.code === 'IDENTITY_UNAVAILABLE');
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'crypto', descriptor); else Reflect.deleteProperty(globalThis, 'crypto');
  }
});

test('assessment has no network, asset, socket, executor or publication dependency and performs zero calls', async () => {
  const original = new Map(); const calls = [];
  for (const name of ['fetch', 'WebSocket', 'XMLHttpRequest', 'executor', 'acquireInputs', 'publishAssessment', 'openWorkerSocket']) {
    original.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { configurable: true, value: (...args) => { calls.push({ name, args }); throw new Error('Forbidden side effect'); } });
  }
  try {
    await assessRequest(request()); await assessRequest(request({ mode: 'continuous_simulation' }));
    assert.deepEqual(calls, []);
    const source = await readFile(new URL('../assessment.mjs', import.meta.url), 'utf8');
    assert.deepEqual([...source.matchAll(/import[^;]+from\s+['"]([^'"]+)['"]/g)].map(match => match[1]), ['./request.mjs']);
    assert.doesNotMatch(source, /\b(fetch|WebSocket|XMLHttpRequest|require|import)\s*\(/);
    assert.doesNotMatch(source, /node:(fs|net|http|https|child_process)|file:\/\/|unix:\/\//);
  } finally {
    for (const [name, descriptor] of original) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor); else Reflect.deleteProperty(globalThis, name);
    }
  }
});
