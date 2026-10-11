# Runtime and input admission review — 10 October 2026

**Disposition: the first physical experiment remains blocked.** The implementation kickoff authorizes progress on the software and manuscript; the [first-experiment contract](FIRST_PHYSICAL_EXPERIMENT.md) still requires a complete build and input recipe before model execution. This review supports RF-005A/008/009A, UO-03/04/05/09 and the physical prerequisites of UX-02/06/07. It does not change any experiment, threshold or invocation allowance.

The [sanitized observation receipt](evidence/runtime-admission-20261010.json) binds the inspected public files and reports fresh local probes separately from historical identities. Dates use the owner's client context. All probes were read-only, with five-second process timeouts for Docker commands. No original research folder was accessed, no source was hydrated, and no VM, container, compiler, dependency download, cloud resource or model was started. The checked Git revision is a baseline for the inspection, not a claim that parallel implementation edits have already been committed or tested.

## Fresh observations

| Surface | Observed on 10 October | Consequence |
|---|---|---|
| Local platform | Darwin 25.6.0, ARM64; CPython 3.14.7 | Suitable for the offline Python work; it is not the required Linux ARM64 native host |
| Container interface | Docker client 29.7.2; selected context uses a local Unix endpoint; bounded server query returned exit 1 because its socket was absent | No server responded at that endpoint; the review did not inspect other contexts or activate Colima/Lima |
| Command availability | `docker`, `colima`, `limactl`, `python3` and `git` are on PATH; `cmake` and `podman` are not | PATH presence is not a qualified worker or complete toolchain, and PATH absence is not a machine-wide inventory |
| Public manifests | 198 profile entries: 181 fixture members, 10 overlay files, 5 preimages, executable and middleware | All declared payload staging paths have zero matching tracked payloads; this is not a search for authorized staged assets elsewhere |
| Fixture identities | 50 of 181 fixture members have a recorded hash; 131 do not | The contract hash is one of the 50; complete input identity/content closure is still required |
| Admission API | Exact historical profile identity verified; `status: blocked`, `execution_ready: false`; zero asset reads | No asset root was supplied, so the API checked the profile and host without discovering or inspecting research storage |
| Build/component closure | Public profile still declares incomplete source lock, no component source-to-binary attestation and no public loader verification | Pins specify a target; they do not establish an obtainable complete build or actual loaded physical libraries |

The 131 unresolved hashes break down into 55 forecast-forcing/preparation members, 28 historical-forcing files, 28 CFE configuration files, 10 Noah configuration files, 8 fixture implementation files and 2 fixture-local runtime copies. The separate native entries have recorded executable/middleware pins; the intended binding of those fixture-local copies still needs explicit closure. This breakdown identifies work within the existing inventory and does not claim that those bytes are unavailable in every permitted source.

The public inventory still records **49 resident and 132 dataless fixture members on 18 September**, with 906,503 resident bytes inspected then. These are historical observations, not refreshed facts about today's original files. This review did not open those files. The recorded fixture remains Watauga's 31 catchments, original 2021-12-01 UTC origin, 786 historical updates, two specified January 2022 issues and 18 model steps per branch. Existing public hashes and all historical evidence remain unchanged.

## Concrete closure assignments

Owners below are proposed implementation roles, not an assignment of rights, authorship or paid resources. The coordinator should give each role an explicit permitted staging area and review its completed receipt before admitting dependent execution.

| Gate / proposed owner | Exact missing deliverable | Admission evidence and dependency |
|---|---|---|
| RF-008 worker — runtime lead | Select one Linux ARM64 worker and a complete bounded build environment | Record OS/architecture, toolchain availability, isolated work/output paths, whole-job controls and permitted resources; local Docker installation alone does not pass |
| RF-008 source — native integration lead | Authorized full `ngen` source at `9175b640…`, its required submodules, five matching preimages and all ten V3 overlay files | Complete tree/content manifest, deterministic patch application and pre/post hashes; a selected-file list is insufficient |
| RF-008 toolchain — build lead | Exact compiler/binutils/CMake/libc/Fortran and Boost/NetCDF/SQLite/UDUNITS/BMI dependency lock, full CMake invocation | Resolve unknown versions/options from allowed source evidence; identify any controlled rebuild as a new artifact when bytes differ |
| RF-008 components — component lead | SLOTH, NoahOWP and CFE source/options/toolchain/library attestations; exact image manifest/layers | Match actual library bytes and dependencies to declared sources and notices; historical framework gitlinks alone cannot attest the image libraries |
| RF-008 routing/loader — runtime lead | t-route environment and service at the recorded identity; relocatable middleware resolution | Lock Python/scientific dependencies, bind routing service bytes and capture the actual native loader resolution after a permitted build; retain single-thread/profile guard evidence |
| RF-009A inputs — domain/forcing lead | Permitted isolated staging of the exact original fixture; authoritative identities for 131 currently unhashed members | Verify the sealed contract and preparation manifests, all required input bytes, geometry, realization, parameters, forecast/history interval coverage, source generations and units. Source locators or a replacement origin cannot fill missing inputs |
| RF-005A diagnostic profile — scientific lead | Original CFE field mapping, units/conversions, hydrofabric/generator identities and actual component binding | Explicitly admit the known-concern original mapping only for diagnostic reproduction; copied hashes alone do not settle the mapping's meaning |
| Rights/access — release coordinator | Artifact-specific ownership/access and redistribution dispositions for sources, image, components and fixture | Establish terms before copying/distributing inherited payloads; select a core license before distributing a licensed reproduction candidate |
| RF-010 reference — benchmark lead | Executable independent-reference recipe after the preceding build/input/diagnostic gates | Use existing E03's two reference phases first; validate clocks/keys/process completion and seal the newly produced reference hashes before comparison consumers |

The first physical execution retains its existing bounds: **4 total vCPUs, 8 GiB whole-job memory, 4 GiB generated output and 1,800 seconds per invocation**. E03 still has five variants with one invocation each. The separate proposed native build has its own 2-CPU, 8-GiB, 30-minute ceiling in [BUILD_RECIPE.md](../native/BUILD_RECIPE.md); neither ceiling has been demonstrated sufficient. No extra probe simulation, sensitivity experiment or retry is added by this review.

RF-005B's coupled candidate-parameter comparison and any adopted release-profile qualification remain downstream, under their own bounded manifest. New reference-output hashes are produced by RF-010; requiring those hashes before their own first generation would recreate the resolved planning cycle.

## Next implementation boundary

Offline campaign contracts, browser interaction prototypes and manuscript methods can proceed while these gates are open. The next native handoff should be an obtainable, rights-aware source/input bundle and an executable bounded build recipe for a named Linux worker. If exact original inputs cannot be recovered through a permitted staging path, retain this blocked disposition and propose a separately identified fixture/protocol amendment. Do not silently shorten the original history, swap in production weather or replace the known-concern profile.

The manuscript [methods implementation map](../paper/METHODS_IMPLEMENTATION_MAP.md) identifies which claims this observation supports. It provides current readiness evidence only; it supplies no new hydrologic, efficiency, recovery, hosting or user-study result.
