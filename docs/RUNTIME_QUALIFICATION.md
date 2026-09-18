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

## Exact candidate example

The historical Watauga candidate has 31 catchments, gauge `03479000` at nexus `1017693`, origin `2021-12-01T00:00:00Z`, 786 historical hours and stop `2022-01-02T18:00:00Z`. Its issues are epochs `1641078000` and `1641081600`, each with 18 branch intervals and output leads 1–18, for 36 keyed forecast rows. The expected contract hash is `b1763b05cfb9fef1cd45b925662149dca3cbcca55ce0535051a35773ca3108fb`.

The preserved inventory lists 181 fixture members: 49 resident and 132 dataless at inspection time. These are historical inventory observations, not present-day claims about the original storage. The public profile can bind the contract from its recorded execution reference and the 49 inspected file hashes; 131 member hashes still require resolution from a sealed original manifest. `native/ASSET_CLOSURE.json` retains every filename and historical size/status without private local paths.

Do not substitute the available production history with a 2018 origin, shorten spinup, infer a land state from routing q0 or silently regenerate altered weather. A complete example must preserve physical configuration, parameters, history/forecast forcing sources and interval semantics, original origin and runtime identity together.

## Qualification acceptance

1. Close source, toolchain, component, routing, image and middleware dependencies in the build recipe; retain notices and artifact-specific source/redistribution provenance. Produce the clean Linux ARM64 build and actual loader evidence.
2. Restore and verify the exact sealed fixture without altering the original research storage. Verify geometry/realization/parameters, every forcing member, all time/units/source identities, reference outputs and the complete expected file set. Inventory equality and byte hashes are necessary but not sufficient scientific validation.
3. Predeclare a bounded serial reference and branched Watauga experiment with CPU/memory/wall-time ceilings. At issue I the parent has consumed [origin, I); a branch consumes interval starts I through I+17h and emits targets I+1h through I+18h. Preserve the parent trajectory independently.
4. Retain zero-exit reaped-child receipts, exact output keys/clocks, finite nonnegative flow validation, comparison results using declared absolute `1e-6` and relative `1e-5` tolerances, native/middleware/component identities and immutable output checksums. Historical zero-difference receipts cannot fill a newly unmeasured result.
5. Exercise parent/sibling isolation, serial/concurrent consistency, child failure, parent interruption and explicit replay recovery from the original origin. Treat a routing snapshot as channel-only state; no complete durable land checkpoint is available. Completed issues may be suppressed only after commit verification while history is still replayed.
6. Repeat on New River with its two nested gauges as one physical domain, then obtain an independent clean-environment reproduction. Another agent on the same machine is an internal check, not external researcher reproduction.

The first increment's tests exercise path confinement, dataless rejection, profile/executable mismatch, missing assets, platform restrictions, byte bounds and unknown identities with synthetic temporary files. Their evidence class is software unit testing. No test file or historical receipt is counted as a new real-model build, execution or performance measurement.
