/** Inspect offline preparation-result/0.1 JSON. Integrity is not admission. */
import { REQUEST_POLICY } from './request.mjs';
import { evaluateRequest } from './assessment.mjs';

export const MAX_PREPARATION_REPORT_BYTES = 8 * 1024 * 1024;
// Exact existing policy bytes; the offline test checks this pin against both copies.
export const PREPARATION_POLICY_BYTES_SHA256 = 'b4bfef6cd2a389d85db7d517aaae03fee7505015e294efda8e5d9386d216db3f';
const MAX_NODES = REQUEST_POLICY.max_issues + 4096;
const HOUR = 3_600_000;
const encoder = new TextEncoder();
const SHA = /^[0-9a-f]{64}$/;
const STATUSES = ['unknown', 'missing', 'failed', 'passed'];
const CHECKS = Object.freeze({
  location_resolution: 'Resolve and version the submitted outlet, gauge/reach mapping and complete upstream domain without substituting a watershed.',
  initialization: 'Select and qualify an initialization origin before the first requested issue; retain its scientific justification.',
  source_coverage: "Check initialization/history and every requested issue's full 18-hour forcing window, including source gaps and units.",
  input_bundle: 'Prepare and content-verify inputs for the complete study; bind source, domain, configuration and transformation identities.',
  runtime_identity: 'Verify the supported runtime and its exact source, binary, component and routing identities.',
  reference_set: 'Bind qualified independent references to the exact requested population and scientific/input/runtime identities.',
  scientific_profile: 'Qualify scientific parameters, forcing/time semantics and initialization for this study; diagnostic metadata alone is insufficient.',
});

export class PreparationReportError extends Error {
  constructor(code, message) { super(message); this.name = 'PreparationReportError'; this.code = code; }
}
const fail = (code, message) => { throw new PreparationReportError(code, message); };
const malformed = () => fail('INVALID_PREPARATION_REPORT', 'Use the complete, unchanged preparation-result/0.1 report exported by the preparation adapter.');
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
const same = (a, b) => canonical(a) === canonical(b);
function exactKeys(value, keys) {
  if (!value || Array.isArray(value) || typeof value !== 'object' || !same(Object.keys(value).sort(), [...keys].sort())) malformed();
}
// Scan bounded JSON before materializing it. JSON.parse alone drops duplicate
// keys, including equivalent escaped names, and would hide ambiguous evidence.
function scanJson(text) {
  let position = 0, nodes = 0;
  const invalid = () => fail('INVALID_PREPARATION_REPORT_JSON', 'The selected file is not valid JSON. Export the preparation report again.');
  const space = () => { while (position < text.length && /[\x20\t\r\n]/.test(text[position])) position += 1; };
  function string(decode = false) {
    if (text[position] !== '"') invalid();
    const start = position++;
    while (position < text.length) {
      const character = text[position++];
      if (character === '"') {
        if (!decode) return;
        try { return JSON.parse(text.slice(start, position)); } catch { invalid(); }
      }
      if (character === '\\') position += 1;
    }
    invalid();
  }
  function value(depth) {
    if (++nodes > MAX_NODES || depth > 16) fail('PREPARATION_REPORT_LIMIT_EXCEEDED', 'The preparation report exceeds the bounded JSON structure.');
    space();
    const type = text[position];
    if (type === '"') { string(); return; }
    if (type === '{') {
      position += 1; space();
      if (text[position] === '}') { position += 1; return; }
      const keys = new Set();
      while (position < text.length) {
        space(); const key = string(true);
        if (keys.has(key)) fail('DUPLICATE_PREPARATION_REPORT_KEY', 'The preparation report contains duplicate JSON fields. Export one complete unambiguous backend report.');
        if (['__proto__', 'constructor', 'prototype'].includes(key)) malformed();
        keys.add(key); space();
        if (text[position++] !== ':') invalid();
        value(depth + 1); space();
        if (text[position] === '}') { position += 1; return; }
        if (text[position++] !== ',') invalid();
      }
      invalid();
    }
    if (type === '[') {
      position += 1; space();
      if (text[position] === ']') { position += 1; return; }
      while (position < text.length) {
        value(depth + 1); space();
        if (text[position] === ']') { position += 1; return; }
        if (text[position++] !== ',') invalid();
      }
      invalid();
    }
    const start = position;
    while (position < text.length && !/[,}\]\x20\t\r\n]/.test(text[position])) position += 1;
    if (position === start) invalid();
  }
  value(0); space(); if (position !== text.length) invalid();
}
function boundedJson(text) {
  if (typeof text !== 'string' || text.length > MAX_PREPARATION_REPORT_BYTES || encoder.encode(text).byteLength > MAX_PREPARATION_REPORT_BYTES) {
    fail('PREPARATION_REPORT_LIMIT_EXCEEDED', 'The preparation report must be at most 8 MiB of UTF-8 JSON.');
  }
  scanJson(text);
  let value;
  try { value = JSON.parse(text); } catch { fail('INVALID_PREPARATION_REPORT_JSON', 'The selected file is not valid JSON. Export the preparation report again.'); }
  let nodes = 0;
  function inspect(item, depth) {
    if (++nodes > MAX_NODES || depth > 16) fail('PREPARATION_REPORT_LIMIT_EXCEEDED', 'The preparation report exceeds the bounded JSON structure.');
    if (typeof item === 'number' && !Number.isFinite(item)) malformed();
    if (item && typeof item === 'object') {
      for (const [key, child] of Object.entries(item)) {
        if (['__proto__', 'constructor', 'prototype'].includes(key)) malformed();
        inspect(child, depth + 1);
      }
    }
  }
  inspect(value, 0);
  return value;
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
async function hash(value) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) fail('PREPARATION_IDENTITY_UNAVAILABLE', 'Web Crypto SHA-256 is unavailable. The preparation report cannot be checked or downloaded.');
  const bytes = await subtle.digest('SHA-256', encoder.encode(canonical(value)));
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('');
}
function evidence(value, status) {
  if (status === 'unknown') { if (value !== null) malformed(); return; }
  exactKeys(value, ['artifact_sha256', 'verifier', 'evidence_class', 'detail']);
  if (typeof value.artifact_sha256 !== 'string' || !SHA.test(value.artifact_sha256)
      || !['synthetic', 'declared_metadata', 'verification_receipt'].includes(value.evidence_class)
      || ['verifier', 'detail'].some(key => typeof value[key] !== 'string' || !value[key].trim() || [...value[key]].length > 2048)) malformed();
}
function originTime(value, request) {
  if (value === null) return null;
  if (request.study.mode !== 'reforecast' || typeof value !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:00:00Z$/.test(value) || value.startsWith('0000-')) malformed();
  const ms = Date.parse(value);
  if (!Number.isFinite(ms) || new Date(ms).toISOString().replace('.000Z', 'Z') !== value
      || ms >= Date.parse(request.study.first_issue_time_utc)
      || (Date.parse(request.preview.last_physical_valid_time_utc) - ms) / HOUR > REQUEST_POLICY.max_history_hours) malformed();
  return value;
}
const blocker = (code, requirement, message, next_option, evidence = null) => ({ code, requirement, message, next_option, evidence });

/** Rebuild the backend contract and verify identities before displaying any outcomes. */
export async function validatePreparationReport(text, currentRequest) {
  const report = boundedJson(text);
  const assessment = evaluateRequest(currentRequest); // Validate and detach before await.
  const request = assessment.requested_request;
  exactKeys(report, ['preparation_result_schema_version', 'artifact_type', 'assessment_kind', 'status', 'preparation_checks_status', 'planning_supported', 'execution_ready', 'release_qualified', 'requested_request', 'requested_population', 'preparation_binding', 'checks', 'blockers', 'evidence_boundary', 'identities']);
  if (report.preparation_result_schema_version !== 'preparation-result/0.1') malformed();
  if (!same(report.requested_request, request)) fail('PREPARATION_REQUEST_MISMATCH', 'This report belongs to another study request. Recheck the complete current site, issue period and retained leads; export a newly bound report.');
  exactKeys(report.identities, ['canonicalization', 'report_sha256', 'report_hash_excludes', 'establishes_admission']);
  if (report.identities.canonicalization !== 'sorted-json-utf8-v1' || typeof report.identities.report_sha256 !== 'string' || !SHA.test(report.identities.report_sha256)
      || !same(report.identities.report_hash_excludes, ['identities']) || report.identities.establishes_admission !== false) malformed();
  exactKeys(report.preparation_binding, ['request_sha256', 'scope_sha256', 'scope']);
  const suppliedScope = report.preparation_binding.scope;
  if (!suppliedScope || typeof suppliedScope !== 'object') malformed();
  const origin = originTime(suppliedScope.initialization_origin_utc, request);
  const forecast = request.study.mode === 'reforecast';
  const requestSha = await hash(request);
  const scope = {
    request_sha256: requestSha, policy_bytes_sha256: PREPARATION_POLICY_BYTES_SHA256,
    submitted_location: { identifier_type: request.location.identifier_type, submitted_identifier: request.location.submitted_identifier },
    mode: request.study.mode, initialization_origin_utc: origin,
    required_history_interval: forecast && origin !== null ? { start_time_utc: origin, stop_time_utc_exclusive: request.preview.last_physical_valid_time_utc, provider_label: 'interval_start', timestep_hours: 1 } : null,
    issue_schedule: forecast ? request.campaign_translation_proposal.issue_schedule : null,
    issue_count: forecast ? request.preview.issue_count : null,
    horizon_hours: forecast ? 18 : null, required_source_leads: forecast ? { min: 1, max: 18 } : null,
    coverage_requirement: forecast ? 'history_and_each_issue_specific_full_forecast_window' : 'undefined_for_proposed_mode',
    final_physical_target_utc: forecast ? request.preview.last_physical_valid_time_utc : null,
  };
  if (!same(suppliedScope, scope)) fail('PREPARATION_SCOPE_MISMATCH', 'The report scope or policy differs from this complete study. Obtain a newly bound report without shortening the issue population or physical forcing window.');
  const scopeSha = await hash(scope);
  const binding = { request_sha256: requestSha, scope_sha256: scopeSha, scope };
  if (!same(report.preparation_binding, binding)) fail('PREPARATION_SCOPE_MISMATCH', 'The report request or scope identity does not match its content. Export a newly bound report.');
  if (!Array.isArray(report.checks) || report.checks.length !== Object.keys(CHECKS).length) malformed();
  const checks = [], blockers = [];
  for (const [index, [check, action]] of Object.entries(CHECKS).entries()) {
    const item = report.checks[index];
    exactKeys(item, ['check_id', 'status', 'reported_status', 'receipt_sha256', 'reported_binding', 'evidence', 'artifact_verified_by_this_interface']);
    if (item.check_id !== check || item.artifact_verified_by_this_interface !== false) malformed();
    let status = 'unknown';
    if (item.reported_status === null) {
      if (item.receipt_sha256 !== null || item.reported_binding !== null || item.evidence !== null) malformed();
    } else {
      if (!STATUSES.includes(item.reported_status) || typeof item.receipt_sha256 !== 'string' || !SHA.test(item.receipt_sha256)) malformed();
      exactKeys(item.reported_binding, ['request_sha256', 'scope_sha256']);
      if (Object.values(item.reported_binding).some(value => typeof value !== 'string' || !SHA.test(value))) malformed();
      evidence(item.evidence, item.reported_status);
      const receipt = { receipt_schema_version: 'preparation-check-receipt/0.1', check_id: check, status: item.reported_status, binding: item.reported_binding, evidence: item.evidence };
      if (await hash(receipt) !== item.receipt_sha256) fail('PREPARATION_RECEIPT_IDENTITY_MISMATCH', 'A declared check receipt does not match its identity. Export the unchanged report again.');
      status = same(item.reported_binding, { request_sha256: requestSha, scope_sha256: scopeSha }) ? item.reported_status : 'evidence_mismatch';
    }
    if (item.status !== status) malformed();
    checks.push(item);
    if (status === 'evidence_mismatch') blockers.push(blocker('PREPARATION_EVIDENCE_BINDING_MISMATCH', check, 'The receipt belongs to a different request, policy or initialization scope; its outcome is unusable.', 'Recheck the complete current scope and issue a newly bound receipt; retain the earlier evidence.', item.evidence));
    else if (status !== 'passed') blockers.push(blocker(`${check.toUpperCase()}_${status.toUpperCase()}`, check, {
      unknown: 'No usable check outcome is reported; availability and qualification remain unknown.',
      missing: 'The adapter reports a required prerequisite is absent.',
      failed: 'The adapter reports the check failed; this does not establish that inputs are absent.',
    }[status], action, item.evidence));
  }
  if (!forecast) blockers.unshift(blocker('MODE_NOT_IMPLEMENTED', 'mode', 'Continuous simulation remains a proposed mode; no issue population is created.', 'Define and qualify its separate date and preparation contract.'));
  else if (origin === null) blockers.unshift(blocker('INITIALIZATION_NOT_SELECTED', 'initialization_origin', 'No initialization origin is selected, so the complete required history is unknown.', CHECKS.initialization));
  blockers.push(
    blocker('CAMPAIGN_PROTOCOL_NOT_ADMITTED', 'execution_admission', 'Preparation receipts do not verify or authorize an identity-bound execution protocol.', 'Independently admit the scientific/input/runtime/reference identities and fresh bounded run authority before execution.'),
    blocker('EXECUTION_SERVICE_UNAVAILABLE', 'execution_service', 'This offline contract does not submit jobs or provide verified downloads.', 'Connect a separately implemented and authorized execution/result adapter after preparation checks.'),
  );
  const expected = {
    preparation_result_schema_version: 'preparation-result/0.1', artifact_type: 'preparation_result', assessment_kind: 'offline_caller_evidence_aggregation', status: 'blocked',
    preparation_checks_status: forecast && origin !== null && checks.every(item => item.status === 'passed') ? 'all_reported_passed' : 'incomplete',
    planning_supported: forecast, execution_ready: false, release_qualified: false,
    requested_request: request,
    requested_population: { issues_utc: forecast ? assessment.requested_population.issues_utc : null, preview: request.preview, retained_leads: forecast ? request.campaign_translation_proposal.retained_leads : null, population_status: forecast ? 'complete_requested_issue_list' : 'undefined_for_proposed_mode' },
    preparation_binding: binding, checks, blockers,
    evidence_boundary: { receipt_source: 'caller_supplied_separately_from_request', artifacts_read_or_verified: false, verifier_authenticated: false, freshness_established: false, scientific_qualification_established: false, execution_admission_established: false },
  };
  const { identities, ...body } = report;
  if (!same(body, expected)) fail('PREPARATION_REPORT_CONTENT_MISMATCH', 'The preparation report has inconsistent status, checks, blockers, population or evidence limits. Export the complete unchanged backend report.');
  if (await hash(body) !== identities.report_sha256) fail('PREPARATION_REPORT_IDENTITY_MISMATCH', 'The report content does not match its SHA-256 identity. Export the unchanged report again.');
  return freeze(report);
}
