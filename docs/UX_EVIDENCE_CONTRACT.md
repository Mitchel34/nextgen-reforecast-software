# Browser-study evidence contract

Version 1.0, 24 September 2026. **Planning specification; no participants, sessions, results, hosted service or analysis implementation are asserted.** This contract makes the [UX evaluation protocol](UX_EVALUATION_PROTOCOL.md) auditable for manuscript Q5 and Table 5. The [saved planning baseline](planning/2026-09-24_BASELINE.json) retains the preceding plan.

## Scope and evidence identities

Use one versioned study manifest per frozen round, starting from [UX_STUDY_MANIFEST.template.json](../benchmarks/UX_STUDY_MANIFEST.template.json). It is a fillable JSON template, not an executable schema, launcher or evidence of completed work. Empty arrays mean no records entered; `null` means unset or unmeasured, never a measured zero. A future validator and analysis implementation need their own tests and receipts.

Browser evidence uses the namespaced levels **UX_E1** (interface prototype), **UX_E2** (sandbox mechanics), **UX_E3** (qualified physical workflow) and **UX_E4** (independent scientific reproduction). These retain the meanings of the protocol's earlier E1–E4 labels. They are not the numerical benchmark groups E01–E09. A level must accompany every scenario, assignment, attempt and summary stratum.

E09 remains the clean-environment operator reproduction experiment. A browser study can link its UX_E4 task to a qualifying E09 receipt when they concern the same immutable recipe and artifacts, but one does not automatically satisfy the other. Never count an operator attempt again as an additional independent participant or physical invocation. Candidate preparation and final release follow [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md).

## Manifest and freeze requirements

Before a round, record the following. A required unknown leaves the affected task unadmitted; it is not completed by inventing a value.

| Group | Required bindings and decisions |
|---|---|
| Study identity | Unique `study_id`, `round_id`, contract version, manifest version, status, planned purpose, freeze time and amendment history. Allocate actual IDs only when a real study is prepared. |
| Protocol and criteria | Exact UX protocol version/path/hash, evidence-contract version/hash, criteria version/hash, assistance policy, assigned tasks, permitted evidence levels and planned analysis. Freeze these before observing outcomes. |
| Software and service | Repository/commit, dirty-patch identity if any, prototype/build identifier, interface version, service deployment/configuration identifiers and remote-worker runtime/image identities as applicable. UX_E1 may have no deployed service; mark it `not_applicable` with reason rather than fabricating a deployment. |
| Scenario truth | Stable `scenario_id` and revision/hash, journey/objective IDs, evidence level, task wording, intended geography/outlet, mode, study/issue/valid-time bounds, leads, initialization, model/parameter/forcing recipe, expected admitted/blocked outcome and reason, permitted endpoint, prerequisites and evidence references. Mode-specific unused fields have explicit reasons. |
| Candidate and science | Bind any reproduction-candidate ID/manifest hash, exact fixture/lock/reference IDs, physical experiment protocol version and receipts. The licensed, accessible candidate is an input to independent evaluation; final release is its later outcome. |
| Study people | Pseudonymous participant/facilitator IDs, relevant experience categories, independent-operator role where applicable, accessibility setup, permitted use of sanitized evidence and a private consent-record reference. No names, contact details or identity crosswalk belong in the public study package. |
| Admission and resources | Admitted journey/scenario IDs; each prerequisite and its evidence; existing environment, resource and physical-run authorization references where needed. This contract grants no execution, recruitment, spending or publication authority and adds no numerical benchmark invocation allowance. |

Freeze the manifest and its referenced scenario/criteria bytes before the round. Keep the manifest's checksum in a separate artifact index to avoid hashing a file containing its own hash. Corrections create a new version with reason, prior-version hash and affected attempts. A product fix creates a new software binding and retest record; retain the original failure. Do not silently promote UX_E1/UX_E2 records to physical evidence after the product changes.

## Assignment, attempt and evidence records

Record **every assigned task**, including tasks never started. This keeps exclusions and unavailable prerequisites visible before summarizing successes.

| Record | Required fields |
|---|---|
| Participant | `participant_id`, experience/accessibility categories when provided, eligibility, participation state, private consent/access reference and permitted public-use categories. Recruitment aggregates are separate; do not publish identifying screening notes. |
| Assignment | `assignment_id`, participant ID, scenario ID/revision, journey/objective IDs, evidence level, software/round binding, eligibility and reason, expected outcome (`supported_completion` or `expected_block`), assigned/started state, nonattempt or withdrawal reason, first-attempt ID if any and primary outcome. An unstarted assignment has outcome `NA` and no invented attempt/timing. |
| Attempt | `attempt_id`, assignment ID, sequence, original/retest relationship, software/scenario bindings, start/end when measured, observed endpoint, primary outcome, first directional-assistance event, assistance events, errors/self-recovery, critical findings, comprehension responses, withdrawal/interruption reason, timings with missing-value reasons, event/evidence references and artifact hashes. |
| Continuation | Link the assisted continuation or later retry to the original attempt and retain its first outcome, first failure and first hint. Record its resulting endpoint separately. Do not replace first-attempt failure with eventual success. |
| Finding and retest | Stable finding ID, affected journey/evidence level, severity, evidence reference, owner, resolution/version, retest assignment/attempt and unresolved state. A closed ticket without relevant retest evidence is not demonstrated resolution. |

The protocol's outcome codes remain `SU`, `SB`, `SA`, `FE`, `PB` and `NA`. Neutral probes and normal built-in help follow the declared assistance policy. A directional hint excludes the attempt from unassisted success even if it ultimately completes. Expected blocks count only toward block comprehension; unexpected product blocks remain attempted outcomes. Preserve all repeated attempts, but summarize first attempts separately from retests or familiarized participants.

UX_E3/UX_E4 success requires links to real preparation, job, runtime/lock, output-verification and export receipts relevant to the claimed endpoint, including their hashes and scientific identities. UX_E4 also requires independent-reproduction evidence and the declared comparison rule. A browser event, screenshot, animation or zero-exit job alone does not establish these conditions. A failed or blocked real task retains available failure receipts and an explicit explanation of missing receipts; missing evidence must never be labeled passed. UX_E1/UX_E2 refer only to their bound prototype/synthetic artifacts.

## Planned result package

Use the following logical artifact names within each study's versioned deposit. These names specify future deliverables; none is claimed to exist from this planning update.

| Artifact | Role and access |
|---|---|
| `ux_study_manifest.json` | Frozen study/round bindings and decisions; publish only a reviewed version with private identity/consent locations removed. |
| `ux_scenarios.json` | Versioned task wording and scenario truth with their admission/evidence bindings. |
| `ux_assignments.csv` | All assigned tasks, eligibility, attempt state, nonattempt reasons and first outcomes. Controlled source by default; a sanitized derivative may be released only after review. |
| `ux_attempts.jsonl` | Append-only attempt, continuation, assistance, error and receipt records; controlled source by default, with reviewed sanitized derivatives where permissible. |
| `ux_findings.csv` | Defects, critical findings, software revisions, fixes and retest linkage; sanitize any participant-derived text. |
| `ux_task_summary.csv` | Reproducible aggregate counts by study/round, journey, scenario variant, evidence level and software revision, with denominator definitions and missing-data reasons. |
| `ux_study_report.md` | Descriptive findings, timing scope, assistance/failures, limits and claim-to-artifact links for Q5/Table 5. Operator E09 findings have their own section/reference. |
| `ux_analysis_manifest.json` | Analysis script/source commit and hash, invocation/configuration, environment, every input/output hash, aggregation rules and result status. |
| `ux_artifact_index.json` | Artifact ID, logical path or accessible locator, media type, version, checksum, access class, source/derived relationship and permitted-use disposition. Never include credentials or signed access URLs. |

Retain recordings, identity crosswalks, consent forms and unsanitized quotations in approved private storage outside the public repository. A private reference is an opaque record ID, not a published filesystem path. Check consent and redistribution rights before releasing quotations, screenshots, event extracts or aggregates; small groups and detailed experience categories can still identify people. The public manuscript can use reviewed aggregates while documenting which underlying evidence is access-controlled and how an authorized reviewer can reproduce the analysis. Do not imply public access to private source records.

## Reproducible counts and claims

For each frozen stratum, emit assigned, eligible, attempted and not-attempted counts; separate `SU/SB/SA/FE/PB/NA` counts; expected-supported and expected-block populations; withdrawals, unresolved critical findings, missing-evidence counts and unique participants. Record recruitment counts separately from task-assignment counts. Do not treat missing entries as zero. The first-outcome totals must reconcile with all assignments, and attempted first outcomes exclude `NA`.

If rates are reported, state the numerator and denominator explicitly. Use `SU / attempted supported assignments` for first-attempt unassisted supported completion and `SB / attempted expected-block assignments` for block comprehension. Unexpected blocks and withdrawals after a task starts remain in the relevant attempted denominator. Report eligible-but-unattempted assignments and reasons beside those rates. Zero denominators yield `null` with a reason. Retests and additional attempts have separate counts; do not inflate the participant denominator or pool UX_E1–UX_E4, different software revisions or task variants into an unexplained success percentage.

Timing summaries distinguish active interaction, system wait and interruptions, with the number of measured and missing observations. Never infer an unmeasured time from a missing event. The analysis must regenerate Table 5's counts from retained records and declared transformations, with a complete hash trail to the exact version of every source record or sanitized analysis input.

The first manuscript's usability evidence is **descriptive task completion and comprehension within the tested scope**. It does not establish superiority over NGIAB, notebooks or another interface. Resource claims remain relative to the declared numerical benchmark baseline. A comparative ease, speed or effort claim requires a separately amended matched design before observations; this contract neither adds that experiment nor claims its results.

## Handoff acceptance

The UX evidence owner supplies the frozen manifest/scenarios, complete assignment/attempt record, sanitized aggregate package and analysis provenance. The manuscript lead checks that Q5 and Table 5 separate operator E09 reproduction from namespaced browser evidence. The release coordinator checks the admitted journeys against the reproduction candidate, unresolved critical findings, fixes and relevant retests before final release. A planning template, empty file or polished screenshot does not satisfy these checks.
