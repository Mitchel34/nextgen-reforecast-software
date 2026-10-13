/** Local researcher request contract. No resolver, source check or model runs here. */
import rawPolicy from './request-policy.json' with { type: 'json' };
export const REQUEST_POLICY = Object.freeze({ ...rawPolicy, retained_leads: Object.freeze({ ...rawPolicy.retained_leads }) });
export const CONTRACT_VERSION = REQUEST_POLICY.request_schema_version;
const HOUR = 3_600_000;
export const MAX_ISSUES = REQUEST_POLICY.max_issues; // Offline campaign issue ceiling, not service capacity.
export const MAX_HISTORY_HOURS = REQUEST_POLICY.max_history_hours;
export class RequestError extends Error {
  constructor(field, message) { super(message); this.name = 'RequestError'; this.field = field; }
}
function dateMs(value, field) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new RequestError(field, 'Choose a complete date.');
  }
  const ms = Date.parse(`${value}T00:00:00Z`);
  if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0, 10) !== value || Number(value.slice(0, 4)) < 1) {
    throw new RequestError(field, 'Enter a real calendar date.');
  }
  return ms;
}
const utc = ms => new Date(ms).toISOString().replace('.000Z', 'Z');
function issueHour(value, field, fallback) {
  if (value === undefined) return fallback;
  const hour = typeof value === 'number' ? value : typeof value === 'string' && /^\d{1,2}$/.test(value) ? Number(value) : NaN;
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) throw new RequestError(field, 'Choose a whole UTC hour from 00 to 23.');
  return hour;
}

export function buildRequest(input) {
  if (!input || typeof input !== 'object') throw new RequestError('identifier', 'Enter a study location.');
  if (!['usgs', 'nwm', 'watershed'].includes(input.identifier_type)) {
    throw new RequestError('identifier_type', 'Choose USGS gauge, NWM reach or watershed.');
  }
  const identifier = typeof input.identifier === 'string' ? input.identifier.trim() : '';
  if (!identifier || identifier.length > REQUEST_POLICY.max_identifier_length) throw new RequestError('identifier', 'Enter an identifier or watershed name, up to 120 characters.');
  if (input.identifier_type !== 'watershed' && !/^\d+$/.test(identifier)) {
    throw new RequestError('identifier', 'Use the numeric identifier. Leading zeros are preserved.');
  }
  if (!['reforecast', 'continuous_simulation'].includes(input.mode)) throw new RequestError('mode', 'Choose whether you want forecast leads.');
  const firstDay = dateMs(input.start_date, 'start_date');
  const lastDay = dateMs(input.end_date, 'end_date');
  if (lastDay < firstDay) throw new RequestError('end_date', 'The last issue date must be on or after the first date.');
  const isForecast = input.mode === 'reforecast';
  const firstHour = isForecast ? issueHour(input.start_hour_utc, 'start_hour_utc', REQUEST_POLICY.default_first_hour_utc) : null;
  const lastHour = isForecast ? issueHour(input.end_hour_utc, 'end_hour_utc', REQUEST_POLICY.default_last_hour_utc) : null;
  const start = firstDay + (firstHour ?? 0) * HOUR;
  const lastIssue = lastDay + (lastHour ?? 23) * HOUR;
  if (lastIssue < start) throw new RequestError('end_hour_utc', 'The last issue hour must be on or after the first issue hour.');
  if (isForecast && input.start_date === '0001-01-01' && firstHour === 0) throw new RequestError('start_date', 'This issue time leaves no representable earlier initialization time. Choose a later UTC hour or date.');
  const stop = lastIssue + HOUR;
  const count = (stop - start) / HOUR;
  const horizon = REQUEST_POLICY.forecast_horizon_hours;
  if (count > MAX_ISSUES || (isForecast && count + horizon > MAX_HISTORY_HOURS)) throw new RequestError('end_date', 'This period exceeds the offline campaign bounds after allowing for initialization and 18-hour forecasts. Shorten it; these bounds do not establish data coverage.');
  // Both the exclusive issue boundary and full physical targets must fit engine UTC syntax.
  if (new Date(stop + (horizon - 1) * HOUR).getUTCFullYear() > 9999) throw new RequestError('end_date', 'This date extends beyond the supported calendar representation.');
  let maxLead = null;
  if (input.mode === 'reforecast') {
    maxLead = typeof input.max_lead_hours === 'number' ? input.max_lead_hours :
      typeof input.max_lead_hours === 'string' && /^\d+$/.test(input.max_lead_hours) ? Number(input.max_lead_hours) : NaN;
    if (!Number.isInteger(maxLead) || maxLead < REQUEST_POLICY.retained_leads.min || maxLead > REQUEST_POLICY.retained_leads.max) {
      throw new RequestError('max_lead_hours', 'Choose a whole number of hours from 1 to 18. Other horizons need a separately qualified profile.');
    }
  }
  const demo = input.identifier_type === 'usgs' && identifier === '03479000';
  const blockers = [
    { code: 'LOCATION_NOT_RESOLVED', message: demo ? 'The Watauga example is a documented demonstration. A live outlet and upstream domain have not been resolved or confirmed.' : 'A live location resolver is not connected. This identifier has not been matched to an outlet or upstream domain.' },
    { code: 'COVERAGE_UNKNOWN', message: 'Historical and forecast input coverage has not been checked for these dates. Eligible dates and gaps are unknown.' },
    { code: 'SCIENTIFIC_PROFILE_UNQUALIFIED', message: 'Model, parameter and initialization defaults still require scientific qualification. An initialization start has not been selected.' },
    { code: 'EXECUTION_SERVICE_UNAVAILABLE', message: 'Data preparation, Linux execution and verified result downloads are not connected to this prototype.' },
  ];
  if (!isForecast) blockers.unshift({ code: 'MODE_NOT_IMPLEMENTED', message: 'Continuous historical simulation is a proposed mode. Its date interpretation and execution contract are not implemented.' });
  const schedule = isForecast ? { start_time_utc: utc(start), stop_time_utc_exclusive: utc(stop), cadence_hours: REQUEST_POLICY.issue_cadence_hours } : null;
  return {
    request_schema_version: CONTRACT_VERSION,
    artifact_type: 'researcher_request',
    interface_stage: 'prototype',
    intended_evaluation_level: 'UX_E1',
    user_study_conducted: false,
    execution_ready: false,
    location: { identifier_type: input.identifier_type, submitted_identifier: identifier, resolution_status: 'unresolved', demonstration: demo ? { label: 'Watauga example', usgs_gauge: '03479000', catchment_count: 31, nexus: '1017693', source: 'docs/FIRST_PHYSICAL_EXPERIMENT.md', is_live_resolution: false } : null },
    study: { mode: input.mode, first_date: input.start_date, last_date: input.end_date, date_semantics: isForecast ? 'inclusive_utc_issue_window_proposal' : 'unresolved_continuous_simulation_dates', time_zone: 'UTC', requested_max_lead_hours: maxLead, first_issue_hour_utc: firstHour, last_issue_hour_utc: lastHour, first_issue_time_utc: isForecast ? utc(start) : null, last_issue_time_utc: isForecast ? utc(lastIssue) : null },
    campaign_translation_proposal: isForecast ? { schema_version: '1.1', issue_schedule: schedule, horizon_hours: horizon, retained_leads: { min_lead_hours: 1, max_lead_hours: maxLead, projection: 'export' } } : null,
    preview: isForecast ? { issue_count: count, first_issue_utc: utc(start), last_issue_utc: utc(lastIssue), first_retained_valid_time_utc: utc(start + HOUR), last_retained_valid_time_utc: utc(lastIssue + maxLead * HOUR), last_physical_valid_time_utc: utc(lastIssue + horizon * HOUR), retained_rows_per_location: count * maxLead, generated_rows_per_location: count * horizon, output_timestep_hours: 1 } : null,
    preparation: { coverage_status: 'unknown', qualified_profile: null, initialization_origin_utc: null, runtime_estimate: null, cost_estimate: null, blockers },
  };
}
