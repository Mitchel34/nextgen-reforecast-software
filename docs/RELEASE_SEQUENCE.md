# Candidate, evaluation and final release sequence

Working-plan decision, 24 September 2026. This resolves the circular reading of “release before independent reproduction” versus “independent reproduction before release.” It defines future handoffs; no candidate, license, independent reproduction or final release is created by this document. The [saved baseline](planning/2026-09-24_BASELINE.json) identifies the previous plan exactly.

## Stages and entry requirements

| Stage | Required inputs and artifact | What may follow | What it does not establish |
|---|---|---|---|
| Development snapshot | Identified source revision and accurate implemented-feature status | Internal tests, reviews and prototype work within the task's scope | A distributable physical runtime or independent reproduction |
| `REPRODUCTION_CANDIDATE` | Frozen source/package and build identities; selected license for included original work; resolved terms/notices for included dependencies and data; accessible complete fixture; expected outputs, comparison procedure and operator instructions; relevant internal physical evidence | Benchmark E09 uses this candidate as its input; candidate defects create findings and a new version when repaired | Final research release, successful external reproduction or browser usability |
| Browser study candidate | Frozen interface/service revision, eligible scenarios, access/resource policy and the [UX study manifest](UX_EVIDENCE_CONTRACT.md); the required physical receipts for claims involving real execution | Independent browser tasks at the declared evidence level; early prototype studies can happen well before a reproduction candidate exists | E09 success, production hosting readiness, or real execution when only prototype/synthetic evidence exists |
| Evaluation closeout | E09 operator record, admitted browser-study results, relevant physical/benchmark evidence, all failures and an explicit disposition of findings | Release coordinator reviews the candidate-to-final evidence mapping | Permission to hide failed attempts, change tolerances after results or claim untested capabilities |
| Final research/product release | Exact final versions with applicable evidence, resolved rights, accessible reproduction artifacts, closed release-critical findings, documentation and hosted-service requirements for claimed browser pathways | Final artifact archival and manuscript availability statement; publication/submission steps follow their separately established authority | Automatic manuscript submission, author approval or paid hosting authorization |

An engine reproduction candidate can enter E09 before the browser application is ready. A browser prototype can enter formative evaluation before the engine is physically qualified. These parallel tracks converge at the final hosted-product release; neither needs completion of the other merely to begin its own eligible evaluation. The final package must identify the actual engine/interface/service combination tested for its claims.

## Candidate manifest and accessibility

At candidate preparation, produce a versioned `candidate_manifest.json` with the following fields. This is an artifact contract, not an existing generated candidate or an executable schema:

- Candidate ID, creation date, status, source commit and candidate-manifest schema version.
- Included components and capabilities; engine, interface and service revisions where applicable; supported platform and explicitly excluded combinations.
- Immutable package/image/build identifiers and hashes; scientific profile, source/configuration/forcing/fixture identities; origin and complete expected keys.
- Selected original-code license, notices and dependency/data access or redistribution terms at their actual scopes; no inferred blanket license.
- Locations and hashes for the complete inputs, expected outputs, instructions and verification tooling; required credentials or access arrangements documented without retaining secrets.
- Internal evidence receipts with exact versions, protocol revisions, outcomes and open findings; the release claim each receipt supports.
- Intended E09 exercise, qualified clean environment and separately bounded resource allowance; links to any distinct browser-study manifest.
- Candidate maintainer/reviewer roles and the scope of allowed assistance; names are supplied when people are actually assigned.

The independent evaluator must be able to obtain the candidate and admitted inputs without private developer paths or unpublished repair steps. Accessible, versioned candidate artifacts can satisfy this requirement before a final journal-linked archival DOI exists. If required data cannot be redistributed, document a lawful, reproducible acquisition/access procedure that the evaluator can actually use; do not call a missing input package complete. Resolve the current core-license decision before distributing a candidate as licensed open-source software. The current repository remains subject to [LICENSE_STATUS.md](../LICENSE_STATUS.md).

The browser-study candidate additionally needs clear participant access boundaries and a pinned service revision throughout each study round. Prototype labels, simulated results and real-job receipts must agree with the claimed evidence level. This document does not select an account provider or hosting stack.

## Failure, fixes and retesting

Candidate contents and completed receipts are immutable. Retain unsuccessful attempts and assistance. A correction creates a new candidate ID and manifest, with the previous candidate and findings still accessible under the relevant terms.

Record an impact review linking every change to affected scientific identities, executable artifacts, tasks and claims. Rerun affected internal qualification and external reproduction/UX tasks before claiming them for the revised version. Scientific changes to inputs, parameters, origin, forcing or runtime cannot inherit incompatible reference outputs. A harmless documentation edit need not trigger every physical experiment, but its limited impact and any required usability retest must be justified explicitly. Additional invocations or participant sessions require the corresponding amended bounds; they are not hidden in the original allowance.

For a configuration variation in E09, retain the baseline experiment unchanged and create a new experiment identity with an explicit relationship to it. Reproducing the baseline and successfully executing the variation are separate outcomes. Do not interpret a request to vary issues/outputs as permission to reuse an incompatible scientific identity.

## Noncircular acceptance

The dependency order is:

**Internal qualification + rights/access closure → immutable reproduction candidate → E09 and relevant browser evidence → finding disposition/retesting → final release.**

RF-018/M7 assembles the final release; it is not a prerequisite for creating the reproduction candidate. RF-015/E09 and WEB-07 supply final evidence. A candidate's manifest must not claim these future results in order to admit the candidate itself. The final release manifest lists the candidate(s) tested, any intervening changes and the evidence validating the final artifacts.

The release coordinator owns candidate/final manifests and rights/access checks. Engine and scientific reviewers own physical qualification; an independent operator supplies E09 evidence; the UX lead supplies browser evidence; the manuscript lead checks that claims match those records. These are future roles, not assigned people or a contributor list.
