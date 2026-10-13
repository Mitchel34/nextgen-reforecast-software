import { buildRequest } from './request.mjs';
import { assessRequest } from './assessment.mjs';
const form = document.querySelector('#study-form');
const content = document.querySelector('#review-content');
const empty = document.querySelector('#review-empty');
const error = document.querySelector('#form-error');
const title = document.querySelector('#review-title');
let currentRequest = null;
let currentAssessment = null;
let reviewRevision = 0;
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function setStep(name) {
  for (const item of document.querySelectorAll('.steps span')) item.removeAttribute('aria-current');
  document.querySelector(`#step-${name}`).setAttribute('aria-current', 'step');
}
function resetReview() {
  reviewRevision += 1;
  currentRequest = null;
  currentAssessment = null;
  content.replaceChildren(); content.hidden = true; empty.hidden = false;
  title.textContent = 'A clear picture before preparation.';
  error.hidden = true;
  form.querySelectorAll('[aria-invalid]').forEach(input => { input.removeAttribute('aria-invalid'); input.removeAttribute('aria-errormessage'); });
  setStep('define');
}
function updateMode() {
  const forecast = form.elements.mode.value === 'reforecast';
  document.querySelector('#lead-fields').hidden = !forecast;
  document.querySelector('#max_lead_hours').disabled = !forecast;
  document.querySelector('#issue-time-fields').hidden = !forecast;
  form.elements.start_hour_utc.disabled = !forecast;
  form.elements.end_hour_utc.disabled = !forecast;
  document.querySelector('#period-label').textContent = forecast ? 'Historical issue period' : 'Historical dates';
  document.querySelector('#date-help').textContent = forecast ? 'Request hourly issues between the first and last selected UTC times, including both endpoints. Dates default to whole days; exact endpoint hours are optional.' : 'Continuous simulation is proposed. You can record these dates, but their interpretation and execution contract remain unresolved.';
}
form.addEventListener('input', resetReview);
form.addEventListener('change', () => { resetReview(); updateMode(); });
document.querySelector('#use-example').addEventListener('click', () => {
  form.elements.identifier_type.value = 'usgs'; form.elements.identifier.value = '03479000';
  form.elements.mode.value = 'reforecast'; form.elements.start_date.value = '2022-01-01';
  form.elements.end_date.value = '2022-01-02'; form.elements.max_lead_hours.value = '18';
  form.elements.start_hour_utc.value = '0'; form.elements.end_hour_utc.value = '23';
  resetReview(); updateMode(); form.elements.identifier.focus();
});
document.querySelector('#use-diagnostic-example').addEventListener('click', () => {
  form.elements.identifier_type.value = 'usgs'; form.elements.identifier.value = '03479000';
  form.elements.mode.value = 'reforecast'; form.elements.start_date.value = '2022-01-01';
  form.elements.end_date.value = '2022-01-02'; form.elements.start_hour_utc.value = '23';
  form.elements.end_hour_utc.value = '0'; form.elements.max_lead_hours.value = '18';
  resetReview(); updateMode(); form.elements.identifier.focus();
});
function displayTime(value) { return value.replace('T', ' ').replace(':00:00Z', ':00 UTC'); }
function addTime(list, label, value) {
  const row = el('div'); row.append(el('dt', label), el('dd', displayTime(value))); list.append(row);
}
function render(request, assessment, revision) {
  content.replaceChildren(); empty.hidden = true; content.hidden = false;
  title.textContent = 'Your study request';
  content.append(el('span', 'Preparation is blocked · request only', 'review-badge'));
  const demo = request.location.demonstration;
  content.append(el('p', demo ? 'Watauga example' : `${request.location.identifier_type.toUpperCase()}: ${request.location.submitted_identifier}`, 'location-title'));
  content.append(el('p', demo ? 'USGS 03479000 · 31 catchments in the documented example. This is not a live location match or a confirmed study boundary.' : 'This identifier has not been resolved. No outlet or study boundary has been confirmed.', 'review-lede'));
  if (request.preview) {
    const preview = request.preview; const stats = el('div', undefined, 'stat-row');
    const issues = el('div', preview.issue_count.toLocaleString('en-US'), 'stat'); issues.append(el('small', 'hourly forecast issues'));
    const rows = el('div', preview.retained_rows_per_location.toLocaleString('en-US'), 'stat'); rows.append(el('small', 'planned retained rows per location'));
    stats.append(issues, rows); content.append(stats);
    const times = el('dl', undefined, 'times');
    addTime(times, 'First selected issue · UTC', preview.first_issue_utc);
    addTime(times, 'Last selected issue · UTC', preview.last_issue_utc);
    addTime(times, 'First retained target · first issue + 1 h', preview.first_retained_valid_time_utc);
    addTime(times, `Last retained target · last issue + ${request.study.requested_max_lead_hours} h`, preview.last_retained_valid_time_utc);
    content.append(times);
    content.append(el('p', `Retain leads 1–${request.study.requested_max_lead_hours} h at hourly steps. Targets extend beyond the issue period. These row counts describe the request; they are not generated data.`, 'review-lede'));
    const defaults = el('details', undefined, 'defaults'); defaults.append(el('summary', 'Inspect proposed defaults and time interpretation'));
    defaults.append(el('p', 'The request includes every hourly issue between the selected first and last UTC times. Whole-day defaults are 00:00 on the first date and 23:00 on the last. No local-time or daylight-saving conversion is applied.'));
    defaults.append(el('p', `Exclusive issue boundary: ${displayTime(request.campaign_translation_proposal.issue_schedule.stop_time_utc_exclusive)}. The proposed engine profile still integrates all 18 forecast hours (${preview.generated_rows_per_location.toLocaleString('en-US')} rows per location); retaining fewer leads does not reduce that integration.`));
    defaults.append(el('p', `Full physical targets extend through ${displayTime(preview.last_physical_valid_time_utc)}. All 18 source forcing leads would still be needed for every issue. Earlier initialization data would also be required; its start is not decided.`));
    defaults.append(el('p', 'The whole-day example preserves all 48 hourly issues. An explicitly selected two-issue window can match the diagnostic clock without changing the whole-day request automatically. Model parameters, initialization, source availability and scientific qualification remain unresolved.'));
    content.append(defaults);
  } else {
    content.append(el('p', `Requested dates: ${request.study.first_date} through ${request.study.last_date}. Continuous simulation is a proposed mode; no issue schedule or engine campaign is generated.`, 'review-lede'));
  }
  content.append(el('h3', 'Request and diagnostic compatibility', 'review-section-title'));
  if (Number.isInteger(assessment.requested_population?.issue_count)) {
    const population = assessment.requested_population;
    const profile = assessment.diagnostic_profile;
    content.append(el('p', `Your complete request contains ${population.issue_count.toLocaleString('en-US')} hourly issues. The existing Watauga diagnostic has ${profile.issue_times_utc.length} exact issues. No requested issue has been removed.`, 'review-lede'));
    content.append(el('p', assessment.diagnostic_profile_match ? 'The requested issue clocks, submitted identifier and forecast horizon match the diagnostic metadata. This is a compatibility check, not verified input preparation or execution authorization.' : 'The complete schedule is supported for offline planning. Executing it requires a profile, inputs, references and a bounded run protocol qualified for that full scope.', 'review-lede'));
    const profileTimes = el('dl', undefined, 'times');
    profile.issue_times_utc.forEach((time, index) => addTime(profileTimes, `Diagnostic issue ${index + 1}`, time));
    content.append(profileTimes);
  } else {
    content.append(el('p', 'Continuous simulation is still a proposed mode. No forecast issue list, executable campaign or implied zero-hour forecast is created.', 'review-lede'));
  }
  content.append(el('h3', 'What preparation must resolve', 'review-section-title'));
  const blockers = el('ul', undefined, 'blockers');
  assessment.blockers.forEach(blocker => blockers.append(el('li', blocker.message)));
  content.append(blockers, el('p', 'Runtime, cost and storage estimates are unavailable until a supported request can be prepared and measured.', 'review-lede'));
  const download = el('button', 'Download study request', 'primary'); download.type = 'button'; download.id = 'download-request';
  const downloadStatus = el('p', '', 'save-status'); downloadStatus.setAttribute('role', 'status');
  download.addEventListener('click', () => {
    if (reviewRevision !== revision || currentRequest !== request || currentAssessment !== assessment) return;
    const blob = new Blob([`${JSON.stringify(request, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = el('a'); anchor.href = url; anchor.download = 'nextgen-study-request.json';
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadStatus.textContent = 'Download requested. The file contains your study request and unresolved preparation steps. No model run has started.';
    setStep('save');
  });
  content.append(download, el('p', 'The JSON file is a portable request for future preparation. It contains no model outputs, verified dataset or executable campaign. Editing any field above clears this review so you cannot download a stale request.', 'download-note'), downloadStatus);
  const assessmentDownload = el('button', 'Download complete request assessment', 'text-button');
  assessmentDownload.type = 'button'; assessmentDownload.id = 'download-assessment';
  assessmentDownload.addEventListener('click', () => {
    if (reviewRevision !== revision || currentRequest !== request || currentAssessment !== assessment) return;
    const blob = new Blob([`${JSON.stringify(assessment, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = el('a'); anchor.href = url; anchor.download = 'nextgen-request-assessment.json';
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadStatus.textContent = 'Assessment download requested. It preserves the original request, every requested issue and explicit limitations. No campaign has been submitted.';
    setStep('save');
  });
  content.append(assessmentDownload, el('p', 'Assessment hashes bind this request and report for inspection. They do not authenticate a sender or authorize model execution.', 'download-note'));
}
form.addEventListener('submit', async event => {
  event.preventDefault(); resetReview();
  const revision = reviewRevision;
  try {
    const request = buildRequest(Object.fromEntries(new FormData(form)));
    title.textContent = 'Assessing your complete request.';
    const assessment = await assessRequest(request);
    if (reviewRevision !== revision) return;
    currentRequest = request; currentAssessment = assessment;
    render(request, assessment, revision); setStep('review'); document.querySelector('#review').focus();
  } catch (problem) {
    if (reviewRevision !== revision) return;
    currentRequest = null; currentAssessment = null;
    content.replaceChildren(); content.hidden = true; empty.hidden = false;
    title.textContent = 'A clear picture before preparation.';
    error.textContent = problem.message; error.hidden = false;
    const field = form.elements[problem.field];
    if (field?.focus) { field.setAttribute('aria-invalid', 'true'); field.setAttribute('aria-errormessage', 'form-error'); field.focus(); }
  }
});
