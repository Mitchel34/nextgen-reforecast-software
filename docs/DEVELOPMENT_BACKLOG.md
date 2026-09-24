# Development backlog — updated 24 September 2026

This backlog operationalizes the owner's 24-section roadmap while retaining [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) milestones M0–M7. [ROADMAP_RECONCILIATION.md](ROADMAP_RECONCILIATION.md) records all section mappings, interface differences and fixture boundaries. Stable work-package IDs below should be used in issues, PRs, tests, evidence manifests and manuscript claims.

**23 September product amendment:** the [objectives and journeys](PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) make a hosted browser experience, minimal researcher inputs and automatic preparation part of the first usable product. RF-001–RF-018 remain engine/research packages. Proposed WEB-01–WEB-07 cover identifier/coverage discovery, acquisition, forms, service jobs, results, recipes and UX evidence. This backlog's ten-day cycle is an internal engineering increment, not a complete web-app delivery schedule. Use the [UX evaluation protocol](UX_EVALUATION_PROTOCOL.md) when assigning researcher-facing deliverables.

The starting product is the public `0.1.0a1` offline planning foundation. “Ready” below means work can begin with bounded local inputs; it does not mean implemented. “Blocked” identifies an external or physical-evidence dependency, while independent contract/documentation work may proceed. All proposed module names and function signatures are design targets, not existing callable APIs. Original Reforecast/HYDRA/thesis folders remain read-only; outputs, tests and staging go in this repository or ignored local directories. Do not hydrate placeholders or launch native models to satisfy a planning task.

**24 September handoff amendment:** the [working-plan reassessment](WORKING_PLAN.md) and [saved baseline](planning/2026-09-24_BASELINE.json) preserve the prior plan while resolving three concerns. The [first-experiment contract](FIRST_PHYSICAL_EXPERIMENT.md) fixes diagnostic admission and fixture precedence; the [release sequence](RELEASE_SEQUENCE.md) supplies an immutable reproduction candidate to E09 before final release; the [UX evidence contract](UX_EVIDENCE_CONTRACT.md) supplies separate browser results to Q5. These are documentation decisions, with no new implementation or execution evidence.

## Priority queue and ownership

| ID | Priority / present status | Controlling milestone | Suggested owner and proposed interface | Dependencies |
|---|---|---|---|---|
| RF-001 | P0 / foundation verified; CI passed | M1 | Coordinator; existing package/CLI, workflow and installation receipts | Local installation receipt plus four-version CI retained in docs/VALIDATION.json |
| RF-002 | P0 / ready; lead retention not implemented | M1/M3 | Planner; versioned campaign schema, `normalize_campaign()`, `iter_expected_rows(kind="generated" or "retained")` | Existing campaign API; decide compatibility contract first |
| RF-003 | P0 / ready; execution provenance/lock absent | M1/M2/M3 | Provenance agent; `provenance.py`, `schemas/campaign-lock.schema.json`, `seal_lock()` / `verify_lock()` | Existing safe readers; coordinate RF-002 schema boundary |
| RF-004 | P0 / ready for bounded fixtures; real-source qualification blocked on complete assets | M2 | Forcing agent; `forcing.py`, `validate_history()`, `validate_forecast_issue()`, `evaluate_gap_policy()` | RF-003 identity contract; RF-009 for real forcing |
| RF-005 | P0 / finding documented; conformance validator and coupled qualification absent | M2 | Scientific configuration agent; `configuration.py`, `validate_parameter_mapping()` | RF-005A: RF-003 and source/library provenance; RF-005B coupled comparison: RF-008/RF-009A/RF-010 |
| RF-006 | P1 / explicit irregular schedules implemented; shorthand and YAML planned | M1 | Planner; bounded `load_campaign_document()` and `expand_schedule()` | RF-002 stable schema; dependency/security choice for optional YAML |
| RF-007 | P1 / prepare absent; ready after contract agreement | M2/M3 | Input/CLI integration agent; `prepare.py`, `prepare_campaign()` → preparation report + immutable lock | RF-003/RF-004/RF-005A; real preparation depends on RF-008/RF-009A |
| RF-008 | P0 / historical inventory/recipe present; clean native build blocked | M2 | Runtime/build agent; runtime-profile attestation + reproducible build recipe | Full source/dependency/component identities, permitted staging and working Linux ARM64 environment |
| RF-009 | P0 / historical fixture incomplete; compact fixture only proposed | M2 | Data/fixture agent; fixture decision record, restoration manifest, source/expected-output bundle | RF-009A: input availability, RF-005A parameter decision and source/rights checks; RF-009B expected-output closure: RF-010 |
| RF-010 | P0 / reference executor absent; adapter design ready, physical run blocked | M3 | Runtime reference agent; `executors/reference.py`, `run_reference(lock, budgets)` | RF-007/RF-008/RF-009A with complete admitted inputs; not RF-005B or RF-009B |
| RF-011 | P0 / historical branching exists outside released implementation; public executor absent | M3 | Native/runtime agent; `executors/shared_history.py`, qualified issue-boundary adapter | RF-010 reference; RF-008 source/preimage and build closure |
| RF-012 | P0 / archive/commit/verify/status/export absent; offline transaction mechanics ready | M3 | Archive/controller agent; `archive.py`, `verify_issue_commit()`, `commit_issue()`, `status()`, `export_verified()` | RF-003 identity; initial synthetic fixtures independent of native build; physical use requires RF-010/RF-011 |
| RF-013 | P1 / protocol/matrix written; new physical equivalence/resources unmeasured | M4 | Verification/benchmark agent; runners consuming fixed workload/tolerance/resource manifests | RF-010/RF-011/RF-012 |
| RF-014 | P1 / recovery policy historical; public recovery absent; synthetic tests ready after commits | M3/M4 | Recovery agent; `recovery.py`, `plan_replay()` / `resume_campaign()` | RF-003/RF-012; physical recovery requires RF-010/RF-011 |
| RF-015 | P1 / New River transfer and independent reproduction not started | M5 | Domain agent + external researcher; tutorial and operator evidence records | Qualified Watauga, RF-013/RF-014; complete New River assets; E09 uses immutable reproduction candidate, not completed RF-018 |
| RF-016 | P0 / development manuscript/register/protocol present; results pending | M6 | Manuscript agent; `paper/`, `benchmarks/`, claim-to-evidence checks | Ready now for design/protocol; final claims depend on RF-010–RF-015 |
| RF-017 | P1 / official AGU rules reviewed; project eligibility and journal readiness unresolved | M6/M7 | Coordinator + author; dated official event/journal requirement record | A qualifying dissemination route and author decisions; separate from runtime critical path |
| RF-018 | P1 / release not ready; license/rights and archival decisions open | M7 | Coordinator + author; candidate and final manifests, notices, source/image/data and archive record | Candidate preparation follows its internal evidence/rights gates before E09; final release requires RF-015 plus admitted WEB-07 evidence and applicable RF-001/008–016 results |

## Work-package deliverables and acceptance

### RF-001 — Preserve the tested foundation and activate reproducible CI

Keep current strict JSON/UTC/resource/path/placeholder guards and installed CLI behavior. Re-run the repository suite and wheel installation against the exact candidate commit; record command, platform, Python version and outcome. The September 18 receipt reports 54 local tests and nine installed CLI checks, which are historical validation counts until refreshed. On September 22, [run 35765301098](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/35765301098) installed the package and passed all 54 tests on each of Linux/Python 3.11–3.14 at commit `1ee028871daf00b3bb76f2416c5a2b5626ab7aee`. The [validation receipt](VALIDATION.json) binds those results. The foundation/CI activation task is complete; refresh relevant checks when implementation changes.

**Done:** clean-environment installation and the claimed matrix have retained passing receipts; failures are resolved or explicitly narrow the supported platform statement. No planner success is represented as native-model success. Failed hash reads and files growing/truncating during inspection remain bounded by the originally admitted byte count.

### RF-002 — Separate retained forecast products from physical execution length

Draft the next schema version and compatibility policy before changing parser behavior. Preserve schema 1.0 `hourly18h` and its 18-step meaning. Add a retained lead interval using the roadmap's `min_lead_hours`/`max_lead_hours` concepts with `1 <= min <= max <= 18`; keep execution length explicitly 18 for this runtime profile. Plans should report both generated and retained row counts, expected issue/domain totals, unchanged original origin and adopted initialization duration. Decide whether projection occurs at committed-product publication or export, and bind that decision in the lock; never discard runtime-completion evidence needed to verify an 18-step child.

**Acceptance:** 1–18 retains all rows; 1–6 retains six rows per issue/location; 6–6 retains exactly lead six; 0, 19, reversed limits and booleans are rejected. All choices still require complete source leads 1–18 and eighteen runtime steps. An irregular issue list changes branch count while preserving continuous history integration. Equivalent defaults preserve old numerical meaning, and any changed lock/schema identity is explicit. No claimed CPU saving follows from selecting fewer retained rows.

### RF-003 — Introduce a scientific provenance contract and immutable campaign lock

Specify experiment/run/configuration/domain/location identities; origin/history interval; exact issue list; execution and retained leads; hydrofabric and catchment axes; realization/parameters; native/component/routing source and loaded-artifact identities; source-object keys/version/generation where supplied; decoded payload hashes; transform names/versions/units; source timestamps and physical intervals; gap decisions; runtime capabilities; budgets; output schema; and evidence class. Unknown fields must remain explicit unknowns that block the relevant readiness claim. Include per-event provenance for preparation, execution, retries/replay and publication. Keep source metadata distinct from weather payload evidence.

**Acceptance:** changing origin, parameters, weather, transformations, issue schedule, runtime artifacts or policy changes the corresponding identity; identical canonical values normalize deterministically. Altering an asset after locking invalidates admission. Unknown source version cannot become a guessed NWM release. Wrong-domain/realization outputs cannot pass merely because issue/lead keys match. Locks and reports remain bounded and safe to read; test clocks and nested-domain identities with small synthetic metadata fixtures.

### RF-004 — Validate forcing contents, exact clocks and gap-policy decisions

Start with bounded local CSV/metadata fixtures using independently authored validators. Read actual required variables, finite values, catchment axes, units, source and provider timestamps, duplicate/missing intervals, issue/lead coverage and hashes. Test the declared historical APCP end-label/accumulation-to-rate treatment separately from already-rate forecast precipitation; prevent double conversion. Preserve unresolved shortwave interpretation and exact forecast grid/decoder fingerprints without inferring a complete model-release history. Integrate existing forcing tools through a versioned adapter later; no new general-purpose regridding engine is needed.

Implement a default `fail` policy. `exclude_issue` records the excluded forecast issue and adjusted retained population; it must not skip a required historical interval or silently replace its weather. `approved_imputation` requires an explicit treatment identifier, approval record, donor/source times, transformation and lineage propagation; a future donor can make a research treatment retrospective rather than available at issue time. Missing, unavailable, substituted, imputed and rejected must remain distinct. Do not assume inherited-state influence expires after a convenient number of hours.

**Acceptance:** detect a one-hour shift despite plausible filenames; wrong accumulation/rate semantics; missing catchment/lead; repeated issue+lead; NaN/Inf; retrospective weather passed as issue-specific forecast weather; and a valid hash over scientifically wrong contents. Approved treatment changes lock identity and appears on every potentially affected descendant output; absent approval fails. Synthetic content checks are labelled separately from restored real-weather qualification.

### RF-005 — Qualify configuration and parameter meaning

Implement source-column/units/transformation checks from [CFE_PARAMETER_FINDING.md](CFE_PARAMETER_FINDING.md). Bind generator revision, hydrofabric metadata, per-catchment source values, generated values and actual loaded CFE library. Audit CFE bottom drainage separately from Noah terrain slope and routing reach slope. Preserve the archived baseline. Freeze a separately identified candidate and a one-factor coupled comparison before that paired physical comparison; evolve both antecedent histories from the same original origin. A known-concern diagnostic baseline admitted under RF-005A can supply the earlier reference executor without waiting on the candidate comparison.

**RF-005A — Pre-execution admission:** bind the known source mapping, configuration identity, declared uncertainties and purpose of the experiment. Wrong source column, undocumented conversion, missing required metadata or a mismatched loaded library prevents release-profile admission even when hashes match. An explicitly identified historical baseline can be admitted for diagnostic reproduction with its known mapping concern retained; that is not release qualification. Tests prove candidate changes invalidate state/output reuse. RF-007, RF-009A and RF-010 require this admission record, not the result of a future coupled comparison.

**RF-005B — Post-reference coupled qualification:** after RF-010 supplies the reference executor, run the separately bounded paired comparison. Retain water/storage/runoff/routed-flow terms under fixed non-CFE settings and correctly label inherited versus candidate configurations. Neither isolated-CFE sensitivity nor reference/shared-history agreement is accepted as coupled parameter correctness. This phase closes the candidate release decision and cannot be a prerequisite for building the first reference executor.

### RF-006 — Add convenient schedules and optional YAML without weakening contracts

Existing explicit `issue_times_utc` lists already support regular and irregular event schedules. Add shorthand for UTC interval cadence or selected UTC hours only as a deterministic expansion to that list. Define inclusive/exclusive issue endpoints explicitly. Optional YAML must normalize to canonical JSON with bounded input, duplicate-key rejection, safe tags, controlled alias expansion and no implicit date/number coercion that changes meaning.

**Acceptance:** hourly, three-hour, daily and irregular schedules produce exact expected lists and row counts; conflicting list/shorthand declarations fail. All schedules retain the hourly integration timestep. JSON/YAML equivalents produce the same normalized scientific identity. Unsafe tags, duplicate mappings, alias bombs, timezone offsets, nonfinite values and unknown fields fail. If YAML is deferred, documentation continues to show JSON as the working format.

### RF-007 — Prepare inputs and seal readiness honestly

`prepare_campaign()` should combine asset inventory, semantic checks and explicit runtime capabilities into a preparation report. Resident/versioned inputs are an internal adapter-development stage. The final researcher workflow requires WEB-01/WEB-02 to resolve an identifier and acquire/prepare supported inputs automatically under declared source, byte/time/request and compute bounds. Researchers must not assemble model files or repair private paths. Preserve original input sources and stage within the software workspace or separately admitted service storage. A complete preparation report may produce a lock, while missing dependencies produce actionable browser explanations.

**Acceptance:** missing or unknown files never produce execution-ready locks; prepared bytes and interpretation match RF-003, RF-004 and RF-005A; changed sources require a new lock. The existing offline commands never download or hydrate implicitly. Future service submission may trigger the disclosed, bounded acquisition within established service permissions; protected-folder hydration, silent parameter repair, origin shortening and weather substitution remain prohibited. A preparation-only result cannot be reported as a run. Unknown coverage must not be presented as verified availability.

### RF-008 — Close the native runtime build and component identities

Use the existing historical profile and staging inventory to close each unresolved source preimage/overlay, dependency/toolchain, component library, routing environment and image/build identity. Refresh the host capability check when build work starts; the previous no-daemon observation is a dated local result. Select a working Linux ARM64 build environment and a bounded recipe only after those inputs are concrete. Retain upstream notices and ownership/redistribution scope; do not copy private implementation or binaries as a shortcut.

**Done:** a clean Linux ARM64 build from the public recipe produces a complete attestation, loads the pinned BMI/routing libraries and passes explicit startup/time/profile guards. Source-repository identity is tied to actual artifacts. A source manifest, existing binary hash or Docker CLI alone is insufficient. Wider native architectures remain unsupported until separately demonstrated.

### RF-009 — Close the real fixture with an explicit identity decision

Maintain separate tracks: exact restoration of the historical 786-hour/two-issue Watauga fixture, and design of a new compact 20-hour/two-issue experiment. The recorded historical inventory has 132 dataless files and 131 unresolved hashes; consult that manifest without hydrating protected sources. Decide what the new “20-hour” span means, because a 20-hour total history interval permits the last 18-hour branch issue only by hour two under the current coverage rule. A 20-hour antecedent period requires a later history stop. Freeze all times before preparing weather.

For the current protocol 0.3, the original Watauga recipe remains the first physical experiment. Compact-fixture design is preparatory only; it does not supersede that decision. If the original inputs cannot be obtained, return a source-bound blocker and propose an explicit new experiment/protocol amendment under [FIRST_PHYSICAL_EXPERIMENT.md](FIRST_PHYSICAL_EXPERIMENT.md). Preserve the original IDs, references and missing-asset record.

**RF-009A — Input and recipe admission:** every required geometry/configuration/parameter/forcing/runtime input has exact resident bytes and source/transform/rights information. Freeze the reference recipe and expected key/clock contract; retain any existing historical expected-output identities. This input stage can feed RF-010 before new reference outputs exist.

**RF-009B — Reference-output closure:** use RF-010 to derive and seal new expected outputs, then verify the complete fixture in a clean staging directory. Historical references remain attached to their original origin/configuration. A newly generated fixture receives a new identity and new reference; the 2018 production history and synthetic weather cannot stand in for missing 2021 physical inputs. No convergence claim is inferred from a short fixture. This post-execution stage is not a prerequisite for implementing RF-010.

### RF-010 — Implement the transparent reference executor

For each issue, create an independent process/configuration from the bound original origin, replay identical historical forcing to I, use that issue's forecast weather for exactly 18 hours, and retain routed outputs and diagnostics under fixed budgets. Expose the executor through a small `run_reference(lock, budgets)` adapter with structured receipts. Controller/process plumbing may be tested using clearly labelled synthetic workers before native admission.

**Done:** fresh real Watauga reference execution binds runtime/input identities and exact provider/target clocks, has complete finite output keys and zero-exit reaping, and produces reviewable expected outputs. An unqualified restored routing snapshot, cold initialization at I or different parameter origin cannot supply the reference. The operator tutorial executes from the released recipe without modifying native source.

### RF-011 — Implement and qualify shared-history execution

Use a minimal pinned native integration: continuous parent; precise issue boundary; single-thread guard; independent read descriptions and output ownership; child forecast-provider switch; separately started/restored channel routing; explicit isolation acknowledgment; bounded child pool; parent continuation; zero-exit child reaping. Keep retry policy explicit: a failed issue after parent advancement requires a valid replay path, not an unrecorded cold fallback.

**Done:** the same real fixture agrees with RF-010 under the predeclared [benchmark protocol](../benchmarks/PROTOCOL.md), complete clocks/keys and unchanged source identities. Demonstrate parent and sibling invariance, router epoch continuity and per-issue completion. A historical receipt or newly passing synthetic worker cannot satisfy the physical criterion.

### RF-012 — Add transactional archive, verify/status, export and executed-run report

Implement issue transactions that require complete expected output keys, finite/nonnegative routed values for the supported profile, exact clocks, bound identities and exactly one successful reaped-child receipt before atomic publication. Existing commits must be verified before reuse; incomplete files are not completed forecasts. Implement read-only status from events/commits, verification with explicit evidence levels, and one documented export format before adding others. Retain realization/run/domain/location/issue/lead/valid time and gap/source lineage through export; do not collapse overlapping valid times.

**Acceptance:** interruption before/after data write, checksum write and atomic publication cannot expose a partial committed issue or silently overwrite an incompatible commit. Wrong counts/keys/identities, corruption, nonfinite outputs and nonzero exits fail. Export round-trip preserves keys, units, masks and selected leads. Executed-run reports distinguish attempted, failed, excluded, committed and verified outputs and use measured resources; existing plan reports remain labelled as plans.

### RF-013 — Execute correctness and equal-resource performance experiments

Freeze reference/optimized workloads, complete sources, hardware, CPU reservations, tolerances and repeat policy before timing. Include initialization, forcing preparation/read, routing, children, output publication, total wall time, CPU-core hours, peak aggregate memory and storage. Report measured disagreement and all failures; do not compare a larger optimized allocation against a smaller reference and call the ratio an algorithmic speedup.

**Done:** retained raw measurements support every correctness/resource result and regenerate summary tables/figures. Serial/concurrent and parent/sibling tests pass the predeclared comparison rule. Performance conclusions remain limited to measured domains, sizes, platforms and configurations; no production-scale extrapolation is labelled a result.

### RF-014 — Recover through verified original-history replay

Implement a side-effect-free recovery plan that verifies lock/commits, preserves original configuration and history origin, checks remaining resource authority and lists unfinished issues. The executor replays all needed history while suppressing only verified completed branches. Record replay cost and interrupted attempts; do not claim a portable land checkpoint.

**Acceptance:** synthetic child/parent/write/job interruption tests establish transaction mechanics first. Physical failure injection then shows original-reference-equivalent outputs, one canonical commit per issue and intact lineage under the same numerical rule. Corrupt commits, changed parameters/forcing/runtime, missing history or exhausted budgets stop recovery. Report measured replay overhead separately from forecast work.

### RF-015 — Transfer to New River and an independent researcher

Qualify the second domain with its two nested output locations sharing one compatible physical history. Release a complete tutorial, exact fixture, supported-platform matrix and a configuration-only variation. Recruit a researcher who did not implement the system after the runnable example exists.

**Done:** New River outputs pass the physical equivalence and recovery criteria. An independent operator installs, reproduces and changes one supported setting without editing core/native source; retain environment, commands, outputs, questions and failures. Separately, external hydrologists complete the supported browser journeys without CLI, Python or manual input preparation, using [UX_EVALUATION_PROTOCOL.md](UX_EVALUATION_PROTOCOL.md). Record assistance and unsuccessful tasks as well as successes. A second agent or second local virtual environment is installation testing, not independent scientific reproduction or external-user usability evidence.

Use the immutable `REPRODUCTION_CANDIDATE` defined in [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md) as E09 input; completing the final RF-018 release is not an entry condition. A supported variation receives its own scientific identity and baseline relationship. Browser-study outcomes use the separate [UX evidence package](UX_EVIDENCE_CONTRACT.md), linked to the relevant physical receipts. Neither evidence stream substitutes for the other.

### RF-016 — Develop the manuscript alongside the code

Use the existing `paper/` draft and claim register. Map each scientific/software claim to the relevant RF work package, released artifact and evidence class. Write formal state/time/provenance contracts, reference method, evaluation protocol and limitations now. Verify ecosystem overlap and citations against primary sources and current journal requirements. Keep historical evidence, new offline tests, synthetic mechanics, fresh native qualification and independent reproduction distinct.

**Done by stage:** development draft has substantive methods and explicit unmeasured results; measured draft regenerates tables/figures from RF-013/RF-014; submission-ready package has only supported abstract/results/conclusion claims plus authorship, declarations, data/code availability and journal-specific materials. HYDRA is an optional downstream use case, with no required forecast-skill claim for this software article.

### RF-017 — Verify dissemination requirements without creating a deadline promise

The [September 22 official-source review](ECOSYSTEM_AND_DISSEMINATION.md) establishes that AGU's late-breaking deadlines apply to specified events, with membership and relevance requirements; unrelated abstracts are rejected. September 29 is not a general software-abstract reopening, and no eligible project connection is established. Determine whether a permitted existing-presentation route or a qualifying event-specific contribution actually exists, and recheck live rules before action. Check current EM&S instructions separately. Draft a preview only from evidence available at the time.

**Done:** dated authoritative requirements and a concrete eligible route or an explicit no-route finding. No automatic abstract/manuscript submission, author endorsement or public presentation claim follows from planning. This package cannot pull unqualified runtime work past its scientific gates.

### RF-018 — Assemble a versioned research release

Resolve core-code licensing and third-party/data distribution terms at their actual scopes. Inventory notices, selected source/image/fixture versions, benchmarks and installation instructions. Tag only coherent verified artifacts and produce archival metadata/identifiers after the package is complete. Keep public repository availability separate from a qualified, licensed research release.

Prepare a source-bound, licensed and accessible reproduction candidate once its relevant internal qualification and rights/access checks are complete. Its manifest can precede E09 and the final archive DOI. After E09 and admitted browser evidence, retain findings, version any fixes, perform the affected retests and bind the final release to the evaluated artifacts. [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md) defines this handoff and prevents a candidate/final-release dependency cycle.

**Done:** the release checklist closes all claimed capability/evidence/rights gaps; released files reproduce the retained results; independent-transfer evidence is linked; archival identifiers resolve; manuscript availability statements match actual public artifacts. Publication and submission steps require the author's concrete final decisions when those artifacts are ready.

For a hosted-product release, also close the admitted WEB packages and claimed UX pathways: account/access boundaries, job/resource limits, storage/retention and sharing policy, source-availability errors, verified downloads and independent browser-user evidence. An engine-only tag may be an engineering release but does not satisfy the first usable hosted-product objective. Planning these checks does not provision infrastructure or authorize spending.

## First ten working days

These are relative working-day slots from the next implementation kickoff, not calendar deadlines or a promise of a finished native product in two weeks. Estimates assume coordinator, planner/provenance, runtime/data and manuscript work can proceed in parallel. Unexpected asset, toolchain, rights or parameter findings change the schedule. Keep the offline lane moving when physical closure is blocked.

| Working days | Ready bounded software lane | Runtime/data closure lane | Manuscript/evidence lane | Reviewable exit |
|---|---|---|---|---|
| 1–2 | RF-001 preserve verified baseline/CI; RF-002 schema/retention compatibility proposal; RF-003 lock and event contracts | RF-008 dependency/build gap inventory; RF-009 historical-versus-new fixture decision; RF-005 source-field contract | RF-016 reconcile claims/architecture/protocol with roadmap; RF-017 assess any eligible route using the official review | Reviewed interfaces, named blocker owners, immutable historical evidence and agreed first PR scopes |
| 3–4 | Implement RF-002 retained-key planning and RF-003 bounded identity fixtures; begin RF-004 clock/source-role failures | Resolve obtainable build/source metadata and fixture manifests; specify new compact fixture timing if chosen; no implicit acquisition/model launch | Add formal contracts and methods diagrams; define figure inputs and required experiment metadata | Passing focused offline tests; clear changed-schema migration; physical blockers retain exact unresolved fields |
| 5–6 | RF-004 local semantic/gap-policy validators; RF-005 conformance tests; RF-012 synthetic atomic commit skeleton | Qualify staging content where complete; build only if RF-008 recipe/environment/source gates are closed | Update methods and claims with merged tests, labelled as offline/synthetic evidence | Adversarial clock/gap/parameter tests and interruption-safe synthetic commit receipts; separate build result or blocker report |
| 7–8 | RF-007 local preparation/lock integration; RF-012 verify/status for synthetic archives; RF-014 replay planner | If complete, begin RF-010 bounded real reference; otherwise finish closure inventory and reference-adapter code against synthetic workers | Draft reference/recovery methods and resource measurement forms; keep results unmeasured if native work blocked | Installed CLI integration and failure/recovery mechanics; a real reference receipt only if physical prerequisites are met |
| 9–10 | Independent review, wheel/CLI regression, RF-012 first export/run-report contract; RF-006 only if core contracts are stable | Review reference outputs; RF-011 physical shared-history work starts only after admissible reference/build; otherwise record the exact external next action | Refresh claim register/status and next-sprint experiment plan; assess release/submission gaps | Integrated progress commit and honest milestone status; no inferred runtime qualification from sprint completion |

The bounded offline increment is estimated at roughly 8–10 working days with these parallel roles after interface agreement. A real build, fixture restoration, coupled parameter decision and independent reproduction are conditional work with no reliable completion date until their missing inputs are resolved. Additional time for physical equivalence, failure experiments, New River transfer and manuscript review must follow actual evidence rather than a conference target.

## Handoffs and stage-specific completion

Each work package should hand over a concise record: implemented files/interfaces; exact test commands and environment; source/fixture/commit identities; generated evidence; unresolved blockers; and claims newly permitted. Coordinator owns integration, public status, CI and Git publication; lane owners review each other's contract boundaries without overwriting active work. Scientific configuration and manuscript reviewers must examine any change that alters origin, weather treatment, parameters, routing or output interpretation.

An offline unit-test pass closes only its software contract. A synthetic worker closes only its controller/transaction contract. A fresh native run closes only its bound profile/fixture experiment. A reference comparison closes only its predeclared numerical scope. External reproduction closes only the recorded independent operator/environment experiment. M7 and submission readiness require all relevant stages, not a count of files or a green synthetic demonstration.
