# Roadmap reconciliation — 22 September 2026

The owner supplied [*NextGen Reforecast Generation: Technical Foundation and Software Roadmap*](source_material/TECHNICAL_FOUNDATION_2026-09-22.md), dated 22 September 2026, with 24 numbered sections; its exact bytes are recorded in the [source manifest](source_material/MANIFEST.json). This document maps that direction onto the existing public implementation and preserves the controlling milestone IDs in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md). Work packages and acceptance criteria are in [DEVELOPMENT_BACKLOG.md](DEVELOPMENT_BACKLOG.md). This reconciliation changes the development plan; it does not qualify a native runtime or announce a completed software release.

The source-code baseline reviewed for this reconciliation is commit `252160f`. The [implementation status](IMPLEMENTATION_STATUS.md) and [validation receipt](VALIDATION.json) retain the earlier local tests and installation evidence. A subsequent [CI run](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/35765301098) at commit `1ee0288` passed 54 tests on each of Python 3.11–3.14 on Linux. The planner/runtime source is unchanged from the reviewed baseline; these checks qualify offline contracts only. The original design and feasibility dossier remain historical evidence. Original research folders remain read-only and were not needed for this reconciliation.

## Evidence states

**Implemented** means the public checkout contains the capability; the linked validation receipt determines the tested platform and scope. **Historical** means inspected predecessor source or a historical receipt describes the capability; it is not qualification of the public package. **Planned** means an interface, implementation or experiment remains to be delivered. **Unverified** means the necessary measurement, source identity, external fact or reproduction evidence is absent. These states can coexist within one roadmap section.

## Mapping all 24 sections

| Supplied section | State at this baseline | Development decision and work package |
|---|---|---|
| 1. NWM, NextGen and reforecasts | Terminology adopted; official ecosystem sources reviewed separately | Describe a research NextGen reforecast using identified components. NOAA's cited hourly/18-hour HRRR/RAP description is CONUS-specific. Do not equate research results with archived operational NWM output. See the [source review](ECOSYSTEM_AND_DISSEMINATION.md); RF-016 maintains citations. |
| 2. Reforecast definition | Implemented issue/lead/valid-time expectation ledger; planned archive identity | Current keys contain domain, location, reach, issue, lead and valid time; realization/run identity is not yet an archive schema. Bind those identities in RF-003/RF-012. |
| 3. HYDRA architecture | Historical two-domain architecture; public physical execution unverified | Preserve the 393-catchment New River domain with nested outputs and separate 31-catchment Watauga domain. Historical qualifications have their own configuration scope. Public release qualification requires RF-010/RF-011/RF-015. |
| 4. State reconstruction | Implemented declared origin/history checks; historical reconstruction; planned public executor | Keep the 2018 production origin separate from the 2021 fixture. Report adopted antecedent duration without declaring universal convergence. RF-003/RF-010. |
| 5. Historical versus forecast weather | Implemented role/hash checks; historical forcing interpretations; planned content qualification | Role names and matching hashes cannot prove AORC/NWM contents or prevent semantic substitution. RF-004 must validate sources, transformations, units, issue identity and complete coverage. |
| 6. Temporal semantics | Implemented expectation clocks; historical provider interpretation; planned physical checks | Forecast target is I+k hours; provider interval starts I+(k−1) hours. RF-004 and RF-012 test actual forcing/output rows, routing clocks and source labels. |
| 7. State-aware branch mechanism | Historical native mechanism; planned public adapter | A fresh Linux ARM64 build and reference comparison must precede public branching claims. FD isolation, one-thread admission, router restore and parent/sibling invariance remain RF-011/RF-013 requirements. |
| 8. Checkpoint limitation | Historical routing snapshot/replay design; public resume unavailable | A channel snapshot is not a complete land checkpoint. RF-014 must replay the unchanged history origin and skip only verified completed issues. Portable complete checkpoints remain outside v1. |
| 9. Campaign customization | Implemented explicit irregular issue lists, resource bounds and nested locations; planned lead retention/YAML/source adapters | Schema 1.0 fixes execution and ledger leads to 18. RF-002 adds selected retained leads within 1–18, without claiming shorter native branches. RF-006 adds optional YAML and schedule shorthand. |
| 10. Researcher workflow | Implemented offline init/plan/ledger/report/doctor; run/resume deliberately unavailable; other commands planned | Preserve existing command semantics and errors. Future prepare/run/status/resume/verify/export/run-report are assigned to RF-007/RF-010–RF-014. |
| 11. NextGen ecosystem | Integration boundary adopted; official source roles reviewed; integration implementations planned | Consume versioned hydrofabric/forcing/runtime/evaluation products through adapters. ForcingProcessor and NextGen Forcings Engine are separate projects. The [source review](ECOSYSTEM_AND_DISSEMINATION.md) does not qualify this project's adapters. RF-004/RF-007/RF-012/RF-016. |
| 12. Architecture | Implemented planner and offline runtime inspection; other layers planned | The backlog allocates the domain/forcing adapter, lock, controller, transaction, verification, export and report interfaces. Those names are proposed, not existing APIs. |
| 13. Provenance | Implemented declared asset hashes/plan IDs and historical runtime profile; scientific execution lineage incomplete | RF-003 introduces source/transform/build/run/issue/event identities and explicit unknown values. RF-004/RF-005 resolve content and parameter semantics; no provenance inferred from calendar dates. |
| 14. Forcing gaps | Historical research imputation and excluded forecast issue; public policy engine planned | Implement explicit fail/exclude_issue/approved_imputation decisions in RF-004. Preserve history continuity and inherited-state lineage; historical treatment is not a generic or operationally causal default. |
| 15. Reference versus optimized | Historical comparison receipts; new public executors and equivalence unverified | RF-010 implements a transparent per-issue replay reference; RF-011 adds shared history. Compare identical physical configurations and origin, not different initialization procedures. |
| 16. Software-paper measurements | Existing planned protocol; new physical measurements and independent reproduction unverified | RF-013/RF-014/RF-015 measure correctness, equal-resource cost, reliability and usability. Historical receipts remain a separate evidence class; no theoretical speedup substitutes for measurements. |
| 17. Initial scope | Narrow target adopted; public native support unqualified | Start with Linux ARM64 SLOTH/NoahOWP/CFE/channel-only t-route and exact 18-hour branches. Planner Linux/macOS support does not imply native portability. RF-008–RF-011. |
| 18. HYDRA and ML | Product boundary adopted; downstream export planned | HYDRA is an optional consumer, with no ML runtime dependency in v1. RF-012 demonstrates an interchange/evaluation path; manuscript success does not depend on corrected forecast skill. |
| 19. EM&S contribution | Manuscript argument drafted; publication-ready evidence unverified | Focus on state reconstruction, issue-specific weather, equivalence, recovery and provenance. RF-016 checks literature and limits claims to executed evidence. |
| 20. Manuscript structure | Development manuscript, claim register and protocol already present; results pending | Continue RF-016 concurrently. Write supported design/methods now; fill results, abstract performance claims and conclusions after RF-010–RF-015. |
| 21. Development milestones | Supplied M0–M6 labels differ from controlling M0–M7 | Use the explicit crosswalk below. Never rename completed milestones or infer native-build completion from the existing M1 planner. |
| 22. Immediate priorities | Campaign foundation implemented; fixture/build/executors/evidence still open | Begin independent offline contracts now while RF-008/RF-009 close physical dependencies. A 20-hour/two-issue fixture is a new proposed experiment, not the preserved 786-hour fixture. |
| 23. AGU26 opportunity | Official dates/rules reviewed; project-specific eligibility not established | The [dated source review](ECOSYSTEM_AND_DISSEMINATION.md) confirms that September 29 concerns listed earthquake/wildfire events, with other events due October 13; these are not general software deadlines. RF-017 requires an eligible route and author decisions. A conference date cannot waive scientific or submission requirements. |
| 24. Long-term vision | Product objective adopted; complete end-to-end capability planned | Deliver a narrow, auditable first release through RF-001–RF-018. Additional formulations, cloud execution and portable checkpoints require separate capability qualification. |

## Milestone numbering crosswalk

The left column is the supplied September roadmap. The right column remains the controlling repository milestone identity. Matching labels are not matching completion states.

| Supplied roadmap | Controlling milestones | Reconciliation |
|---|---|---|
| M0 Evidence and scope | M0 Feasibility, plus open M2/M7 qualification and rights gates | The completed dossier records scope and gaps; it did not resolve every build or distribution dependency. |
| M1 Public core / clean reproducible build | M1 Planning foundation + M2 Runtime/example closure | Public planning software exists. A fresh complete native build remains a separate M2 exit. |
| M2 Reference fixture / another machine runs it | M2 asset/build closure + M3 physical execution + M5 external transfer | Fixture bytes, same-host execution and another researcher's reproduction are separate evidence stages. |
| M3 Verification/benchmark | M4 Reliability/resource study, dependent on M3 execution | Written protocols and mechanics tests precede executed physical experiments. |
| M4 Researcher transfer | M5 Transfer/usability | Require a researcher who did not build the system; another local agent does not meet this condition. |
| M5 Research release | M7 Release/submission readiness | Tag, image, fixture, benchmark archive, notices/license, documentation and archival identifiers must correspond to qualified artifacts. |
| M6 Manuscript | M6 Manuscript/reproducibility package + M7 final submission readiness | Draft throughout development; submission requires final evidence and author/declaration decisions. No manuscript submission is implied by this plan. |

## Current and proposed campaign behavior

Current [campaign.py](../src/ngen_reforecast/campaign.py) accepts explicit, strictly increasing, unique UTC issue hours. It does **not** require consecutive hours or a fixed issue cadence, so selected events, every-third-hour and irregular lists are already representable. Issues must follow the original origin, and declared historical coverage must reach the final issue plus 18 hours. Schedule shorthand is convenience work; it does not require changing the historical integration timestep or skipping history between issues.

Current [schema 1.0](../schemas/campaign.schema.json) accepts JSON, exact fields, `profile: hourly18h` and `horizon_hours: 18`. The expectation ledger emits all leads 1–18. Passing YAML, adding `min_lead_hours` to the current object, or setting horizon to 6 is unsupported today. The roadmap's YAML examples are prospective interfaces.

RF-002 should introduce a versioned **retained lead interval**, with `1 <= min_lead_hours <= max_lead_hours <= 18`, while retaining an explicit execution horizon of 18 hours for the historical native profile. Proposed schema fields and migration must be reviewed before implementation. Plans must distinguish generated and retained row counts. Selecting 1–6 retained hours must still require all 18 physical forcing intervals and all runtime completion checks; it cannot be presented as a six-step qualified runtime or proportional CPU saving. A separately qualified short native profile would be another future feature.

Optional YAML in RF-006 must normalize to the same strict canonical representation and lock identity as equivalent JSON. Reject duplicate keys, unknown fields, nonfinite numbers, unsafe tags, implicit timestamp/coercion surprises and unbounded aliases; do not weaken resident-file bounds. Existing schema 1.0 campaigns remain readable through an explicit compatibility policy, without silent reinterpretation of their hashes or numerical meaning.

## Three distinct fixture/campaign identities

| Identity | Bounds and state | Rule |
|---|---|---|
| Preserved historical Watauga V3 day fixture | Origin `2021-12-01T00:00:00Z`; history stop `2022-01-02T18:00:00Z` exclusive; 786 history hours; issues `2022-01-01T23:00:00Z` and `2022-01-02T00:00:00Z`; 18 leads each | Preserve exact expected identities and references. Last recorded inventory has 181 members, 132 dataless and 131 unresolved member hashes; those are September 18 inventory facts, not a fresh protected-folder scan. |
| Proposed compact 20-hour/two-issue fixture | A new experiment request with origin, issue offsets, history stop, source bytes, complete 18-step branches and expected outputs still to be frozen | Specify what “20-hour” measures. With 20 total history hours and coverage through the last target, the last issue must be at most origin+2h. A 20-hour antecedent window is a different duration. Neither choice inherits the 786-hour reference or proves converged spinup. |
| Historical production campaign | Origin `2018-07-18T00:00:00Z`; first retained issue `2018-09-17T00:00:00Z`; adopted 61-day initialization | Preserve separate source/treatment/parameter identities. Production history cannot replace the 2021-origin fixture, and 61 days is not universal convergence evidence. |

RF-009 records whether exact historical restoration or a separately identified compact fixture is pursued. It does not rewrite the historical manifest to make missing files disappear. A new release parameterization also needs a separate identity and freshly evolved history; the [CFE parameter finding](CFE_PARAMETER_FINDING.md) remains an M2 release gate.

## Command-state reconciliation

| Phase | Public package now | Intended next behavior |
|---|---|---|
| `init` | Writes a JSON planning template without scientific assets | Discoverable supported profiles and explanatory input checklist |
| `plan` | Validates declarations and bounded resident hashes; always reports physical runtime blocked | Canonical schedule/retained products, content-validation status and explicit execution admissions |
| `prepare` | Absent | Resolve/stage already authorized versioned inputs, validate semantic coverage and seal a lock; acquisition must be explicit and bounded |
| `run` | Recognized but returns unavailable | Execute a locked, qualified profile under declared resources; initially reference, then shared-history |
| `status` | Absent | Read durable events and verified commits without inventing a percentage from partial files |
| `resume` | Recognized but returns unavailable | Verify existing commits, replay from the unchanged origin, suppress only completed issues and retain recovery evidence |
| `verify` | Absent | Verify input/output keys, clocks, lineage, numerical checks and completion receipts at the declared evidence level |
| `export` | Absent | Export verified products with run/realization/domain/location/issue/lead/valid-time identities and lineage |
| `report` | Generates an offline **plan report** from campaign JSON | Add a distinct executed-run report backed by verified artifacts; keep plan and run reports labelled |
| `ledger`, `doctor` | Expected-key CSV and offline historical runtime inspection | Continue as diagnostics; neither output is a physical forecast or a native build receipt |

## Scientific gates carried into implementation

Source-content validation must distinguish accumulated historical precipitation from forecast precipitation rates; preserve original labels and provider intervals; require finite values, complete catchment/issue/lead coverage and bound source object identities; and retain unresolved shortwave timing as uncertainty. RF-004 must reject a weather file whose bytes match a supplied hash but whose physical meaning contradicts its declared role. It must not infer an authoritative NWM model release solely from date or grid fingerprint.

Gap policy must default to `fail`. `exclude_issue` may suppress an unavailable forecast branch with a recorded reason, but may not skip missing historical intervals needed by later states. `approved_imputation` requires a separately identified, preapproved transformation with donor/source records and explicit retrospective availability. Inherited-state influence remains conservatively flagged until an evidence-backed rule establishes otherwise. Missing, unavailable, imputed, substituted and rejected are separate statuses.

Parameter qualification includes source column, units, transformation, generator revision, generated values and actual loaded library identity. A successful checksum or serial-versus-branched comparison cannot establish parameter correctness. In particular, CFE drainage, Noah terrain slope and routing reach slope are separate quantities. Any adopted CFE mapping correction requires a separate configuration, new antecedent trajectory and new physical reference.

No date, desired feature, historical receipt, offline test or generated document upgrades the package to a qualified reforecast generator. The next deliverables are the bounded work packages below, followed by measured physical and independent-reproduction evidence.
