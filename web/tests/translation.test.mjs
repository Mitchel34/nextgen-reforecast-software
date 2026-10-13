/** Browser-to-engine arithmetic only. No acquired assets, native model or file writes. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { buildRequest } from '../request.mjs';

const repoRoot = fileURLToPath(new URL('../../', import.meta.url));

// One hour before the first issue is deliberately SYNTHETIC test scaffolding.
// It proves only clock/schema compatibility, not a selected or adequate
// scientific initialization period. All assets are absent and unchecked.
const pythonProbe = `
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from ngen_reforecast.campaign import normalize_campaign, plan_campaign, iter_expected_rows
from ngen_reforecast.preparation import validate_request, translate_request

if sys.version_info < (3, 11):
    raise SystemExit("Browser integration tests require Python 3.11 or newer")

def utc(value):
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:00:00Z"

request = validate_request(json.load(sys.stdin))
first_issue = datetime.fromisoformat(request["study"]["first_issue_time_utc"].replace("Z", "+00:00"))
synthetic_origin = first_issue - timedelta(hours=1)
# This is internal synthetic metadata, never a verified location or scientific origin.
preparation = {
    "evidence_class": "server_owned_preparation_descriptor",
    "origin_time_utc": utc(synthetic_origin),
    "location_binding": {"identifier_type": request["location"]["identifier_type"],
                         "submitted_identifier": request["location"]["submitted_identifier"], "status": "declared_candidate"},
    "domains": [{"domain_id": "synthetic", "locations": [{"location_id": "synthetic", "reach_id": "1"}], "assets": []}],
    "resources": {"host_cpus": 2, "parent_cpus": 1, "cpus_per_branch": 1,
                  "max_concurrent_branches": 1, "wall_time_seconds": 1,
                  "max_asset_bytes": 1, "max_total_asset_bytes": 1},
}
spec = translate_request(request, preparation, campaign_id="browser-arithmetic-fixture")
normalized = normalize_campaign(spec)
plan = plan_campaign(normalized, Path.cwd(), check_assets=False)
# Each fixed case has at most 72 issues (1296 generated keys), so these
# expectation-ledger materializations are intentionally small and bounded.
generated = list(iter_expected_rows(normalized, kind="generated"))
retained = list(iter_expected_rows(normalized, kind="retained"))
print(json.dumps({
    "schema_version": normalized["schema_version"],
    "issue_count": len(normalized["issue_times_utc"]),
    "first_issue_utc": normalized["issue_times_utc"][0],
    "last_issue_utc": normalized["issue_times_utc"][-1],
    "first_retained_valid_time_utc": retained[0]["valid_time_utc"],
    "last_retained_valid_time_utc": retained[-1]["valid_time_utc"],
    "last_physical_valid_time_utc": generated[-1]["valid_time_utc"],
    "generated_rows_per_location": len(generated),
    "retained_rows_per_location": len(retained),
    "plan_generated_rows": plan["totals"]["generated_forecast_rows"],
    "plan_retained_rows": plan["totals"]["retained_forecast_rows"],
    "retained_leads": normalized["retained_leads"],
    "execution_horizon_hours": plan["time_contract"]["execution_horizon_hours"],
    "required_source_lead_hours": plan["time_contract"]["required_source_lead_hours"],
    "synthetic_antecedent_hours": plan["time_contract"]["antecedent_history_hours_at_first_issue"],
    "hashed_bytes": plan["totals"]["hashed_bytes"],
    "execution_ready": plan["execution_ready"],
    "blocker_codes": sorted({item["code"] for item in plan["blockers"]}),
}))
`;

const scenarios = [
  {
    name: 'minimum supported whole issue day retains year 0001',
    start: '0001-01-02', end: '0001-01-02', lead: 1, issues: 24,
    lastRetained: '0001-01-03T00:00:00Z', lastPhysical: '0001-01-03T17:00:00Z',
  },
  {
    name: 'year 0099 crosses into 0100 without a 1900 offset',
    start: '0099-12-31', end: '0100-01-01', lead: 6, issues: 48,
    lastRetained: '0100-01-02T05:00:00Z', lastPhysical: '0100-01-02T17:00:00Z',
  },
  {
    name: 'leap day preserves all three UTC issue days',
    start: '2024-02-28', end: '2024-03-01', lead: 18, issues: 72,
    lastRetained: '2024-03-02T17:00:00Z', lastPhysical: '2024-03-02T17:00:00Z',
  },
  {
    name: 'daylight-saving transition preserves 72 hourly UTC issues',
    start: '2024-03-09', end: '2024-03-11', lead: 6, issues: 72,
    lastRetained: '2024-03-12T05:00:00Z', lastPhysical: '2024-03-12T17:00:00Z',
  },
  {
    name: 'upper calendar boundary leaves room for all 18 target hours',
    start: '9999-12-30', end: '9999-12-30', lead: 18, issues: 24,
    lastRetained: '9999-12-31T17:00:00Z', lastPhysical: '9999-12-31T17:00:00Z',
  },
  {
    name: 'exact two-issue diagnostic window has no whole-day minimum',
    start: '2022-01-01', end: '2022-01-02', startHour: 23, endHour: 0, lead: 6, issues: 2,
    lastRetained: '2022-01-02T06:00:00Z', lastPhysical: '2022-01-02T18:00:00Z',
  },
  {
    name: 'earliest representable one-issue window preserves an earlier initialization hour',
    start: '0001-01-01', end: '0001-01-01', startHour: 1, endHour: 1, lead: 1, issues: 1,
    lastRetained: '0001-01-01T02:00:00Z', lastPhysical: '0001-01-01T19:00:00Z',
  },
];

for (const scenario of scenarios) {
  test(`browser to Python campaign: ${scenario.name}`, () => {
    const request = buildRequest({
      identifier_type: 'watershed', identifier: 'Synthetic arithmetic fixture', mode: 'reforecast',
      start_date: scenario.start, end_date: scenario.end, max_lead_hours: scenario.lead,
      start_hour_utc: scenario.startHour, end_hour_utc: scenario.endHour,
    });
    const child = spawnSync('python3', ['-B', '-c', pythonProbe], {
      cwd: repoRoot,
      env: { ...process.env, PYTHONPATH: join(repoRoot, 'src'), PYTHONDONTWRITEBYTECODE: '1' },
      input: JSON.stringify(request), encoding: 'utf8', shell: false,
      timeout: 10_000, maxBuffer: 64 * 1024,
    });
    assert.ifError(child.error);
    assert.equal(child.status, 0, `Python contract probe failed: ${child.stderr}`);
    const engine = JSON.parse(child.stdout);

    const expected = {
      issue_count: scenario.issues,
      first_issue_utc: `${scenario.start}T${String(scenario.startHour ?? 0).padStart(2, '0')}:00:00Z`,
      last_issue_utc: `${scenario.end}T${String(scenario.endHour ?? 23).padStart(2, '0')}:00:00Z`,
      first_retained_valid_time_utc: request.preview.first_retained_valid_time_utc,
      last_retained_valid_time_utc: scenario.lastRetained,
      last_physical_valid_time_utc: scenario.lastPhysical,
      generated_rows_per_location: scenario.issues * 18,
      retained_rows_per_location: scenario.issues * scenario.lead,
    };
    for (const [field, value] of Object.entries(expected)) {
      assert.equal(engine[field], value, `Python ${field}`);
      assert.equal(request.preview[field], value, `browser ${field}`);
    }
    assert.equal(engine.schema_version, '1.1');
    assert.equal(engine.plan_generated_rows, expected.generated_rows_per_location);
    assert.equal(engine.plan_retained_rows, expected.retained_rows_per_location);
    assert.deepEqual(engine.retained_leads, { min_lead_hours: 1, max_lead_hours: scenario.lead, projection: 'export' });
    assert.equal(engine.execution_horizon_hours, 18);
    assert.deepEqual(engine.required_source_lead_hours, { min: 1, max: 18 });
    assert.equal(engine.synthetic_antecedent_hours, 1);
    assert.equal(engine.hashed_bytes, 0);
    assert.equal(engine.execution_ready, false);
    assert.equal(request.execution_ready, false);
    assert.deepEqual(engine.blocker_codes, ['asset_checks_disabled', 'asset_role_missing', 'runtime_not_qualified']);
  });
}
