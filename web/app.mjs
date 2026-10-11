import { buildRequest } from './request.mjs';
const form = document.querySelector('#study-form');
const content = document.querySelector('#review-content');
const empty = document.querySelector('#review-empty');
const error = document.querySelector('#form-error');
const title = document.querySelector('#review-title');
let currentRequest = null;
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
  currentRequest = null;
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
  document.querySelector('#period-label').textContent = forecast ? 'Historical issue dates' : 'Historical dates';
  document.querySelector('#date-help').textContent = forecast ? 'Proposed interpretation: issue a forecast every hour on each selected day, including both dates, in UTC.' : 'Continuous simulation is proposed. You can record these dates, but their interpretation and execution contract remain unresolved.';
}
form.addEventListener('input', resetReview);
form.addEventListener('change', () => { resetReview(); updateMode(); });
document.querySelector('#use-example').addEventListener('click', () => {
  form.elements.identifier_type.value = 'usgs'; form.elements.identifier.value = '03479000';
  form.elements.mode.value = 'reforecast'; form.elements.start_date.value = '2022-01-01';
  form.elements.end_date.value = '2022-01-02'; form.elements.max_lead_hours.value = '18';
  resetReview(); updateMode(); form.elements.identifier.focus();
});
function displayTime(value) { return value.replace('T', ' ').replace(':00:00Z', ':00 UTC'); }
function addTime(list, label, value) {
  const row = el('div'); row.append(el('dt', label), el('dd', displayTime(value))); list.append(row);
}
function render(request) {
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
    addTime(times, 'First issue · selected first day', preview.first_issue_utc);
    addTime(times, 'Last issue · selected last day', preview.last_issue_utc);
    addTime(times, 'First retained target · first issue + 1 h', preview.first_retained_valid_time_utc);
    addTime(times, `Last retained target · last issue + ${request.study.requested_max_lead_hours} h`, preview.last_retained_valid_time_utc);
    content.append(times);
    content.append(el('p', `Retain leads 1–${request.study.requested_max_lead_hours} h at hourly steps. Targets extend beyond the issue period. These row counts describe the request; they are not generated data.`, 'review-lede'));
    const defaults = el('details', undefined, 'defaults'); defaults.append(el('summary', 'Inspect proposed defaults and time interpretation'));
    defaults.append(el('p', 'Date meaning is an implementation proposal for review: both selected UTC issue days are included, with one issue per hour. No local-time or daylight-saving conversion is applied.'));
    defaults.append(el('p', `Exclusive issue boundary: ${displayTime(request.campaign_translation_proposal.issue_schedule.stop_time_utc_exclusive)}. The proposed engine profile still integrates all 18 forecast hours (${preview.generated_rows_per_location.toLocaleString('en-US')} rows per location); retaining fewer leads does not reduce that integration.`));
    defaults.append(el('p', `Full physical targets extend through ${displayTime(preview.last_physical_valid_time_utc)}. All 18 source forcing leads would still be needed for every issue. Earlier initialization data would also be required; its start is not decided.`));
    defaults.append(el('p', 'The demonstration date selection creates hourly issues on whole days. It does not reproduce the separately defined two-issue Watauga scientific benchmark. Model parameters, initialization, source availability and scientific qualification remain unresolved.'));
    content.append(defaults);
  } else {
    content.append(el('p', `Requested dates: ${request.study.first_date} through ${request.study.last_date}. Continuous simulation is a proposed mode; no issue schedule or engine campaign is generated.`, 'review-lede'));
  }
  content.append(el('h3', 'What preparation must resolve', 'review-section-title'));
  const blockers = el('ul', undefined, 'blockers');
  request.preparation.blockers.forEach(blocker => blockers.append(el('li', blocker.message)));
  content.append(blockers, el('p', 'Runtime, cost and storage estimates are unavailable until a supported request can be prepared and measured.', 'review-lede'));
  const download = el('button', 'Download study request', 'primary'); download.type = 'button'; download.id = 'download-request';
  const downloadStatus = el('p', '', 'save-status'); downloadStatus.setAttribute('role', 'status');
  download.addEventListener('click', () => {
    if (!currentRequest) return;
    const blob = new Blob([`${JSON.stringify(currentRequest, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = el('a'); anchor.href = url; anchor.download = 'nextgen-study-request.json';
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadStatus.textContent = 'Download requested. The file contains your study request and unresolved preparation steps. No model run has started.';
    setStep('save');
  });
  content.append(download, el('p', 'The JSON file is a portable request for future preparation. It contains no model outputs, verified dataset or executable campaign. Editing any field above clears this review so you cannot download a stale request.', 'download-note'), downloadStatus);
}
form.addEventListener('submit', event => {
  event.preventDefault(); resetReview();
  try {
    currentRequest = buildRequest(Object.fromEntries(new FormData(form)));
    render(currentRequest); setStep('review'); document.querySelector('#review').focus();
  } catch (problem) {
    error.textContent = problem.message; error.hidden = false;
    const field = form.elements[problem.field];
    if (field?.focus) { field.setAttribute('aria-invalid', 'true'); field.setAttribute('aria-errormessage', 'form-error'); field.focus(); }
  }
});
