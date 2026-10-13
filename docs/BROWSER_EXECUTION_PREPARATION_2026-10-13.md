# Browser-to-execution preparation checkpoint — 13 October 2026

**Subsequent implementation amendment:** This document preserves the original explanation-only proposal. The owner subsequently requested eliminating the mismatch. [The implemented version 0.2 request/assessment contract](ASSESSMENT_INTERFACE_IMPLEMENTATION_2026-10-13.md) supports optional exact UTC issue hours and full offline backend translation, including one or two issues and unchanged 48-issue defaults. Sections describing every request as whole-day and the assessor as nonexistent apply to the earlier 0.1/proposal stage. New physical execution and hosting remain unauthorized. Prior document bytes are retained in ignored local evidence with their original receipt; this amendment does not turn those earlier checks into tests of the new implementation.

This is a local preparation contract and review plan. No service/API implementation, new model execution, hosting or publication is introduced. It follows the [working plan](WORKING_PLAN.md), [browser request contract](BROWSER_REQUEST_CONTRACT.md) and [pinned operator contract](PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md). Current scope is recorded in [AGENTS.md](../AGENTS.md).

## Project and evidence boundaries

The deliverable is an open-source reforecast generator and accompanying software manuscript. HYDRA/NWM AGU poster preparation and NextGen internal/residual correction are separate projects, with separate scientific artifacts and authority. This generator may supply downstream datasets; it does not depend on a neural correction model, borrow its skill results or turn a correction experiment into software qualification.

The published package is `0.1.0a5` at `d7ff94cc32dbf5f3db8d3f9eeb47e82cc1f03e39`. Existing Watauga v2 operator diagnostics and C50–C52 remain supported by their unchanged [acceptance](evidence/public-campaign-execution-increment-20261011.json) and [publication](evidence/public-campaign-execution-publication-20261011.json) receipts. The six successful model processes are historical results of that admitted increment. No remaining repair reservations are repurposed into permission for a new campaign.

## Observed mismatch

The browser's [request builder](../web/request.mjs) proposes inclusive UTC issue dates with hourly cadence. One whole day produces 24 issues; January 1–2, 2022 produces 48. All current date-only reforecast requests therefore differ from the executor's two exact issue hours: January 1 at 23:00 UTC and January 2 at 00:00 UTC. The admission check in [execution_lock.py](../src/ngen_reforecast/execution_lock.py) enforces that exact population, fixed cold origin, history endpoint, domain and 18-hour horizon.

For the two-day example with retained leads 1–6, the browser proposes 864 generated rows and 288 retained rows per location. The operator diagnostic generates 36 and retains 12. Both use a full 18-hour physical integration horizon; selecting fewer leads does not reduce integration or forcing requirements. The browser's final physical target is January 3 at 17:00 UTC, beyond the diagnostic input period ending January 2 at 18:00 UTC.

The prototype correctly reports unresolved location, unknown coverage, unqualified scientific defaults, unavailable execution service and `execution_ready: false`. Its Watauga demonstration label is not a verified gauge/reach crosswalk. The artifact is a proposal fragment, not a campaign with an admitted origin/history, runtime, resources and complete input/reference bundle. No functional defect justifies making the prototype appear runnable.

## Next reviewable deliverable

Prepare a pure assessment interface before adding submission or hosting. The candidate report name `browser-preparation-assessment/0.1-draft` is proposed only; no new schema or callable service exists yet. An assessment must bind the validated researcher request to its own identity and independently recompute its issue/lead population. Browser preview counts and a client-supplied readiness flag cannot authorize execution.

| Report part | Required information | Readiness rule |
|---|---|---|
| Requested study | Submitted identifier and type; mode; dates; declared date interpretation; cadence; complete requested issue list/count; generated horizon and retained leads | Preserve the request unchanged. Unsupported issue populations are blockers, never silently projected into a smaller campaign |
| Location resolution | Verified gauge/reach mapping, upstream domain identity and source/version, or explicit unresolved/ambiguous status | A demonstration label or matching number cannot replace resolution evidence |
| Coverage and preparation | Required initialization/history/final target intervals; source coverage and failures; scientific profile and input/runtime/reference bindings | Missing, unknown and failed lookup remain distinct. No unknown coverage is promoted to ready |
| Compatibility | Requested versus admitted profile clocks, location, horizon, populations and parameter/runtime identity | Exact diagnostic match does not establish release suitability or general watershed support |
| Blockers and options | Stable blocker code, affected requirement, evidence and understandable next option | Every current whole-day request is blocked for execution. A fixed diagnostic recipe may be offered separately with explicit differences and consent; preserve the original request |
| Prior result inspection | Verified result/lock/scientific/runtime identities; generated/retained counts; issue/lead/valid-time keys; units and diagnostic quality | A prior result is labeled as prior evidence. Completion requires fresh `verify_result(expected_lock=...)`, not successful process exit or a captured-output record |

The service will own model files, worker sockets, resources and internal paths. Hydrologists still provide only a practical location, dates and forecast preference. Automatic acquisition remains required by UO-03; an operator bundle is not the final researcher experience.

An initial read-only diagnostic result view can use explicitly synthetic fixtures or the existing result after fresh read-only verification. It must distinguish absent, incomplete, failed verification and verified completed archives. Queued/running/cancelled states require separate durable job evidence; they cannot be inferred from archive absence. Recovery remains unsupported. Submission, acquisition, worker management and download access control are future interfaces, not capabilities supplied by this plan.

## Acceptance cases for the subsequent local bridge

These are proposed tests, not results of an implemented assessor.

| Case | Required outcome | Work/journey mapping |
|---|---|---|
| Two-day Watauga request: 48 issues versus admitted 2 | Explicit schedule and final-target blockers; original request retained; zero launches | RF-002/003/007; WEB-03; UO-01/03; UX-02/05 |
| One-day request: 24 issues | Still blocked; no date choice can manufacture the two issue hours | RF-002/007; WEB-03; UX-02/05 |
| Unknown gauge, unresolved NWM reach or ambiguous watershed | Evidence-backed location blocker without substituting the Watauga demonstration | WEB-01/02; RF-003/007; UX-05 |
| No-lead continuous simulation | Explicit proposed/unimplemented mode; no zero-hour reforecast | WEB-03; UO-06; UX-01/05 |
| Client changes preview counts or sets readiness true | Server revalidation rejects the mismatch; no ready lock from client assertions | RF-003/007; WEB-03/04; UX-05 |
| Retain leads 1–6 versus 1–18 | Complete 18-step workload preserved; generated/retained populations displayed separately | RF-002/012; WEB-05; UX-07 |
| Missing, corrupt or different-lock prior archive | No completed result or download permission; explicit verification failure | RF-003/012; WEB-04/05; UX-06/07 |
| Verified existing diagnostic result | Exact result/scientific/runtime/lock provenance and quality shown; no claim of a new run or general scientific validity | RF-012/016; WEB-05/07; UO-05/09; UX-07 |

All assessment/view tests must inject inert fakes for executor, socket, acquisition and publication boundaries and assert zero calls. The current continuation permits preparation and existing offline checks, not implementing an end-to-end hosted service or running these future scientific workloads.

## Decisions and next gates

The current whole-day date semantics remain a proposal. Resolve issue versus valid dates, cadence and how a curated diagnostic recipe is presented before freezing the service request contract. Preserve open scientific defaults, source-unit/terrain semantics, initialization convergence, clean-build provenance and redistribution/license gates. Hosting accounts, service resources, retention/sharing, continuous mode and external UX thresholds also remain open in the [working plan](WORKING_PLAN.md).

After the pure assessment/result contract is reviewed, a separately scoped implementation can add local synthetic service-adapter tests and the browser review/status/result view. A real browser-to-dataset milestone still needs supported-domain resolution, bounded automatic preparation, job isolation/access rules and qualified physical execution. Shared-history and recovery require their own admitted protocols and fresh authority. A source check, planning fixture or prototype test does not close those gates.

The [continuation receipt](evidence/continuation-preparation-20261013.json) distinguishes fresh checks from retained physical evidence. Original research folders remain read-only; the new metadata baseline does not erase the earlier 347-entry drift or assert original content-byte equality. The manuscript's scientific claims remain unchanged. All changes from this continuation are local and unpublished.
