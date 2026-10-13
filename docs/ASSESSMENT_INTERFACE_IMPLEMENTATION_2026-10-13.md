# Shared request and assessment interface — 13 October 2026

The owner correction asks to eliminate the mismatch rather than only explain it. This implementation removes the browser's artificial 24-issue minimum and gives the browser and offline backend one versioned UTC request policy. It preserves complete whole-day studies and the unchanged physical diagnostic admission. At the earlier implementation/local-validation checkpoint, no scientific/model/campaign run, service start, hosting/deployment, spending, publication, deletion or permission change had occurred. Work remains separate from HYDRA/NWM AGU poster work and NextGen internal/residual correction.

## Why the two limits differed

| Limit | Source and meaning | Implemented resolution |
|---|---|---|
| At least 24 browser issues | Version 0.1 interpreted each selected date as an entire UTC issue day. This was a software/UI convention, not a NextGen scientific requirement | Version 0.2 adds optional first/last UTC issue hours. Dates still default to 00–23, preserving full studies; an explicit one- or two-hour window is valid |
| Exactly two diagnostic issues | [`_supported_campaign`](../src/ngen_reforecast/execution_lock.py) enforces the two cases in the [sealed profile](../src/ngen_reforecast/_profiles/watauga-v2.json), together with exact origin/history/domain and resources | Kept as an execution-admission boundary. Matching hours now have a coherent frontend/backend path; larger schedules remain complete planning specifications |
| Six planned / nine maximum diagnostic processes | The sealed protocol has history plus two independent forecasts, each native + routing; its three repair reservations are not a general campaign allowance | No ledger reset or inherited authority. A larger execution needs its own frozen workload and resource/run allowance; current authority permits zero new processes |

The two-issue admission combines software enforcement with an identified scientific/input/reference envelope and bounded resource authorization. The general [campaign normalizer](../src/ngen_reforecast/campaign.py) already supports broader bounded issue lists; its arithmetic was never limited to two. Widening the old admission check alone would discard the evidence binding, so it is deliberately not bypassed.

## One supported request contract

The authoritative [policy](../web/request-policy.json) defines request version 0.2, hourly cadence, an 18-hour physical horizon, retained leads 1–18 and existing offline size bounds. The [packaged Python copy](../src/ngen_reforecast/preparation/request-policy.json) is byte-identical, with drift checked in tests and a package-data declaration. [The contract](BROWSER_REQUEST_CONTRACT.md) defines the serialized fields.

`buildRequest(input)` accepts practical location, dates and lead preference. Optional `start_hour_utc` / `end_hour_utc` give endpoint precision; ordinary whole-day users need no extra inputs. The canonical artifact records the corresponding UTC hours and timestamps. Every hour from the first issue through the last is included, with an exclusive stop one hour later.

| Request, retained leads 1–6 | Issues | Generated rows | Retained rows | Final physical target |
|---|---:|---:|---:|---|
| January 1–2 with default whole-day hours | 48 | 864 | 288 | January 3 at 17:00 UTC |
| Explicit January 1 at 23:00 through January 2 at 00:00 | 2 | 36 | 12 | January 2 at 18:00 UTC |
| A single selected issue hour | 1 | 18 | 6 | Selected issue + 18 hours |

The maximum representable request is 99,982 issues with minimal one-hour initialization headroom; the history cap or actual scientific origin can require less. Oversized, reversed, non-hourly or unrepresentable windows are rejected rather than clipped. These limits do not advertise service capacity or verified source availability. Version 0.1 files remain intact and produce `REQUEST_SCHEMA_MIGRATION_REQUIRED`; no implicit migration changes their scope.

## Implemented code paths

[request.mjs](../web/request.mjs) and the new Python [preparation backend](../src/ngen_reforecast/preparation/__init__.py) independently validate the same policy and artifact. `normalize_request(input)` produces equivalent canonical JSON; `validate_request(artifact)` rejects changed derived fields, readiness claims or unresolved metadata pretending to be evidence. `translate_request(artifact, preparation, campaign_id=...)` uses separate service-owned origin/domain/resource and location-binding metadata, validates the campaign with the existing normalizer, and returns every requested issue. It is planning only: no inputs/runtime are checked and no location is resolved by trusting the descriptor label.

The pure [assessment interface](../web/assessment.mjs) exports synchronous `evaluateRequest` and asynchronous `assessRequest`. It preserves an immutable snapshot of the original artifact and a complete requested issue list, reports declared diagnostic compatibility and explicit remaining blockers, and adds SHA-256 request/report/policy identities. Hashes detect changes, not sender authenticity or execution authority. Exact diagnostic clock matches avoid a false schedule-mismatch blocker while `execution_ready` remains false for unresolved preparation and service/admission gates.

The [UI](../web/app.mjs) offers optional issue-hour precision and a separately labeled diagnostic example, bounded summary text, unchanged request download and complete assessment download. It has no run or submission action. Every edit, mode change, example selection or newer submission invalidates pending hashes and reviews; stale success/error callbacks and old download closures cannot combine different requests. Continuous mode remains explicitly unimplemented and does not manufacture a forecast list.

Unit and integration tests cover exact/default windows, leap/DST/calendar and size edges, policy-copy equality, complete backend translation, tampered/unknown/legacy artifacts, Unicode and numeric parity, immutable identities, zero execution/admission/asset-read calls, and synthetic DOM review/download races. The offline checks passed **55 Node tests** (including seven browser/Python integration cases and eight synthetic DOM tests) and **19 Python tests**; the original diagnostic executor/profile source bindings remained unchanged. These results establish local request/preparation behavior only. That validation checkpoint included no live-browser evaluation, new wheel, new CI run or new physical campaign qualification. The earlier CI validates the preceding revision and does not validate this implementation.

## Exact remaining gate for a full 48-issue run

With the existing independent-serial recipe, history plus 48 forecast replays would require **98 native/routing process launches** before any repair allowance, rather than six. Retaining leads 1–6 does not reduce that workload. From the unchanged December 1 cold origin, the full history/final coverage reaches January 3 at 17:00 UTC, 809 hours; the current fixture ends January 2 at 18:00 UTC and supplies only two issue-specific forecast cases.

Before executing that scope, prepare and content-validate a separately identified fixture covering the complete initialization/history and all 48 issue-specific 18-hour forcing populations; retain its scientific and source limitations. Freeze a new protocol with the exact input/runtime/scientific identities, native-output/warning/time checks, resource limits and process/repair allowances. Generate and seal independent physical references under fresh run authority, then admit the broader executor envelope against them. The existing two-issue fixture/reference set and ledgers must remain unchanged. Current continuation authorizes none of those runs, so no expanded execution lock or positive readiness is produced here.

Scientific defaults/source units, clean-build provenance, rights/license, automatic acquisition, hosted access/job isolation, verified prior-result inspection, recovery and outside-user evaluation remain separate unfinished gates. Existing source-bound diagnostic warning treatment and C50–C52 physical evidence are not upgraded by these offline tests. This completes the coherent request/assessment code milestone while broader physical execution remains unqualified.
