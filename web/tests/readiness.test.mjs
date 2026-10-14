/** Browser request to caller-evidence backend contract; synthetic, zero forecasts. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { buildRequest } from '../request.mjs';
import { assessRequest } from '../assessment.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const probe = `
import json
import sys
import hashlib
from datetime import datetime, timedelta
from ngen_reforecast.preparation.readiness import (
    CHECK_IDS, RECEIPT_VERSION, assess_preparation, preparation_binding,
)
request = json.load(sys.stdin)
first = datetime.fromisoformat(request["study"]["first_issue_time_utc"].replace("Z", "+00:00"))
value = first - timedelta(hours=1)
# One synthetic preceding hour tests scope arithmetic only, not spinup adequacy.
origin = f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:00:00Z"
binding = preparation_binding(request, origin_time_utc=origin)
receipts = [{
    "receipt_schema_version": RECEIPT_VERSION, "check_id": check, "status": "passed",
    "binding": {key: binding[key] for key in ("request_sha256", "scope_sha256")},
    "evidence": {"artifact_sha256": "a" * 64, "verifier": "inert-integration-fake",
                 "evidence_class": "synthetic", "detail": "No source or model checked."},
} for check in CHECK_IDS]
report = assess_preparation(request, origin_time_utc=origin, check_receipts=receipts)
population = report["requested_population"]
print(json.dumps({
    "request_sha256": binding["request_sha256"],
    "issues_sha256": hashlib.sha256("\\n".join(population["issues_utc"]).encode()).hexdigest(),
    "preview": population["preview"], "retained_leads": population["retained_leads"],
    "issue_count": len(population["issues_utc"]),
    "first_issue": population["issues_utc"][0], "last_issue": population["issues_utc"][-1],
    "scope": binding["scope"], "status": report["status"],
    "preparation_checks_status": report["preparation_checks_status"],
    "execution_ready": report["execution_ready"], "release_qualified": report["release_qualified"],
    "evidence_boundary": report["evidence_boundary"],
    "blockers": [item["code"] for item in report["blockers"]],
}))
`;

for (const scenario of [
  { name: 'exact two-hour diagnostic metadata window', start: '2022-01-01', end: '2022-01-02', startHour: 23, endHour: 0, count: 2 },
  { name: 'complete two-day study', start: '2022-01-01', end: '2022-01-02', count: 48 },
  { name: 'complete twelve-month single-site planning study', start: '2022-01-01', end: '2022-12-31', count: 8760 },
]) {
  test(`preparation result consumes browser request: ${scenario.name}`, async () => {
    const request = buildRequest({
      identifier_type: 'watershed', identifier: 'Synthetic Ω watershed 🏞️', mode: 'reforecast',
      start_date: scenario.start, end_date: scenario.end,
      start_hour_utc: scenario.startHour, end_hour_utc: scenario.endHour, max_lead_hours: 6,
    });
    const browser = await assessRequest(request);
    const child = spawnSync('python3', ['-B', '-c', probe], {
      cwd: root, env: { ...process.env, PYTHONPATH: join(root, 'src'), PYTHONDONTWRITEBYTECODE: '1' },
      input: JSON.stringify(request), encoding: 'utf8', shell: false,
      timeout: 10_000, maxBuffer: 64 * 1024,
    });
    assert.ifError(child.error);
    assert.equal(child.status, 0, child.stderr);
    const backend = JSON.parse(child.stdout);
    assert.equal(backend.request_sha256, browser.identities.request_sha256);
    const issuesSha = createHash('sha256').update(browser.requested_population.issues_utc.join('\n')).digest('hex');
    assert.equal(backend.issues_sha256, issuesSha);
    assert.equal(backend.issue_count, scenario.count);
    assert.deepEqual(backend.preview, request.preview);
    assert.deepEqual(backend.retained_leads, request.campaign_translation_proposal.retained_leads);
    assert.equal(backend.first_issue, request.preview.first_issue_utc);
    assert.equal(backend.last_issue, request.preview.last_issue_utc);
    assert.equal(backend.scope.final_physical_target_utc, request.preview.last_physical_valid_time_utc);
    assert.deepEqual(backend.scope.required_source_leads, { min: 1, max: 18 });
    assert.equal(backend.preparation_checks_status, 'all_reported_passed');
    assert.equal(backend.status, 'blocked');
    assert.equal(backend.execution_ready, false);
    assert.equal(backend.release_qualified, false);
    assert.equal(backend.evidence_boundary.artifacts_read_or_verified, false);
    assert.equal(backend.evidence_boundary.execution_admission_established, false);
    assert.deepEqual(backend.blockers, ['CAMPAIGN_PROTOCOL_NOT_ADMITTED', 'EXECUTION_SERVICE_UNAVAILABLE']);
  });
}
