import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRequest, RequestError } from '../request.mjs';
const base = { identifier_type: 'usgs', identifier: '03479000', mode: 'reforecast', start_date: '2022-01-01', end_date: '2022-01-02', max_lead_hours: '6' };
const request = changes => buildRequest({ ...base, ...changes });
const rejects = (changes, field) => assert.throws(() => request(changes), error => error instanceof RequestError && error.field === field);
test('inclusive issue dates translate to exclusive next-day UTC and all hourly issues', () => {
  const result = request();
  assert.deepEqual(result.campaign_translation_proposal, { schema_version: '1.1', issue_schedule: { start_time_utc: '2022-01-01T00:00:00Z', stop_time_utc_exclusive: '2022-01-03T00:00:00Z', cadence_hours: 1 }, horizon_hours: 18, retained_leads: { min_lead_hours: 1, max_lead_hours: 6, projection: 'export' } });
  assert.equal(result.preview.issue_count, 48);
  assert.equal(result.preview.last_issue_utc, '2022-01-02T23:00:00Z');
  assert.equal(result.preview.last_retained_valid_time_utc, '2022-01-03T05:00:00Z');
  assert.equal(result.preview.last_physical_valid_time_utc, '2022-01-03T17:00:00Z');
  assert.equal(result.preview.retained_rows_per_location, 288);
  assert.equal(result.preview.generated_rows_per_location, 864);
});
test('one date contains 24 issues and targets cross the year boundary', () => {
  const p = request({ start_date: '2023-12-31', end_date: '2023-12-31', max_lead_hours: 18 }).preview;
  assert.equal(p.issue_count, 24); assert.equal(p.first_retained_valid_time_utc, '2023-12-31T01:00:00Z');
  assert.equal(p.last_retained_valid_time_utc, '2024-01-01T17:00:00Z');
});
test('leap days are real calendar days, invalid rollovers are rejected', () => {
  assert.equal(request({ start_date: '2024-02-28', end_date: '2024-03-01' }).preview.issue_count, 72);
  for (const start_date of ['2023-02-29', '2024-02-30', '2024-04-31', '2024-13-01', '2024-01-00', '01/01/2024', '', '0000-01-01']) rejects({ start_date }, 'start_date');
});
test('UTC schedules do not gain or lose hours at daylight-saving boundaries', () => {
  for (const [start_date, end_date] of [['2024-03-09', '2024-03-11'], ['2024-11-02', '2024-11-04']]) {
    assert.equal(request({ start_date, end_date }).preview.issue_count, 72);
  }
});
test('leading years survive without JavaScript 1900 coercion and overflow is blocked', () => {
  assert.equal(request({ start_date: '0001-01-02', end_date: '0001-01-02' }).preview.first_issue_utc, '0001-01-02T00:00:00Z');
  rejects({ start_date: '0001-01-01', end_date: '0001-01-01' }, 'start_date');
  rejects({ start_date: '9999-12-31', end_date: '9999-12-31' }, 'end_date');
});
test('reversed and excessively large issue windows fail before expansion', () => {
  rejects({ end_date: '2021-12-31' }, 'end_date');
  rejects({ start_date: '2000-01-01', end_date: '2020-01-01' }, 'end_date');
});
test('lead retention cannot silently change physical horizon or accept malformed values', () => {
  for (const max_lead_hours of [0, 19, 1.5, true, null, '', '6 hours', '1e1', ' 6 ', [], {}]) rejects({ max_lead_hours }, 'max_lead_hours');
  for (const maximum of [1, 6, 18]) {
    const r = request({ max_lead_hours: maximum });
    assert.equal(r.campaign_translation_proposal.horizon_hours, 18);
    assert.equal(r.preview.generated_rows_per_location, 864);
    assert.equal(r.preview.retained_rows_per_location, 48 * maximum);
  }
});
test('identifier validation preserves submitted leading zeros without claiming resolution', () => {
  assert.equal(request({ identifier: ' 03479000 ' }).location.submitted_identifier, '03479000');
  assert.equal(request().location.resolution_status, 'unresolved');
  assert.equal(request().location.demonstration.is_live_resolution, false);
  rejects({ identifier: '' }, 'identifier'); rejects({ identifier: 'gauge 03479000' }, 'identifier');
  rejects({ identifier: '0'.repeat(121) }, 'identifier'); rejects({ identifier_type: 'other' }, 'identifier_type');
  for (const location of [{ identifier_type: 'nwm', identifier: '1017693' }, { identifier_type: 'watershed', identifier: 'Watauga' }, { identifier_type: 'usgs', identifier: '00000000' }]) {
    const r = request(location); assert.equal(r.location.demonstration, null); assert.equal(r.location.resolution_status, 'unresolved');
  }
});
test('future or historical dates never imply availability or execution readiness', () => {
  for (const date of ['1900-01-01', '2090-01-01']) {
    const r = request({ start_date: date, end_date: date });
    assert.equal(r.preparation.coverage_status, 'unknown'); assert.equal(r.execution_ready, false);
    assert.equal(r.preparation.runtime_estimate, null); assert.equal(r.preparation.qualified_profile, null);
    assert.equal(r.preparation.blockers.length, 4);
  }
});
test('no-lead request remains a proposed mode without manufactured campaign translation', () => {
  const r = request({ mode: 'continuous_simulation', max_lead_hours: undefined });
  assert.equal(r.preview, null); assert.equal(r.campaign_translation_proposal, null);
  assert.equal(r.study.requested_max_lead_hours, null); assert.equal(r.preparation.blockers[0].code, 'MODE_NOT_IMPLEMENTED');
  rejects({ mode: 'forecast' }, 'mode');
});
test('portable request round-trips as JSON without mutating inputs', () => {
  const input = Object.freeze({ ...base }); const r = buildRequest(input);
  assert.deepEqual(JSON.parse(JSON.stringify(r)), r);
  assert.equal(r.request_schema_version, '0.1'); assert.equal(r.artifact_type, 'researcher_request');
  assert.equal(r.interface_stage, 'prototype'); assert.equal(r.intended_evaluation_level, 'UX_E1'); assert.equal(r.user_study_conducted, false); assert.equal(r.execution_ready, false);
});

test('large issue periods leave at least one history hour before first issue and the full horizon after last', () => {
  const end = days => new Date(Date.parse('2000-01-01T00:00:00Z') + (days - 1) * 86400000).toISOString().slice(0, 10);
  assert.equal(request({ start_date: '2000-01-01', end_date: end(4165) }).preview.issue_count, 99960);
  rejects({ start_date: '2000-01-01', end_date: end(4166) }, 'end_date');
});
