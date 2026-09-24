# Runtime inspection and qualification

The implemented runtime inspector answers whether supplied resident files match the selected historical reference and what remains unresolved. Every report currently returns `status: blocked` and `execution_ready: false`. Matching metadata, passing unit tests and matching binary hashes do not qualify a public hydrologic runtime.

## Use the offline API

From an installed package or a checkout with `src` on the Python path:

```python
from pathlib import Path
from ngen_reforecast.runtime import inspect_runtime

report = inspect_runtime(Path("profiles/nextgen-arm64-v3.json"))
# To inspect an already prepared local staging directory explicitly:
# report = inspect_runtime(Path("profiles/nextgen-arm64-v3.json"), Path(".local/assets"))
print(report["status"], report["execution_ready"])
```

No source-cache discovery, network request, process invocation, container activation, file restoration, source mutation or model run occurs. The command reads the exact profile first, checks host platform, then checks only assets under the caller-supplied root. Output paths are portable paths relative to that root; the local root itself is never printed. On a host without no-follow directory APIs, safe asset inspection is unavailable and fails explicitly.

Use this staging layout only for authorized resident copies or new build products when their rights are resolved. Creating this directory does not imply that missing inputs should be copied or hydrated automatically:

```text
<explicit-local-root>/
  runtime/bin/ngen-shared
  runtime/lib/libiso_c_bmi.so
  source/pristine/<five original framework file paths>
  source/patched/<ten modified or new framework file paths>
  fixture/CONTRACT.json
  fixture/<remaining 180 members listed in native/ASSET_CLOSURE.json>
```

The inspector admits the one immutable historical profile. It verifies its canonical JSON SHA-256, rejects duplicate JSON keys and profile files larger than 1 MiB, and accepts harmless formatting/key-order changes. The accompanying JSON Schema admits exactly the same profile metadata. This intentionally prevents an arbitrary profile from replacing the executable hash or declaring itself qualified.

Each asset path is checked using directory file descriptors and no-follow opens. Absolute/parent-traversal paths, symlink directories or leaves, dataless/offline entries and nonregular files fail before their content is read. File-size mismatches fail before hashing. A stable resident regular file is read in 64 KiB chunks, subject to a 16 MiB per-file and 128 MiB aggregate bound, with at most 256 profile entries; the current profile has 198. File identity, size and modification metadata are checked across the read. A changing file fails, and its admitted size is conservatively charged to the budget. Known SHA-256 values must match exactly. Unknown expected hashes yield observed hashes and `ASSET_IDENTITY_UNRESOLVED`, never a verified result.

Inspection is a local integrity check, not authentication against an adversary modifying metadata and content together. The fixture remains incomplete even if all currently known hashes match. The doctor does not inspect Docker state, resolve dynamic libraries, validate forcing numerical contents or prove scientific equivalence.

The [CFE drainage attribute finding](CFE_PARAMETER_FINDING.md) adds an unresolved parameter-semantics requirement: record whether CFE `slop` came from `mean.slope` or `mean.slope_1km`, with hydrofabric metadata, generator identity, conversions and the actual library version. Hash agreement can preserve an erroneous mapping. This is a qualification requirement, not a check currently implemented by `doctor`. Keep the immutable historical profile unchanged; an adopted correction requires a new configuration/profile identity and newly evolved antecedent history.

## Exact candidate example

The historical Watauga candidate has 31 catchments, gauge `03479000` at nexus `1017693`, origin `2021-12-01T00:00:00Z`, 786 historical hours and stop `2022-01-02T18:00:00Z`. Its issues are epochs `1641078000` and `1641081600`, each with 18 branch intervals and output leads 1–18, for 36 keyed forecast rows. The expected contract hash is `b1763b05cfb9fef1cd45b925662149dca3cbcca55ce0535051a35773ca3108fb`.

The preserved inventory lists 181 fixture members: 49 resident and 132 dataless at inspection time. These are historical inventory observations, not present-day claims about the original storage. The public profile can bind the contract from its recorded execution reference and the 49 inspected file hashes; 131 member hashes still require resolution from a sealed original manifest. `native/ASSET_CLOSURE.json` retains every filename and historical size/status without private local paths.

Do not substitute the available production history with a 2018 origin, shorten spinup, infer a land state from routing q0 or silently regenerate altered weather. A complete example must preserve physical configuration, parameters, history/forecast forcing sources and interval semantics, original origin and runtime identity together.

## Qualification acceptance

The [24 September first-experiment decision](FIRST_PHYSICAL_EXPERIMENT.md) and [benchmark protocol 0.3](../benchmarks/PROTOCOL.md) separate admission from the evidence the first run will produce. The implemented inspector described above is unchanged; the following are future acceptance stages, not new inspector capabilities.

1. **Build and loader admission (RF-008).** Close source, toolchain, component, routing, image and middleware dependencies in the build recipe; retain notices and artifact-specific source/redistribution provenance. Produce the clean Linux ARM64 build, actual loader evidence and enforced-limit checks. Bind any controlled rebuild to its actual artifact identities rather than silently replacing the historical profile. This stage does not require already achieved physical equivalence.
2. **Input and diagnostic-parameter admission (RF-005A/RF-009A).** Restore and seal every required original Watauga execution input without altering the original research storage. Verify geometry/realization/parameters, every forcing member and all time/units/source identities. Bind the diagnostic historical configuration and its known CFE concern. Preserve all existing historical reference identities and verify any historical output bytes used for comparison. New reference outputs and their hashes are generated in the next stage; they are not prerequisite inputs. Inventory equality and byte hashes are necessary but not sufficient content validation. Missing required execution inputs or identities keep the first task blocked.
3. **Independent sequential references (RF-010; first phases of E03).** Start with the exact 786-hour/two-issue Watauga recipe under protocol 0.3's existing budgets and E03 invocation ceiling. At issue I the independent process has consumed [origin, I); it then consumes interval starts I through I+17h and emits targets I+1h through I+18h. Validate clocks, complete finite/nonnegative keys and successful process completion, then seal new reference hashes. The two references do not yet establish branched equivalence or an E03 pass. Do not substitute a compact or production-origin fixture under this identity.
4. **Physical comparison and reference-output closure (RF-011/RF-009B; remaining E03 phases).** Preserve the parent's complete 786-step trajectory, run the uninterrupted-history and shared-branch controls, and compare against the sealed references. Retain zero-exit reaped-child receipts, exact output keys/clocks, the symmetric `math.isclose` rule with absolute `1e-6` and relative `1e-5` discharge tolerances, native/middleware/component identities and immutable output checksums. Historical zero-difference receipts cannot fill a newly unmeasured result. Complete E03 before its dependent physical groups.
5. **Reliability, transfer and release-profile evidence.** Exercise parent/sibling isolation, serial/concurrent consistency, child failure, parent interruption and explicit replay recovery under the declared groups. Treat a routing snapshot as channel-only state; no complete durable land checkpoint is available. Completed issues may be suppressed only after commit verification while history is replayed. Repeat the declared transfer cases on New River with its two nested gauges as one physical domain. RF-005B evaluates a corrected candidate later under a separate paired manifest and invocation allowance; any adopted profile requires its own applicable physical evidence. Diagnostic historical-baseline success is not corrected-parameter or release qualification.
6. **Independent reproduction and final release.** Freeze an immutable, licensed, accessible **REPRODUCTION_CANDIDATE** as specified in [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md), then conduct E09 on a qualified clean environment. Preserve the frozen example's identity; a supported variation receives a new experiment identity and recorded differences. Another agent on the same machine is an internal check, not external researcher reproduction. Final release follows that evidence, admitted browser-user evidence under [UX_EVIDENCE_CONTRACT.md](UX_EVIDENCE_CONTRACT.md), and any fixes/retests. E09's physical allowance does not automatically include browser-user runs or additional retest campaigns.

RF-005B's coupled result and RF-009B's newly generated output hashes are downstream of the first independent reference. Neither may be used as a prerequisite that prevents that reference from being built. If exact original inputs cannot be restored, report the blocked fields and propose an explicit new fixture/protocol decision; do not alter the protected historical recipe.

The first increment's tests exercise path confinement, dataless rejection, profile/executable mismatch, missing assets, platform restrictions, byte bounds and unknown identities with synthetic temporary files. Their evidence class is software unit testing. No test file or historical receipt is counted as a new real-model build, execution or performance measurement.
