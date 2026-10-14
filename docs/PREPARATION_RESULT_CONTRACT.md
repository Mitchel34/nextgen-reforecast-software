# Preparation result contract — 14 October 2026

The pure Python [readiness interface](../src/ngen_reforecast/preparation/readiness.py) reports what a preparation adapter says it has checked for one complete researcher request. It returns structured, actionable blockers while preserving the requested site, every issue hour and the full physical preparation scope. This increment supports the site → period → preparation part of the researcher journey; execution, verification and archive download still require their separate adapters and admission.

The interface reads only the packaged request policy. It performs no location resolution, acquisition, physical asset inspection, native forecast, execution admission, worker submission or archive operation. Caller evidence never authenticates the named verifier, proves an artifact's contents or establishes its freshness. A receipt labeled `verification_receipt` is still a caller declaration at this boundary.

## API and schemas

The existing [shared request contract](BROWSER_REQUEST_CONTRACT.md) and [version 0.2 implementation](ASSESSMENT_INTERFACE_IMPLEMENTATION_2026-10-13.md) remain the input authority. Requests are revalidated from their location and study fields before any report is built. Added request fields, edited previews and readiness assertions are rejected; check receipts must be supplied separately from the researcher request.

```python
from hashlib import sha256
from ngen_reforecast.preparation import normalize_request
from ngen_reforecast.preparation.readiness import (
    RECEIPT_VERSION, assess_preparation, preparation_binding,
)

request = normalize_request({
    "identifier_type": "usgs", "identifier": "03479000",
    "mode": "reforecast", "start_date": "2022-01-01",
    "end_date": "2022-12-31", "max_lead_hours": 6,
})
origin = "2021-12-01T00:00:00Z"  # Explicit selection; no spinup qualification.
binding = preparation_binding(request, origin_time_utc=origin)
receipt = {
    "receipt_schema_version": RECEIPT_VERSION,
    "check_id": "source_coverage",
    "status": "failed",
    "binding": {key: binding[key] for key in ("request_sha256", "scope_sha256")},
    "evidence": {
        "artifact_sha256": sha256(b"synthetic coverage example").hexdigest(),
        "verifier": "documentation-example",
        "evidence_class": "synthetic",
        "detail": "Synthetic failure example; no physical sources inspected.",
    },
}
report = assess_preparation(request, origin_time_utc=origin,
                            check_receipts=[receipt])
assert len(report["requested_population"]["issues_utc"]) == 8760
assert report["execution_ready"] is False
```

`preparation_binding(serialized_request, *, origin_time_utc=None)` returns `request_sha256`, `scope_sha256` and the complete `scope`. An adapter obtains these identities for its exact request and selected origin, then binds each check receipt to both hashes. `assess_preparation(serialized_request, *, origin_time_utc=None, check_receipts=None)` returns detached JSON under `preparation-result/0.1`. Receipt schema version is `preparation-check-receipt/0.1`.

A receipt has exactly five fields: `receipt_schema_version`, `check_id`, `status`, `binding` and `evidence`. Binding has exactly `request_sha256` and `scope_sha256`, both lowercase 64-character SHA-256 strings. Unknown outcomes require `evidence: null`. Every other receipt outcome requires exactly `artifact_sha256`, `verifier`, `evidence_class` and `detail`; the artifact hash must be lowercase SHA-256, and `verifier` and `detail` must be nonblank strings of at most 2,048 characters. Supported evidence classes are `synthetic`, `declared_metadata` and `verification_receipt`. Their labels do not grant trust or admission.

The bounded receipt list admits at most one receipt for each of the following seven checks, in the fixed report order:

| Check ID | Required adapter work |
|---|---|
| `location_resolution` | Resolve and version the submitted outlet, gauge/reach mapping and complete upstream domain without substituting a watershed |
| `initialization` | Select and qualify an origin before the first issue, with its scientific justification |
| `source_coverage` | Check initialization/history and every issue's full 18-hour forcing window, including source gaps and units |
| `input_bundle` | Prepare and content-verify the complete input set, binding sources, domain, configuration and transformations |
| `runtime_identity` | Verify exact supported runtime source, binaries, components and routing identities |
| `reference_set` | Bind qualified independent references to the full requested population and its scientific/input/runtime identities |
| `scientific_profile` | Qualify parameters, forcing/time semantics and initialization for this study; diagnostic metadata is insufficient |

## Scope and identity

`request_sha256` covers the complete validated request, including location, issue dates/hours and retained-lead selection. `scope_sha256` covers a scope that embeds that request hash, the exact packaged policy-byte hash, submitted location, mode, explicit initialization origin, required history interval, full issue schedule/count, 18-hour horizon, source leads 1–18 and final physical target. Receipts for another site, shorter issue population, changed origin or policy/scope identity cannot satisfy the current request. The earlier evidence remains visible with its reported binding and receipt hash.

For reforecasts, an origin must be a real exact hourly UTC timestamp `YYYY-MM-DDTHH:00:00Z`, strictly before the first issue. Selecting it does not establish adequate spinup or a qualified state. When no origin is selected, the required history interval remains unknown (`null`), and `INITIALIZATION_NOT_SELECTED` remains a blocker even if a caller reports initialization passed.

The bound history interval uses provider forcing labels, with `start_time_utc` equal to the selected origin, `stop_time_utc_exclusive` equal to the last issue plus 18 hours, `provider_label: interval_start` and `timestep_hours: 1`. These source rows cover `[origin, stop)`; the corresponding physical target hours cover `(origin, stop]`, with the final target recorded separately as `final_physical_target_utc`. This follows the existing campaign/forcing semantics and does not add a provider row at the final target. A broad history interval is insufficient on its own: the scope also requires each issue's specific full forecast forcing window. Retaining leads 1–6 or just lead 1 changes export selection and request identity, but always preserves source leads 1–18 and all 18 physical updates per issue.

The shared policy has `max_issues: 100000` and `max_history_hours: 100000`; the request validator also reserves the full 18-hour horizon and representable earlier initialization. The maximum issue window with minimal one-hour initialization headroom is 99,982 issues, and an earlier actual origin can reduce it. Selected history exceeding 100,000 hours is rejected with `PREPARATION_SCOPE_LIMIT_EXCEEDED`; the interface never silently shortens it. These are offline bounds, not source availability or service-capacity promises.

The request and receipt inputs accept only bounded plain JSON: at most 65,536 UTF-8 bytes, depth 16 and 4,096 nodes per validated input. Invalid receipt syntax, unknown checks, duplicate checks or unsupported evidence classes raise `RequestPreparationError` with `code`, `field` and an explanatory message. A well-formed receipt for another scope instead produces a report blocker. Continuous simulation remains proposed: it has no implemented initialization contract or manufactured forecast population, and reports `MODE_NOT_IMPLEMENTED`.

## Outcomes and actionable blockers

| Effective check status | Meaning |
|---|---|
| `unknown` | No usable check outcome was reported; this does not claim an absent or failed prerequisite |
| `missing` | The caller reports a required prerequisite is absent |
| `failed` | The caller reports the check failed; this does not establish that inputs are absent |
| `passed` | A matching receipt reports success; the interface has not verified it |
| `evidence_mismatch` | A well-formed receipt has a different request or scope binding, so its reported outcome is unusable |

`evidence_mismatch` is derived by the interface, never a receipt input status. Each reported check preserves `reported_status`, `reported_binding`, `receipt_sha256` and `evidence`, with `artifact_verified_by_this_interface: false`. Missing check receipts become `unknown`, never an inferred failure or success.

Every blocker has `code`, `requirement`, `message`, `next_option` and detached `evidence` (or `null`). For example, the synthetic source-coverage receipt above produces:

```json
{
  "code": "SOURCE_COVERAGE_FAILED",
  "requirement": "source_coverage",
  "message": "The adapter reports the check failed; this does not establish that inputs are absent.",
  "next_option": "Check initialization/history and every requested issue's full 18-hour forcing window, including source gaps and units.",
  "evidence": {
    "artifact_sha256": "<the synthetic example's SHA-256>",
    "verifier": "documentation-example",
    "evidence_class": "synthetic",
    "detail": "Synthetic failure example; no physical sources inspected."
  }
}
```

Matching passed receipts remove only their respective preparation-check blockers. All seven passed checks plus an explicit origin yield `preparation_checks_status: all_reported_passed`; otherwise it is `incomplete`. Both cases retain `status: blocked`, `execution_ready: false` and `release_qualified: false`, with `CAMPAIGN_PROTOCOL_NOT_ADMITTED` and `EXECUTION_SERVICE_UNAVAILABLE`. The former requires independent scientific/input/runtime/reference admission and fresh bounded run authority; the latter requires a separately implemented and authorized execution/result adapter. Neither the report nor its hashes supersede existing scientific checks or diagnostic execution limits.

The report's `evidence_boundary` explicitly records that artifacts were not read or verified, the verifier was not authenticated, and freshness, scientific qualification and execution admission were not established. `requested_request` and `requested_population` retain the full request, complete hourly issue list, preview and retained-lead selection for an implemented reforecast mode.

## Deterministic result and validation evidence

The report is a detached plain-JSON snapshot: later changes to the caller's request or receipts cannot mutate it. Checks and blockers use fixed order, so reordering the same receipts yields the same report. `identities.report_sha256` hashes the complete report excluding its `identities` field, using sorted object keys, compact UTF-8 JSON and canonical equivalent integer-valued numbers (for example `6.0` and `6`). The canonicalization label is `sorted-json-utf8-v1`. A changed outcome changes the report hash. Hashes identify content; `establishes_admission` is always false.

Validation passed **45 targeted Python tests**: **18 readiness tests**, **19 existing request regressions** and **eight pinned admission regressions**. The [synthetic readiness module](../tests/test_preparation_readiness.py) covers distinct outcomes, scope mismatch, origin and bounds, complete retained-lead scope, schema refusal, detached/deterministic identities and guarded zero acquisition/execution/admission/archive/process calls. The full serial browser/contract suite passed **58 Node tests** (55 existing and three new cross-backend readiness cases) after the review fixes. Independent source and documentation review corrected the provider forcing interval convention and numeric-equivalence issue-count handling, and the identified documentation corrections are incorporated here. [The increment receipt](evidence/preparation-readiness-increment-20261014.json) binds code, logs and preservation checks. This is targeted local validation; no complete Python suite, new CI run, wheel build or physical-model run is claimed.

The twelve-month single-site test preserves all **8,760 hourly 2022 issues**, **157,680 generated rows per location**, **52,560 retained rows for leads 1–6**, and the final physical target **1 January 2023 at 17:00 UTC**. It generates no forecasts or data and measures no workflow elapsed time. It is a scope-preservation test for the intended benchmark, not a participant study or performance result. “50 steps to 10” and “40% faster” remain illustrative targets with no established result.

## Next bounded morning work

1. Implement one preparation adapter that sources an actual check receipt from an already available, separately qualified verifier, retaining its artifact identity, exact study binding and evidence limits. Test mismatched and stale bindings before expanding to further checks.
2. Add a browser display/download path for the report, showing each check's declared status and actionable blocker while preserving request identity and stale-review protection. Keep positive preparation outcomes distinct from execution admission.
3. Prepare any real sources, full issue-specific forcing, initialization, references and scientific admission as separately bounded work with their own protocol and authority. Only after those gates close should execution, verification and downloadable archive adapters be connected for a full researcher study.
