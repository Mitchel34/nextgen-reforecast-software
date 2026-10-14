# Resident forcing preparation and browser report inspection — 14 October 2026

This local increment implements one actual preparation check for RF-003/007 and WEB-03, supporting UX-02/05: the [forcing adapter](../src/ngen_reforecast/preparation/forcing_adapter.py) calls the existing decoded-forcing validators over explicitly selected resident files, then supplies a bound source-coverage receipt to the [readiness contract](PREPARATION_RESULT_CONTRACT.md). The browser can import, inspect and download that unchanged readiness report. The overnight readiness-contract milestone remains historical at `e0b03a9588670b95224586ade0137f6bd91ab5a4`; its receipt is preserved.

The new path is a bounded operator preparation bridge. Location resolution, automatic acquisition, hosted submission, model execution, recovery and verified scientific archive downloads remain unfinished. Accepting an offline report does not turn a prepared operator bundle into the complete researcher experience.

## Preparation check

```python
import json
from pathlib import Path
from ngen_reforecast.preparation import validate_request
from ngen_reforecast.preparation.readiness import preparation_binding
from ngen_reforecast.preparation.forcing_adapter import check_forcing_preparation

request = validate_request(json.loads(Path("researcher-request.json").read_text()))
origin = "2021-12-01T00:00:00Z"  # Explicit operator selection, not spinup qualification.
binding = preparation_binding(request, origin_time_utc=origin)

# Supply this independently from manifests, using the resolved domain's
# expected axis and identity. These examples are declarations, not resolution.
domain = {
    "evidence_class": "caller_owned_domain_descriptor",
    "binding": {key: binding[key] for key in ("request_sha256", "scope_sha256")},
    "catchment_ids": ["cat-1", "cat-2"],
    "domain_identity_sha256": "<exact SHA-256 of the domain evidence>",
}
result = check_forcing_preparation(
    request, origin_time_utc=origin, domain_descriptor=domain,
    history_manifest_path=Path("prepared/history.json"),
    forecast_manifest_paths={
        "2022-01-01T23:00:00Z": Path("prepared/issue-20220101T23.json"),
        "2022-01-02T00:00:00Z": Path("prepared/issue-20220102T00.json"),
    },
    base_dir=Path("prepared"),
)
# Save the complete readiness_report value for browser inspection. The
# operator can retain adapter_evidence separately as the cited check artifact.
Path("preparation-report.json").write_text(json.dumps(result["readiness_report"], ensure_ascii=True))
```

The example paths, catchments and domain digest must be replaced with the independently established inputs for that exact request. The forecast map must contain only its requested issue keys. The adapter does not infer a domain axis from a manifest or authenticate the caller-owned descriptor. Its SHA-256 binding detects accidental reuse across requests/origins, not a fraudulent mapping.

`check_forcing_preparation` returns `adapter_evidence` plus the unchanged `preparation-result/0.1` shape in `readiness_report`. The adapter artifact binds the request/scope/domain descriptor, each complete forcing validation report, diagnostics and declared bounds under `adapter_identity_sha256`. The source-coverage receipt cites that identity. Save the complete adapter artifact if durable inspectable check evidence is required; the API itself writes no files.

`validate_history` checks the provider interval `[origin, last issue + 18h)` using the external catchment axis. `validate_forecast_issue` checks every issue separately with all 18 source leads. Retaining leads 1–6 changes export selection without reducing those checks. No gap exclusion, imputation, initialization shortening or weather substitution occurs. Existing source/unit/transform and runtime/scientific checks are preserved byte-for-byte.

## Outcomes and bounds

An omitted initialization origin leaves source coverage unknown and reads no forcing files. Unimplemented continuous mode creates no forecast population. Missing manifest selections or a known absent local path produce explicit missing evidence; permission, symlink, placeholder, size, parse, clock/content or concurrent-change refusals remain failed checks. A missing local path does not prove an upstream archive is missing.

All requested manifests must be supplied before partial-study reads begin. At most **two issues**, **32 catchments**, **1,000 history hours**, and **50,000 total expected catchment-hour rows** enter this adapter. An oversized study is blocked before forcing reads and preserves its complete requested population. The twelve-month request therefore still has all 8,760 issues; this adapter does not truncate it to the diagnostic pair.

Manifest preflight is capped at 64 KiB, each payload at 8 MiB, and the total selected payload preflight at 16 MiB. The unchanged validators have their own hard limits of 1 MiB per manifest and 32 MiB per payload; concurrent file growth after preflight can reach those existing read limits before refusal. Metadata is checked before and after validation and again at closeout. A changed or disappearing file prevents a complete-content claim. Caller-owned issue-path mappings are copied only after their bounded size is checked.

The five-second elapsed budget is cooperative between bounded validator operations, not a hard interruption of one call or a resource reservation. It includes the adapter's file-check phase; ordinary input validation and complete readiness-report construction retain their existing bounds. The implementation uses no worker/server, multiprocessing, acquisition or model invocation. This increment's tests ran in small serial batches; host pressure was checked before validation, with pauses required at load 8 or greater or memory free below 20%.

Even when every decoded content check passes, the forcing reports retain source-truth/version, historical-availability and radiation qualification blockers. The broader `source_coverage` check is therefore still failed, with `decoded_content_valid=True` explicitly distinguished in its evidence detail. This means unfinished source qualification, not a failed forecast job. `source_coverage_qualified`, `execution_ready` and release qualification remain false. Other readiness checks stay unknown; no scientific/execution identity or authority is invented.

## Browser display

After reviewing the complete current request, choose **Inspect a preparation report** and import the JSON containing `result["readiness_report"]`. The adapter envelope is a separate artifact and is not imported as a readiness report. No backend service or physical source read occurs in the browser.

The importer caps UTF-8 input at 8 MiB and bounds JSON depth/nodes. It rejects duplicate or unsafe fields, unknown schemas, edited readiness claims, another request/site/retention, shorter populations, policy/scope mismatch, inconsistent check/blocker states, and changed receipt/report hashes. It independently reconstructs the scope and report from the current validated request and the declared receipts. The existing policy-byte pin is tested against both packaged/browser copies; policy changes require an explicit corresponding importer update.

The accessible view displays complete issue counts, full 18-lead preparation requirements, the declared initialization/provider interval, check outcomes, evidence limits and each blocker's next action. Text is rendered with `textContent`. Integrity hashes identify content without authenticating a verifier, inspecting cited artifacts, establishing freshness or admitting execution.

Editing the request, changing mode/example, submitting a newer assessment or selecting another file immediately invalidates the imported report and its download. Late file-read/hash callbacks and stale detached download handlers cannot restore it. The download is the unchanged inspected preparation report; it contains no scientific dataset archive.

## Evidence and remaining work

Targeted tests and independent review are recorded in the [increment receipt](evidence/forcing-preparation-browser-increment-20261014.json). Synthetic resident CSVs exercise actual existing content validators; synthetic DOM checks exercise report display/import/download and asynchronous invalidation. Twelve-month and maximum supported population tests establish scope preservation only. No live participant study or workflow speed/step benchmark is claimed; “50 steps to 10” and “40% faster” remain illustrative.

Next, supply an independently resolved domain and a separately qualified source/version/availability/radiation contract before broadening this adapter. Then implement durable submission/result boundaries under their own admission and resource authority. Physical execution, downloads, spending, credentials/security changes, publication and public push were outside this increment. Existing original research folders, physical fixtures, ledgers and accepted scientific bindings remain preserved.
