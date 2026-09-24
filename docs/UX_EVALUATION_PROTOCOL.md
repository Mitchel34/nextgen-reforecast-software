# UX evaluation protocol

23 September 2026. Status: proposed evaluation protocol for a planned graphical product. No user sessions, usability results, hosted service, remote model runs or independent scientific reproductions are reported here.

The [product objectives and user journeys](PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) define what researchers should be able to accomplish. This protocol makes those objectives observable during development. The existing [implementation status](IMPLEMENTATION_STATUS.md), [engine milestones M0–M7](../IMPLEMENTATION_PLAN.md), [development backlog](DEVELOPMENT_BACKLOG.md) and [scientific benchmark protocol](../benchmarks/PROTOCOL.md) remain the sources for actual software and scientific qualification. A successful interface test cannot replace those gates.

## Purpose and scope

Related methodological context is recorded in the [EM&S guide](../paper/RELATED_WORK_AND_WRITING_GUIDE.md): Houtkamp et al. (2025) motivates iterative evaluation with users; Choi et al. (2023) distinguishes developer and user burdens but uses expert coauthor ratings. Neither source establishes this protocol's sample size or success thresholds. The scenarios and thresholds below remain proposed project choices to refine through formative work.

Evaluate whether a hydrologist can select a scientifically appropriate workflow, understand its scope and limitations, obtain the intended results when supported, and make an informed next choice when work is blocked. The participant should need a normal web browser and domain knowledge appropriate to the task. **CLI use, Python coding, configuration-file editing, local Docker installation and access to a developer are not prerequisites for successful use of the planned graphical product.** Advanced details may remain inspectable without becoming mandatory setup steps.

UO-01–UO-04 and UO-09 capture owner direction. UO-05–UO-08 are research-informed design proposals awaiting explicit refinement. All are product objectives, not statements that the current package implements a hosted interface or runnable physical workflow. Confirm proposed mode, recipe and comparison terminology with the owner before treating those design details as fixed acceptance requirements.

## Objective-to-journey evaluation map

| Objective | Requirement to investigate | Principal journeys | Observable evidence |
|---|---|---|---|
| UO-01 Minimal inputs | Researcher supplies only decisions that cannot responsibly be inferred; defaults remain visible | UX-01, UX-02, UX-05 | Input inventory; redundant entry and correction count; participant explains selected location, period and method before starting |
| UO-02 Hosted graphical interface | Researcher reaches the supported end state entirely in the browser | All journeys | Navigation record and any dependency on code, terminals, local model setup or developer intervention |
| UO-03 Automatic acquisition/preparation | The system resolves supported inputs and explains remaining gaps | UX-01, UX-02, UX-03, UX-05 | Preparation states, source/coverage summary, blocker comprehension; actual acquisition receipts only in qualified stages |
| UO-04 Remote supported Linux execution | The interface submits and tracks an admitted job on a supported remote environment | UX-01, UX-02, UX-06 | Intended-versus-actual job identity, environment and resource bounds; browser interaction is insufficient proof of remote execution |
| UO-05 Understandable trustworthy outputs — proposal | Researcher interprets products, evidence and uncertainty correctly | UX-02, UX-06, UX-07 | Teach-back responses, verification status, issue/lead interpretation, labelled preview versus real results |
| UO-06 Distinct simulation/reforecast modes — proposal | Researcher chooses a continuous historical simulation or issue-specific reforecasts for the stated question | UX-01, UX-02, UX-04 | Mode selected and explanation of meteorological inputs, time dimensions and permitted comparisons |
| UO-07 Exact study recipes — proposal | Reproduction preserves a study's original scientific specification and dependencies | UX-03, UX-05, UX-07 | Recipe/version identification, unchanged origin/settings, explicit missing-asset outcome, reproduction verification |
| UO-08 Controlled comparisons — proposal | A deliberate change produces a distinct, interpretable experiment while retaining the baseline | UX-04, UX-07 | Baseline/variant identities, visible change summary, compatible comparison and retained provenance |
| UO-09 Independently usable/reproducible product | A researcher who did not build the system can complete supported work and reproduce its evidence | All journeys; independent test centered on UX-03/UX-04 | Assistance log and independent operator record linked to qualified software, exact recipe, outputs and verification |

## Evidence levels and prerequisites

Record the evidence level for every task and artifact. Never combine these levels into one undifferentiated success rate.

| Level | What may be evaluated | Evidence required before use | What a successful task establishes |
|---|---|---|---|
| E1 — Interface prototype | Labels, mode choice, forms, maps, navigation, status explanations and comprehension of prepared scenarios | Versioned prototype; documented scenario truth; conspicuous prototype/sample-result labels | A participant can navigate and understand the proposed design. It establishes no data acquisition, execution, numerical result or scientific reproduction. |
| E2 — Sandbox mechanics | Real UI/controller wiring, preparation/status transitions, synthetic interruption recovery and download packaging | Isolated bounded sandbox; versioned synthetic fixture; labelled simulated job/results; retained event/transaction evidence | The tested mechanics work for the synthetic fixture. Synthetic discharge is not hydrologic evidence, and a scripted completion is not a physical run. |
| E3 — Qualified physical workflow | End-to-end preparation, supported remote execution, verification and export of a complete real fixture | Relevant M2/M3 gates closed; exact real inputs/build; bounded authorized run recipe; controller/output checks; remote execution environment qualified | The researcher completed the declared physical workflow under the recorded conditions. General model validity, arbitrary-domain support and independent reproduction do not automatically follow. |
| E4 — Independent scientific reproduction | A person who did not implement the system reproduces an identified study/fixture and makes a supported change | E3 evidence; complete accessible recipe and fixture; M4 checks applicable to claims; independent operator; predeclared comparison rule | Reproduction/usability evidence within the tested study, platform, operator and configuration scope, supporting M5/UO-09. It is not population-wide usability evidence. |

The existing offline planning package and its passing CI do not satisfy E2–E4 for a future hosted product. A developer walking a prototype establishes E1 review evidence; an external hydrologist walking that prototype is still E1. A second agent, test account or local virtual environment is not an independent scientist. Continuous historical simulation and graphical remote execution each require their own implementation and qualification; they are not inferred from the reforecast planner.

## Participants and facilitation

Propose recruiting **3–5 external hydrologists or environmental modelers** for an initial formative round. This is a recruitment suggestion: no participants are booked or contacted through this protocol. Seek a useful spread of workflow familiarity, including a researcher comfortable with hydrologic questions but unfamiliar with NextGen installation, an experienced NextGen user, and a forecast-verification or reproducibility user where feasible. Record relevant experience without treating this small purposive group as statistically representative.

Use participant IDs rather than publishing names or contact details. Obtain consent for any screen recording or quotations and use non-sensitive demonstration locations/data unless a separate research-data arrangement exists. Offer keyboard-only interaction and record any assistive technology or access needs relevant to the interface. Do not exclude people from the intended audience merely because they cannot use the CLI.

Before each round, freeze the prototype/software revision, scenario manifests, task wording, permitted assistance, expected outcomes and evidence level. Give every participant the same neutral explanation of the task environment. For E1/E2, explain clearly that any model execution/results are simulated. Do not teach the correct click sequence or rehearse the scientific answers being assessed.

Use built-in help normally: locating and understanding product help can be part of unassisted use. When a participant is stuck, first ask a neutral question such as “What would you expect to happen next?” Log it as a probe. A hint naming the next control, changing the intended interpretation, supplying missing setup knowledge or operating the interface becomes assistance. Record the first hint and the assisted continuation separately; do not erase earlier failed or blocked attempts.

Do not invent a completion-time target before observing a baseline. Record actual active interaction time, system wait time and interruptions separately when timing is feasible. Explain that feedback concerns the product, not the participant. Participants may stop a task; preserve their reason and the visible state rather than coercing completion.

## Task cards

Each task card provides neutral wording, facilitator setup and an observable end state. Substitute exact locations, dates, studies and settings only from a versioned scenario manifest. The facilitator must know whether the selected area/data/profile are supported at the tested revision. A plausible place name or calendar range is not proof of support. Tasks marked for qualified execution must stop at the review/blocked state when E3 prerequisites are absent.

### UX-01 — Create a continuous historical simulation

**Maps to:** UO-01, UO-02, UO-03, UO-04, UO-06, UO-09.

**Participant prompt:** “You want a continuous streamflow simulation for this watershed and historical period using historical weather. Use the product to set it up, inspect what it will do, and proceed as far as this environment supports. Show how you would obtain the resulting time series.”

**Facilitator setup:** Supply a supported, unambiguous scenario with a named watershed/gauge or map target, period and a scientifically admissible default configuration. The manifest states the geographic truth, intended simulation mode, weather source, initialization policy and allowed endpoint for the evidence level. Do not require the participant to discover a hydrofabric identifier, configure native libraries or supply technical paths.

**Unassisted success:** The participant selects continuous historical simulation, verifies the intended watershed/period and visible method/defaults, understands the initialization and coverage summary, and reaches the declared review or qualified-run end state. At E3, automatically prepared inputs and remote execution must have receipts; the final product is a continuous time series from that run. At E1/E2, the participant recognizes the sample result and no physical completion is recorded.

**Critical errors:** Starting a forecast-issue campaign unintentionally; selecting another watershed; interpreting an incomplete or sample series as verified output; believing a short initialization guarantees hydrologic convergence. Record whether the interface exposed the error and whether the participant corrected it before submission.

**Capture:** Required inputs, defaults changed, mode/location/period chosen, preparation questions, run-summary comprehension and result identity. Unexpected unsupported conditions become a blocked observation, not a fabricated success.

### UX-02 — Generate historical reforecasts

**Maps to:** UO-01, UO-02, UO-03, UO-04, UO-05, UO-06, UO-09.

**Participant prompt:** “You want forecasts that would have been issued over this historical period for this watershed. Use the stated issue schedule and retain the requested lead hours. Check the experiment before starting and show how you would inspect forecasts for one issue.”

**Facilitator setup:** Provide a frozen supported issue schedule, retained lead interval within 1–18 and exact scenario coverage. Include two issues with an overlapping valid hour so interpretation can be observed. Keep the physical execution horizon explicit: the current target runtime always requires 18 steps even when fewer output leads are retained. Current schema 1.0 does not yet implement retained-lead selection; an E1 concept is not a shipped control.

**Unassisted success:** The participant chooses reforecasts, identifies the intended watershed and issue schedule, distinguishes historical initialization weather from issue-specific forecast weather, and confirms generated versus retained products. When inspecting an output, the participant can identify issue, lead and valid time and explain why two values may share a valid hour. Only E3 counts a verified physical forecast archive as delivered.

**Critical errors:** Substituting retrospective weather for forecast weather without disclosure; collapsing overlapping forecasts into one time series; treating retained six-hour products as evidence of a six-step or proportionally cheaper native run; silently changing the requested issue population to fit missing data.

**Capture:** Input burden, schedule/lead choices, time-zone interpretation, row-count summary, availability explanation, resource estimate comprehension and issue-selection actions. Ask for a plain-language explanation; the participant need not calculate epochs or edit a schema.

### UX-03 — Reproduce a published study

**Maps to:** UO-02, UO-03, UO-04, UO-05, UO-07, UO-09.

**Participant prompt:** “Use the supplied study recipe to reproduce its stated experiment. Check what is fixed, what must be available, and how the product will decide whether the reproduction agrees. Proceed without changing the study's scientific settings.”

**Facilitator setup:** Use a versioned study recipe with exact authorship/source identification, initialization origin, physical inputs, parameterization, runtime profile and comparison rule. At E1/E2 this may be a clearly marked demonstration recipe; do not describe it as a published scientific reproduction. E3/E4 require an actual accessible recipe and complete qualified fixture. Include a separate missing-dependency variant if relevant.

**Unassisted success:** The participant finds the intended recipe/version, understands fixed scientific settings and expected evidence, and preserves them through preparation. If admitted, the result identifies the recipe/run and the comparison outcome. If an exact dependency is unavailable, the participant recognizes reproduction is blocked, identifies the missing dependency and uses an offered valid next action without silently substituting another dataset, origin or model build.

**Critical errors:** Calling an adapted run an exact reproduction; accepting unavailable assets as complete; replacing the historical 786-hour Watauga fixture with a proposed 20-hour fixture or different-origin production history; interpreting a successful job exit as numerical agreement.

**Capture:** Recipe discovery, changes attempted, blocked or admitted decision, interpretation of verification, and ability to locate a reusable evidence bundle. E4 additionally records the independent operator's environment, actions and comparison result; a facilitator-led reproduction is assisted evidence.

### UX-04 — Adapt and compare an experiment

**Maps to:** UO-01, UO-02, UO-05, UO-06, UO-07, UO-08, UO-09.

**Participant prompt:** “Keep this baseline experiment unchanged. Create a separate version with the one supported change described in the scenario, then explain how you would compare the two fairly.”

**Facilitator setup:** Choose a supported change whose meaning is predeclared: for example issue schedule or retained output leads. Treat parameter changes as a separate, more demanding scenario only after their physical semantics are qualified. The manifest defines which results can be compared and which sources/settings must remain fixed. Do not ask participants to choose scientifically arbitrary values to make a screen pass.

**Unassisted success:** The participant duplicates or creates a separate experiment, sees the exact change summary, retains an identifiable baseline and selects a comparison appropriate to matching outputs. The interface distinguishes a retained-product projection from a new physical experiment. Changed physical parameters create new configuration/history identities and require the appropriate fresh antecedent simulation; they do not reuse old state by assumption.

**Critical errors:** Overwriting the baseline; losing track of which input changed; comparing different issues/leads as paired values; applying a parameter correction only to archived numbers; claiming forecast skill improvement from a workflow-equivalence comparison.

**Capture:** Baseline/variant IDs, selected change, participant's comparison explanation, incompatibility warnings and any unintended edits. At E1/E2, score the interaction and reasoning only; do not report a measured hydrologic comparison.

### UX-05 — Resolve ambiguous location, unsupported coverage or missing inputs

**Maps to:** UO-01, UO-02, UO-03, UO-05, UO-07, UO-09.

**Participant prompt:** “Set up the experiment in this request. Check that the location and available inputs match it. If something prevents the request from running, explain what is missing or uncertain and choose an acceptable next action.”

**Facilitator setup:** Prepare separate scenario variants: an ambiguous location name with distinguishable map/gauge candidates; a correctly identified watershed outside supported coverage; unavailable historical weather; missing issue-specific forecast weather; and a temporary upstream lookup failure. Preserve submitted gauge/reach identifiers and their different identifier systems. Include declared uncertainty rather than replacing the problem with an artificially complete dataset. Record which variants each participant attempts.

**Successful blocked outcome:** The participant can distinguish ambiguous location from unsupported geography, missing historical inputs, missing forecast issues and temporarily unknown availability; recognizes that a run has not been submitted or completed; and can save the request, retry a transient lookup, narrow it knowingly, select a supported alternative knowingly, or inspect what restoration requires. A temporary upstream failure must not become a claim that the data do not exist. Missing optional evaluation observations must not be confused with missing inputs required to simulate. Any changed period, domain, issue mask or recipe is visible and accepted as a changed experiment. Declining to proceed when no scientifically valid option exists is successful handling of the case.

**Critical errors:** Arbitrary first-match watershed selection; unexplained nearest-domain substitution; fabricated weather; silent shortening of initialization; excluding a forecast issue while also skipping history needed by later states; presenting approved historical imputation as operationally available data without its lineage.

**Capture:** Error language understood, suggested versus chosen action, retained intent and treatment/coverage changes. A valid block may pass UX-05 while the desired physical workflow remains unavailable. Record product-coverage failure separately from user error.

### UX-06 — Monitor and recover a campaign

**Maps to:** UO-02, UO-04, UO-05, UO-09.

**Participant prompt:** “Your campaign has been submitted. Check its current state, leave the browser, then return in another permitted session and find the same campaign and available results. In the interruption scenario, explain what happened and recover it if the product offers a valid recovery path.”

**Facilitator setup:** Supply labelled preparation/queued/running/partial/failed/complete/verified states with their actual evidence. At E2 use a bounded synthetic interruption; at E3 use only the already qualified failure/recovery scenario. Freeze expected completed issues and recovery eligibility. Include a case where changing input identities or a missing history dependency correctly prevents resume.

**Unassisted success:** The participant returns to the same persistent campaign, distinguishes successful submission from running and running from verified completion, identifies which outputs are usable, and understands whether recovery is possible. At the appropriate implemented evidence level, closing the browser does not cancel or duplicate the remote job. When eligible, recovery preserves the original configuration/origin and verified completed issues; the user understands that history may be replayed and that additional work may be required. When ineligible, they identify the cause and avoid relabelling a new experiment as a resume.

**Critical errors:** Downloading partial outputs as the complete verified archive; starting duplicate campaigns unintentionally; treating a channel snapshot as a full land restart; believing progress cannot regress during replay; accepting changes to original inputs while claiming continuation of the same run.

**Capture:** Status interpretation, interruption recognition, chosen action, duplicate submissions, preservation of completed-result identity and recovery explanation. Record actual job events separately from UI representations. A prototype “Resume” interaction does not establish real recovery or instant restart.

### UX-07 — Inspect, verify, download and share results

**Maps to:** UO-02, UO-05, UO-07, UO-08, UO-09.

**Participant prompt:** “Find the results for the stated question, determine what has been verified, and obtain a reusable download with enough information for another researcher to understand the experiment. Show what another person would receive through the product's sharing option.”

**Facilitator setup:** Use a versioned result bundle with declared completeness, units, verification state, source/treatment lineage, settings and known limitations. Provide a contrast between a preview, a completed output and a verified output. E1/E2 downloads and share destinations must remain clearly labelled demonstrations; do not publish scientific results or send messages as part of this protocol.

**Unassisted success:** The participant selects the intended location/issues/leads or simulation period, reads units and axes, recognizes evidence/limitations and downloads the expected data plus recipe/Methods/provenance information. Reforecast export preserves issue/lead/valid time. They can identify the shared artifact, its version and access scope, and distinguish sharing a view or recipe from granting access to unavailable data. An integrity or completeness failure prevents the interface from representing the product as verified.

**Critical errors:** Calling raw model output observations or corrected predictions; interpreting unavailable verification as passed; dropping issue identity from a forecast export; sharing the wrong version or unintended access scope; treating file existence as a successful verified download.

**Capture:** Data selection, comprehension answers, download membership/checksums as applicable, retained recipe/identity, share preview/access interpretation and any missing material. External reproduction is scored separately from the act of downloading or sharing.

## Outcome definitions

Assign one primary outcome per participant/task/variant, then record errors and assistance independently. Keep the original outcome when an assisted continuation succeeds.

| Code | Definition | Counting rule |
|---|---|---|
| SU — Unassisted supported success | Participant reaches the declared supported end state with no directional facilitator assistance and no unresolved critical error | Count only within the declared evidence level; using built-in help is allowed |
| SB — Unassisted expected-block success | The scenario is intentionally unavailable or unsafe to continue; participant understands the block and takes an appropriate valid next action or correctly stops | Counts as success for blocked-case comprehension, not as delivered model output |
| SA — Assisted completion | A directional hint, developer intervention or facilitator operation was needed to reach the end state | Record the help and resulting endpoint; exclude from unassisted counts |
| FE — User-facing task failure | Supported end state is not reached, or a consequential error remains undetected | Record whether the cause is navigation, terminology, scientific interpretation or interaction design; do not blame the participant by default |
| PB — Unexpected product/environment block | An unplanned outage, missing capability or invalid fixture prevents the intended task | Report separately from FE; retain it as product availability evidence and do not quietly remove it from attempted-task totals |
| NA — Not attempted/not eligible | Task was not started or prerequisite evidence level was unavailable | Report reason; no success, failure or completion-time value is invented |

**Recoverable error:** a wrong intermediate choice the participant recognizes and fixes using the product before it changes the submitted scientific request or output interpretation. Record both the error and self-recovery; it does not automatically turn an otherwise successful task into failure.

**Critical error:** a choice or interpretation that would invalidate the intended science, misrepresent execution/evidence, lose experiment identity, silently change inputs, expose results contrary to the selected access scope, or start unauthorized/unbounded work. A critical error caught before submission remains a finding; an unresolved critical error cannot receive SU/SB. Prototype tasks can expose a critical design failure even though no real model or external action occurred.

**Recovery success:** the participant reaches the correct recoverable state through the interface, understands what is preserved and what will be repeated, and the appropriate evidence level confirms the system behavior. Resetting a prototype screen establishes neither successful durable recovery nor physical reference equivalence.

## Resource and progress comprehension

Do not supply invented runtime, cost, storage or confidence numbers. If no empirical basis exists, show the estimate as unavailable with the reason and explain what preparation/measurement can resolve. If an estimate exists, present its scope, assumptions, range or uncertainty, and distinction from measured usage and hard resource limits. Label queued time, preparation, model execution, verification and history replay separately where those states are actually known.

Use a teach-back prompt: “Which parts of this resource summary are estimates, which are limits, and what could change?” A successful answer need not use technical terms; it must not treat an estimate as a guarantee or mistake incomplete preparation for execution readiness. Record the participant's intended action when the estimate is too uncertain to support their decision. For the 18-step native profile, reduced retained leads do not imply reduced physical integration cost.

No active session should incur new paid resources, real publications or messages solely to test a control. At E1/E2 those controls operate against explicit demonstrations. At E3/E4 the concrete test plan must already specify the authorized environment, budget and scientific recipe; this document authorizes none of those actions.

## Evidence and scorecard templates

Keep an evaluation manifest for each round. Include: protocol revision; interface/software revision; date; facilitator; participant IDs and relevant experience; task/variant manifests; evidence levels and prerequisites; display/accessibility setup; assistance policy; recording consent; result-artifact paths; and the predeclared criteria. Scenario truth includes the intended geographic selection, supported coverage, exact mode/time/settings, expected blocked/admitted state, and actual versus simulated backend behavior.

Copy this task scorecard for each attempt. Blank fields mean not yet recorded, not zero or success.

| Field | Value to record |
|---|---|
| Round / participant / task variant | `[round ID] / [participant ID] / [UX-01…UX-07 and variant]` |
| Objective IDs | `[applicable UO IDs; note proposed objectives]` |
| Evidence level / revision / prerequisites | `[E1–E4; exact revision; prerequisites met or unmet]` |
| Intended outcome / actual outcome | `[scenario truth] / [observed endpoint]` |
| Primary outcome | `[SU / SB / SA / FE / PB / NA]` |
| Assistance | `[none, neutral probes, first directional hint, developer action; exact point]` |
| Errors and self-recovery | `[observed errors; detected by user/UI/facilitator; recovered or unresolved]` |
| Scientific interpretation | `[mode, location, origin, issue/lead, forcing, identity and verification answers as relevant]` |
| Resource understanding | `[estimate versus limit; uncertainty understood; actual usage if measured]` |
| Timing, if observed | `[active interaction; system wait; interruptions; unavailable fields explicitly marked]` |
| Confidence/feedback | `[participant's own statement; do not infer certainty from silence]` |
| Evidence references | `[consented screen note/clip, event record, lock/recipe, output/verification artifact]` |
| Finding / severity / next action | `[stable finding ID; critical/major/minor; owner; proposed change]` |
| Retest | `[revision and outcome, or not yet tested]` |

Use a separate aggregate table so blocked tasks and assistance remain visible:

| Journey / objective IDs / evidence level | Invited / attempted / eligible | SU | SB | SA | FE | PB | NA | Unresolved critical findings | Evidence / next decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `[UX ID / UO IDs / E level]` | `[counts]` | `[count]` | `[count]` | `[count]` | `[count]` | `[count]` | `[count]` | `[IDs]` | `[links and decision]` |

Report counts and denominators for the actual participants and tasks, including dropouts and unexpected product blocks. With 3–5 purposively selected participants, do not present task rates as estimates of all hydrologists or claim statistical significance. Do not pool multiple attempts by the same person as independent participants. Distinguish first-attempt performance from performance after hints or design revisions.

## Proposed acceptance and iteration rules

These targets are proposals to approve and refine before a round; **none are measured results**. No duration, success percentage or system throughput is asserted.

1. **Scientific comprehension gate:** every participant in the final formative round can identify the intended mode, geography/time scope and verified-versus-unverified state for their assigned critical tasks. Any unresolved critical error requires a design change and retest before the affected workflow advances.
2. **Independent interaction target:** aim for every supported core task to be completed unassisted in the final round, using only the normal interface/help. Report the actual SU counts even if the target is missed; do not conceal SA, FE or PB outcomes behind a positive overall label.
3. **Blocked-case target:** participants assigned each blocker variant can distinguish its cause, recognize that no valid run has completed and select an honest next action. Passing this target improves explanation and control; it does not close the missing data/runtime capability.
4. **Preparation/remote-execution gate:** UO-03/UO-04 advance from concept to implemented only when actual qualified preparation/execution records substantiate the interface's claims. UI animation, queued status, simulated output and passing planner CI are insufficient.
5. **Result-integrity gate:** exported/shown results retain their declared units, time keys, version/recipe identity, exclusions and evidence level; no partial, synthetic or failed output is represented as a verified complete archive. Scientific numeric equivalence uses the separate benchmark protocol, not a usability score.
6. **Independent reproduction gate:** UO-09 scientific reproduction requires E4 evidence and the relevant M5 conditions, including a researcher who did not build the system. Unassisted E1 success is an encouraging design result, not completion of this gate.
7. **Iteration rule:** retain failed attempts and defects, fix the highest-consequence findings first, and retest affected tasks on the new revision. Predeclare whether returning or new participants are used and report familiarity effects. Never upgrade an evidence level solely because navigation becomes easier.

The facilitator's report should state what changed, which journey/objective it addressed, what was observed, what remains uncertain and the next bounded evaluation. Link actionable findings to development work packages and, when results exist, to manuscript claims. This protocol adds a researcher-facing acceptance layer while preserving the separate implementation, physical-qualification and reproducibility milestones.
