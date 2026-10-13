/** Offline request assessment only. This module does not resolve, acquire or execute. */
import { buildRequest, CONTRACT_VERSION, MAX_ISSUES, REQUEST_POLICY, RequestError } from './request.mjs';

export const ASSESSMENT_SCHEMA_VERSION = 'browser-preparation-assessment/0.1';
export const MAX_REQUEST_BYTES = 65_536;
export const MAX_REQUEST_DEPTH = 16;
export const MAX_REQUEST_NODES = 4_096;
export const MAX_ASSESSMENT_ISSUES = MAX_ISSUES;
const HOUR = 3_600_000;
const encoder = new TextEncoder();
const utc = ms => new Date(ms).toISOString().replace('.000Z', 'Z');

export class AssessmentError extends Error {
  constructor(code, field, message) {
    super(message); this.name = 'AssessmentError'; this.code = code; this.field = field;
  }
}
const fail = (code, field, message) => { throw new AssessmentError(code, field, message); };
function freeze(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
}

/** Declared prior diagnostic metadata; reading this object is not fresh admission. */
export const DIAGNOSTIC_PROFILE_METADATA = freeze({
  profile_id: 'watauga-v2-operator-diagnostic',
  evidence_class: 'declared_diagnostic_metadata',
  release_qualified: false,
  current_assets_verified: false,
  origin_time_utc: '2021-12-01T00:00:00Z',
  history_stop_time_utc: '2022-01-02T18:00:00Z',
  issue_times_utc: ['2022-01-01T23:00:00Z', '2022-01-02T00:00:00Z'],
  issue_count: 2,
  horizon_hours: 18,
  output_timestep_hours: 1,
  location: { usgs_gauge: '03479000', nwm_reach: '1017693', catchment_count: 31 },
  generated_rows_per_location: 36,
  historical_export_example: { min_lead_hours: 1, max_lead_hours: 6, retained_rows_per_location: 12 },
  supported_export_retention: { min_lead_hours: 1, max_lead_hours: 18, projection: 'export' },
  scientific_configuration_identity_sha256: 'e05ec5ed5ceea3d5894e6691f7120f75aea1db6d951c9585b34b4ea34fd5dee6',
  runtime_identity_sha256: '9f3a32d9bb9cf5214b99bf84e40230a2d83deeeb6c27430bd37f00a9ca02578d',
  input_assembly_identity_sha256: '3c55890840e80768bc0647abf04d1b24a6c8bc061fec5a67de875bdc91334dfe',
  reference_set_identity_sha256: '3ac59c420b3b96a5c45f2dea53dc149524e496a5063356944246cf08c25963d2',
  evidence_sources: ['docs/PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md', 'docs/evidence/public-campaign-execution-increment-20261011.json'],
});

// Inspect own data properties before copying. JSON cannot contain accessors, holes,
// hidden fields, symbols, cycles or arbitrary object instances. No getter is invoked.
function snapshotJson(input) {
  let nodes = 0;
  const ancestors = new Set();
  function copy(value, field, depth) {
    if (++nodes > MAX_REQUEST_NODES || depth > MAX_REQUEST_DEPTH) fail('REQUEST_LIMIT_EXCEEDED', field, 'The request exceeds the bounded JSON structure.');
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) fail('MALFORMED_REQUEST', field, 'JSON numbers must be finite.');
      return value;
    }
    if (typeof value === 'string') {
      if (value.length > MAX_REQUEST_BYTES) fail('REQUEST_LIMIT_EXCEEDED', field, 'The request exceeds the JSON byte limit.');
      return value;
    }
    if (typeof value !== 'object') fail('MALFORMED_REQUEST', field, 'Only JSON values are accepted.');
    if (ancestors.has(value)) fail('MALFORMED_REQUEST', field, 'A request cannot contain cycles.');
    const array = Array.isArray(value);
    if (Object.getPrototypeOf(value) !== (array ? Array.prototype : Object.prototype) && !(Object.getPrototypeOf(value) === null && !array)) {
      fail('MALFORMED_REQUEST', field, 'A request must contain plain JSON objects and arrays.');
    }
    const keys = Reflect.ownKeys(value);
    if (keys.length > MAX_REQUEST_NODES || (array && value.length > MAX_REQUEST_NODES)) fail('REQUEST_LIMIT_EXCEEDED', field, 'The request contains too many JSON members.');
    if (keys.some(key => typeof key !== 'string')) fail('MALFORMED_REQUEST', field, 'JSON symbol fields are unsupported.');
    const output = array ? [] : {};
    ancestors.add(value);
    for (const key of keys) {
      if (array && key === 'length') continue;
      if (key.length > MAX_REQUEST_BYTES) fail('REQUEST_LIMIT_EXCEEDED', field, 'A JSON field exceeds the byte limit.');
      if (['__proto__', 'constructor', 'prototype'].includes(key)) fail('MALFORMED_REQUEST', `${field}.${key}`, 'Unsafe JSON field name.');
      if (array && (!/^(0|[1-9]\d*)$/.test(key) || Number(key) >= value.length)) fail('MALFORMED_REQUEST', field, 'JSON arrays cannot have named fields.');
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) fail('MALFORMED_REQUEST', `${field}.${key}`, 'Only enumerable JSON data fields are accepted.');
      output[key] = copy(descriptor.value, `${field}.${key}`, depth + 1);
    }
    ancestors.delete(value);
    if (array && Object.keys(output).length !== value.length) fail('MALFORMED_REQUEST', field, 'JSON arrays cannot have missing elements.');
    return output;
  }
  const result = copy(input, '$', 0);
  if (encoder.encode(JSON.stringify(result)).byteLength > MAX_REQUEST_BYTES) fail('REQUEST_LIMIT_EXCEEDED', '$', 'The request exceeds 65,536 UTF-8 JSON bytes.');
  return result;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}
function difference(actual, expected, field = '$') {
  if (actual === expected) return null;
  if (!actual || !expected || typeof actual !== 'object' || typeof expected !== 'object' || Array.isArray(actual) !== Array.isArray(expected)) return field;
  const actualKeys = Object.keys(actual).sort(); const expectedKeys = Object.keys(expected).sort();
  const extra = actualKeys.find(key => !Object.hasOwn(expected, key));
  const missing = expectedKeys.find(key => !Object.hasOwn(actual, key));
  if (extra !== undefined || missing !== undefined) return `${field}.${extra ?? missing}`;
  for (const key of expectedKeys) {
    const found = difference(actual[key], expected[key], `${field}.${key}`);
    if (found) return found;
  }
  return null;
}
function validateRequest(input) {
  const request = snapshotJson(input);
  if (!request || typeof request !== 'object' || Array.isArray(request)) fail('MALFORMED_REQUEST', '$', 'Submit a serialized researcher request object.');
  if (request.request_schema_version === '0.1' && request.artifact_type === 'researcher_request') {
    fail('REQUEST_SCHEMA_MIGRATION_REQUIRED', '$.request_schema_version', 'Schema 0.1 uses whole issue dates. Preserve that artifact and explicitly rebuild it under schema 0.2; no implicit migration or scope reduction is performed.');
  }
  if (request.request_schema_version !== CONTRACT_VERSION || request.artifact_type !== 'researcher_request') {
    fail('UNSUPPORTED_REQUEST_SCHEMA', '$.request_schema_version', `Only researcher_request schema ${CONTRACT_VERSION} is supported. Rebuild older or unknown request artifacts explicitly.`);
  }
  if (!request.location || !request.study || typeof request.location !== 'object' || typeof request.study !== 'object') {
    fail('MALFORMED_REQUEST', '$', 'Location and study fields are required.');
  }
  let rebuilt;
  try {
    rebuilt = buildRequest({
      identifier_type: request.location.identifier_type,
      identifier: request.location.submitted_identifier,
      mode: request.study.mode,
      start_date: request.study.first_date,
      end_date: request.study.last_date,
      start_hour_utc: request.study.first_issue_hour_utc,
      end_hour_utc: request.study.last_issue_hour_utc,
      max_lead_hours: request.study.requested_max_lead_hours,
    });
  } catch (error) {
    if (error instanceof RequestError) fail('INVALID_STUDY', error.field, error.message);
    throw error;
  }
  const mismatch = difference(request, rebuilt);
  if (mismatch) fail('INCONSISTENT_REQUEST', mismatch, 'This request differs from the canonical request rebuilt from its location and study. Rebuild the request; derived previews, resolution and readiness cannot be supplied as evidence.');
  return request;
}
function blocker(code, requirement, message, next_option) { return { code, requirement, message, next_option }; }

/** Synchronous assessment; no file, network, worker, archive or asset access. */
export function evaluateRequest(input) {
  const request = validateRequest(input);
  const forecast = request.study.mode === 'reforecast';
  const p = request.preview;
  const issues = [];
  if (forecast) {
    if (p.issue_count > MAX_ASSESSMENT_ISSUES) fail('REQUEST_LIMIT_EXCEEDED', '$.study', 'The complete requested issue list exceeds the offline assessment bound.');
    const start = Date.parse(request.campaign_translation_proposal.issue_schedule.start_time_utc);
    for (let i = 0; i < p.issue_count; i++) issues.push(utc(start + i * HOUR));
  }
  const profile = DIAGNOSTIC_PROFILE_METADATA;
  const location = request.location;
  const identifierMatch = (location.identifier_type === 'usgs' && location.submitted_identifier === profile.location.usgs_gauge) ||
    (location.identifier_type === 'nwm' && location.submitted_identifier === profile.location.nwm_reach);
  const scheduleMatch = forecast && issues.length === profile.issue_times_utc.length && issues.every((issue, i) => issue === profile.issue_times_utc[i]);
  const horizonMatch = forecast && request.campaign_translation_proposal.horizon_hours === profile.horizon_hours;
  const diagnosticMatch = forecast && identifierMatch && scheduleMatch && horizonMatch;
  const lastTarget = forecast ? p.last_physical_valid_time_utc : null;
  const targetRelation = !forecast ? 'not_applicable' : lastTarget > profile.history_stop_time_utc ? 'beyond_declared_endpoint' :
    lastTarget <= profile.origin_time_utc ? 'before_declared_interval' : 'at_or_before_declared_endpoint';
  const blockers = [
    blocker('LOCATION_NOT_RESOLVED', 'location_resolution', 'No verified outlet, gauge/reach crosswalk or upstream domain has been resolved. A matching diagnostic identifier is only a metadata comparison.', 'Resolve and version the submitted location without substituting another watershed.'),
    blocker('COVERAGE_UNKNOWN', 'coverage', 'Source coverage, issue availability and gaps have not been checked across initialization, history and every full forecast target.', 'Check actual sources for the complete requested period after defining initialization.'),
    blocker('INITIALIZATION_NOT_SELECTED', 'initialization', 'The researcher request does not select a scientifically justified initialization origin or history interval.', 'Select and qualify initialization; do not silently inherit the diagnostic cold origin.'),
    blocker('SCIENTIFIC_PROFILE_UNQUALIFIED', 'scientific_profile', 'The pinned diagnostic is not release-qualified, and no qualified scientific profile has been bound to this request.', 'Qualify scientific defaults and bind the complete input, runtime and reference identities.'),
    blocker('INPUT_BUNDLE_NOT_PREPARED', 'input_preparation', 'No input/runtime/reference bundle has been prepared or verified for this request by this offline interface.', 'Prepare and verify the full requested study through a separately authorized preparation service.'),
    blocker('CAMPAIGN_PROTOCOL_NOT_ADMITTED', 'execution_admission', 'This request has no current identity-bound input, reference and bounded resource protocol. Prior diagnostic receipts do not authorize a new run.', 'Admit and authorize the complete requested campaign under its own protocol before any execution.'),
    blocker('EXECUTION_SERVICE_UNAVAILABLE', 'execution_service', 'This assessment does not submit work, contact workers or provide verified dataset downloads.', 'Implement the service and its execution admission after the preparation contract is reviewed.'),
  ];
  if (!forecast) blockers.unshift(blocker('MODE_NOT_IMPLEMENTED', 'mode', 'Continuous simulation remains a proposed mode with unresolved date semantics. No reforecast schedule has been manufactured.', 'Define and qualify a separate continuous-simulation contract.'));
  if (!identifierMatch) blockers.push(blocker('DIAGNOSTIC_LOCATION_MISMATCH', 'diagnostic_location', 'The submitted identifier does not match the two declared identifiers in the available Watauga diagnostic metadata; no mapping is inferred.', 'Prepare the requested location, or inspect Watauga separately while preserving this request.'));
  if (forecast && !scheduleMatch) blockers.push(blocker('DIAGNOSTIC_SCHEDULE_MISMATCH', 'issue_schedule', `The ${issues.length}-issue requested schedule is supported for planning and is preserved unchanged. It differs from the two-issue diagnostic; execution needs a complete fixture, sealed references and bounded protocol for the requested schedule.`, 'Qualify preparation and execution for every requested issue. Inspect the fixed diagnostic only as a separate study.'));
  if (targetRelation === 'beyond_declared_endpoint' || targetRelation === 'before_declared_interval') blockers.push(blocker('DIAGNOSTIC_TARGET_OUTSIDE_PREPARED_INTERVAL', 'final_physical_target', `The requested final physical target ${lastTarget} is outside the declared diagnostic interval ending ${profile.history_stop_time_utc}. This comparison is not a source-coverage check.`, 'Check and prepare inputs through the full requested targets, plus required initialization/history.'));
  return freeze({
    assessment_schema_version: ASSESSMENT_SCHEMA_VERSION,
    artifact_type: 'browser_preparation_assessment',
    assessment_kind: 'offline_preparation',
    status: 'blocked',
    planning_supported: forecast,
    diagnostic_profile_match: diagnosticMatch,
    execution_ready: false,
    release_qualified: false,
    request_policy: REQUEST_POLICY,
    requested_request: request,
    requested_population: {
      mode: request.study.mode,
      date_semantics: request.study.date_semantics,
      issue_schedule: forecast ? request.campaign_translation_proposal.issue_schedule : null,
      issues_utc: issues,
      issue_count: forecast ? issues.length : null,
      population_status: forecast ? 'complete_requested_issue_list' : 'not_defined_for_proposed_mode',
      horizon_hours: forecast ? request.campaign_translation_proposal.horizon_hours : null,
      retained_leads: forecast ? request.campaign_translation_proposal.retained_leads : null,
      generated_rows_per_location: forecast ? p.generated_rows_per_location : null,
      retained_rows_per_location: forecast ? p.retained_rows_per_location : null,
      first_issue_utc: forecast ? issues[0] : null,
      last_issue_utc: forecast ? issues.at(-1) : null,
      first_retained_valid_time_utc: forecast ? p.first_retained_valid_time_utc : null,
      last_retained_valid_time_utc: forecast ? p.last_retained_valid_time_utc : null,
      last_physical_valid_time_utc: lastTarget,
      output_timestep_hours: forecast ? p.output_timestep_hours : null,
    },
    location_resolution: { status: 'unresolved', submitted_identifier: location.submitted_identifier, identifier_type: location.identifier_type, verified_gauge_reach_mapping: null, upstream_domain_identity: null, source_version: null },
    coverage_preparation: {
      coverage_status: 'unknown', source_check_performed: false,
      initialization_origin_utc: null, required_history_interval: null,
      required_full_target_endpoint_utc: lastTarget,
      input_bundle_status: 'not_prepared_by_this_interface', qualified_profile: null,
      runtime_estimate: null, cost_estimate: null,
      current_input_identity: null, current_runtime_identity: null, current_reference_identity: null,
    },
    diagnostic_profile: profile,
    compatibility: {
      mode: { matches: forecast, requested: request.study.mode, diagnostic: 'reforecast' },
      location_identifier: { matches_declared_identifier: identifierMatch, establishes_resolution: false },
      schedule: { matches: scheduleMatch, requested_issue_count: forecast ? issues.length : null, diagnostic_issue_count: profile.issue_count, request_preserved: true },
      horizon: { matches: horizonMatch, requested_hours: forecast ? request.campaign_translation_proposal.horizon_hours : null, diagnostic_hours: profile.horizon_hours },
      retention: { supported_export_projection: forecast, reduces_integration_horizon: false, diagnostic_rows_with_requested_projection: forecast ? profile.issue_count * request.study.requested_max_lead_hours : null },
      final_target: { requested_utc: lastTarget, declared_diagnostic_endpoint_utc: profile.history_stop_time_utc, relation: targetRelation, establishes_source_coverage: false },
      diagnostic_profile_match: diagnosticMatch,
      match_scope: 'declared_issue_clocks_identifier_and_horizon_only',
      origin_and_history_bound: false,
      assets_runtime_reference_verified: false,
      fresh_execution_authorized: false,
      establishes_admission: false,
    },
    blockers,
    options: [
      { code: 'PRESERVE_REQUEST_AND_PREPARE', label: 'Keep the requested study and prepare all requested issues', rewrites_request: false, execution_available: false },
      { code: 'INSPECT_SEPARATE_DIAGNOSTIC', label: 'Inspect the fixed two-issue Watauga diagnostic separately', rewrites_request: false, execution_available: false, changes_study_scope: true, requires_separate_explicit_choice: true },
    ],
    prior_result: { status: 'not_inspected', result_identity: null, verification_performed: false, completion_established: false },
  });
}

/** Bind immutable snapshots with standard Web Crypto; identities never grant admission. */
export async function assessRequest(input) {
  const report = evaluateRequest(input); // Snapshot and freeze before the first await.
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) fail('IDENTITY_UNAVAILABLE', '$', 'Standard Web Crypto SHA-256 is unavailable. No assessment identity can be produced.');
  const hash = async value => {
    const bytes = await subtle.digest('SHA-256', encoder.encode(canonicalJson(value)));
    return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
  };
  const [requestSha, assessmentSha, policySha] = await Promise.all([hash(report.requested_request), hash(report), hash(report.request_policy)]);
  return freeze({ ...report, identities: { canonicalization: 'sorted-json-utf8-v1', algorithm: 'SHA-256', request_sha256: requestSha, assessment_sha256: assessmentSha, policy_sha256: policySha, assessment_hash_excludes: ['identities'], establishes_admission: false } });
}
