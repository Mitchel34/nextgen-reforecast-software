/** Synthetic Python fixtures. No original sources, acquisition or model calls. */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const probe = `
import json
import sys
from datetime import datetime, timedelta
from ngen_reforecast.preparation.readiness import RECEIPT_VERSION, assess_preparation, preparation_binding
data = json.load(sys.stdin)
request = data["request"]
options = data["options"]
origin = None
if request["study"]["mode"] == "reforecast" and not options.get("noOrigin", False):
    first = datetime.fromisoformat(request["study"]["first_issue_time_utc"].replace("Z", "+00:00"))
    value = first - timedelta(hours=1)
    origin = f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:00:00Z"
binding = preparation_binding(request, origin_time_utc=origin)
receipts = []
for check, status in options.get("statuses", {}).items():
    check_binding = {key: binding[key] for key in ("request_sha256", "scope_sha256")}
    if check in options.get("mismatch", []):
        check_binding["scope_sha256"] = "b" * 64
    receipts.append({"receipt_schema_version": RECEIPT_VERSION, "check_id": check, "status": status,
        "binding": check_binding, "evidence": None if status == "unknown" else {
            "artifact_sha256": "a" * 64, "verifier": "inert-report-test",
            "evidence_class": "synthetic", "detail": options.get("detail", "Synthetic declaration only; no physical source checked."),
        }})
print(json.dumps(assess_preparation(request, origin_time_utc=origin, check_receipts=receipts), ensure_ascii=True))
`;
export function preparationReport(request, options = {}) {
  const child = spawnSync('python3', ['-B', '-c', probe], {
    cwd: root, env: { ...process.env, PYTHONPATH: join(root, 'src'), PYTHONDONTWRITEBYTECODE: '1' },
    input: JSON.stringify({ request, options }), encoding: 'utf8', shell: false,
    timeout: 10_000, maxBuffer: 8 * 1024 * 1024,
  });
  assert.ifError(child.error); assert.equal(child.status, 0, child.stderr);
  return JSON.parse(child.stdout);
}
export function residentAdapterReport() {
  const child = spawnSync('python3', ['-B', '-c', `
import json
from test_forcing_preparation_adapter import ForcingPreparationAdapterTests
fixture = ForcingPreparationAdapterTests()
try:
    fixture.setUp()
    result = fixture.call()
    print(json.dumps({"request": fixture.request, "report": result["readiness_report"], "adapter_evidence": result["adapter_evidence"]}, ensure_ascii=True))
finally:
    fixture.doCleanups()
`], {
    cwd: root, env: { ...process.env, PYTHONPATH: [join(root, 'src'), join(root, 'tests')].join(':'), PYTHONDONTWRITEBYTECODE: '1' },
    encoding: 'utf8', shell: false, timeout: 10_000, maxBuffer: 1024 * 1024,
  });
  assert.ifError(child.error); assert.equal(child.status, 0, child.stderr);
  return JSON.parse(child.stdout);
}
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
export function resignReport(report) {
  const { identities, ...body } = report;
  identities.report_sha256 = createHash('sha256').update(canonical(body)).digest('hex');
  return report;
}
