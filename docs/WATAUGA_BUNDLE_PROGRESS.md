# Watauga bundle restoration progress

Observed 10 October 2026 under the owner's continued multiagent implementation request. This advances RF-009A, UO-05 and UX-02/05. The original research workspaces remained read-only; no cloud hydration, download, inherited-code import or model execution occurred in this workstream.

The exact original Watauga contract is now resident and verified. Its 45,886 bytes match the pre-existing SHA-256 `b1763b05cfb9fef1cd45b925662149dca3cbcca55ce0535051a35773ca3108fb`. Reading its 179 member records resolves **all 131 previously unknown expected member hashes**, with no conflicts against the historical inventory's known hashes or sizes. The [derived identity supplement](evidence/watauga-fixture-bindings-20261010.json) preserves the [historical closure](../native/ASSET_CLOSURE.json) unchanged. A content-derived hash is never promoted to an expected identity merely because a candidate file is available.

**The input bundle remains incomplete: 44 of 181 exact members were restored into private local staging; 137 remain unavailable.** The contract is the only resident original fixture member in the fresh metadata inspection; the other 180 original members are dataless and were not opened. Exact hash-matching preservation copies supplied 43 additional members. The [fresh evidence report](evidence/watauga-bundle-20261010.json) records member-level availability and custody, separate from expected-identity closure.

| Available exact members | Count | Remaining limitation |
|---|---:|---|
| Original `CONTRACT.json` | 1 | Describes intended inputs; it is not their data payload |
| Original CFE configurations | 31 | Original drainage mapping requires diagnostic scientific admission |
| Watauga hydrofabric | 1 | Spatial/content validation remains a separate check |
| Historical native binary and BMI middleware | 2 | Matching bytes do not qualify a Linux environment or loaded components |
| Historical scripts and Python modules | 9 | Preserved as inert private bytes; not imported, executed or publicly distributed |
| **Total** | **44** | **137 exact members remain unavailable** |

Unavailable members include both complete branch-forcing sets (66 members), 64 input members including the 31 historical forcing CSVs and 31 Noah namelists, and seven other fixture members. Similar filenames and sizes were insufficient: 586 inspected preservation candidates failed the expected hash and were rejected. Later production weather, different Noah configurations and different experiment origins were not used as replacements.

The bounded search covered known HYDRA preservation roots and five related original preparation directories. Some large roots reached their explicit enumeration ceilings; the report identifies these incomplete searches. This is a record of inspected candidates, not proof that no recoverable copy exists elsewhere. The exact inspected source candidates had zero changes in device, inode, mode, size, modification time, change time and dataless flags before versus after staging. The coordinator separately checks the protected Reforecast workspace.

## Implemented operator utilities

[`bundle.py`](../src/ngen_reforecast/bundle.py) is independently authored, standard-library code. It performs no discovery or acquisition by itself:

- `bind_fixture_contract(raw, historical_assets)` verifies an already-bound contract before deriving an identity supplement; rejects conflicting bindings and malformed/unsafe paths.
- `inventory_bundle(assets, source_roots, candidates=None)` checks explicitly selected resident files with typed missing, dataless, mismatch, unbound and verified results.
- `stage_bundle(assets, source_roots, destination, candidates=None)` creates a fresh private directory, copies only verified bytes, verifies destination bytes and makes each staged file read-only. It refuses overwrite and destinations within a source root. It never hardlinks source files.

Source aliases keep absolute host paths out of returned reports. Asset and candidate paths must be normalized relative paths. Descriptor-based traversal rejects symlinks and dataless files/directories before content access. Per-file source reads cannot exceed 16 MiB; aggregate reads, including reserved bytes after a failed/raced read, cannot exceed 128 MiB. This inspection consumed 5,971,617 source bytes across accepted and rejected candidates. Source-root declarations are the operator's responsibility; the utility does not authorize access or redistribution.

All staged material is under the ignored `.local/watauga-bundle-20261010/fixture/` in the active software checkout. The original bytes, full candidate-path receipt and before/after metadata snapshots remain private under ignored `.local/`. Public changes contain independently authored code, tests, relative identity metadata and summarized evidence only. Selecting a project license or clearing inherited asset rights is still separate work.

A partial bundle always reports `input_bytes_verified=false`; even a byte-complete bundle retains `scientific_semantics_verified=false` and `execution_ready=false`. Eighteen synthetic unit tests passed for identity resolution, missing/changed files, bounds, rejected source paths, no-overwrite staging and retained incomplete states. These are software checks, not physical forecast results.

## Observed original CFE mapping

A [fresh content audit](evidence/watauga-cfe-mapping-20261010.json) used only the restored private CFE configurations and hydrofabric, rechecking all 32 input hashes before and after. The GeoPackage was opened through SQLite with `mode=ro`, `immutable=1` and `query_only=ON`; no journal or sidecar was created. All 31 catchment/configuration keys matched.

Every original `soil_params.slop` numeric setting equals its catchment's `mean.slope` value exactly; none equals `mean.slope_1km`. The former ranges from 83.1903 to 87.9693 (median 86.9488); the latter ranges from 0.043079 to 0.062094 (median 0.043415). The CFE files label the setting `[m/m]`. The inspected source schema supplies no authoritative per-attribute unit definition, so source units remain unknown. Matching numerical values establishes correspondence; it does not establish the original generator's transformation provenance, valid parameter semantics or the effect of a corrected coupled simulation. Per-catchment data remains private, with its checksum recorded in the public audit.

The implemented `validate_configuration` API was then exercised against the actual 31 configurations, a private attribute table derived from the verified hydrofabric, and the exact CFE library extracted by the runtime workstream from the pinned image. All 33 bound assets and 31 drainage-value pairs passed the narrow content checks. The report retains the inherited-mapping warning plus 31 out-of-range warnings; generator revision remains explicitly null, source-attribute units and meanings remain unknown, and full configuration, loaded-library and physical qualification remain false. No model library was loaded. The full per-catchment API report remains private; its aggregate counts and validation identity are recorded in the public mapping receipt. All 33 inspected input hashes and metadata were unchanged.

This confirms the known drainage-attribute concern in the exact baseline bytes now restored. The baseline remains diagnostic-only pending the rest of RF-005A. RF-005B's candidate mapping and full coupled qualification remain separate, as required by the working plan. No parameters were edited and no model was run.

## Separate backup lookup follow-up

A separately authorized read-only lookup reported no complete, fully resident `day-model-preparation01` backup within its bounded search. It independently reverified the same 44 staged files (4,452,920 bytes), with the other 137 expected paths absent. Known preservation paths, shallow likely archive/download locations and mounted volumes supplied no additional candidate. A resident review ZIP's central-directory index (2,350 entries; 424,163 bytes) contains related build/source evidence but no entries under `day-model-preparation01`; the index check does not exclude identical payloads stored under other paths. A historical preservation receipt stating that external backup was pending is not evidence that a complete backup exists.

The [follow-up record](evidence/watauga-backup-search-followup-20261010.json) explicitly attributes these observations to the separate lookup. The coordinator reconciled its counts with the existing committed inventory; it did not replay the search or receive a public raw search log. This was not an exhaustive disk scan and does not establish that no backup exists elsewhere. The restoration count remains 44/181, with no new physical or scientific qualification.

## Next closure step

Restore the remaining exact hash-bound members into an isolated permitted source location, or identify an existing resident equivalent. Do not hydrate the protected originals or replace their contents. Re-run bounded identity/staging inspection with explicit source aliases, then validate content, units, coverage, original clock boundaries and model configuration using the scientific-admission checks. These requirements preserve the [first physical experiment](FIRST_PHYSICAL_EXPERIMENT.md): 31 catchments, the 1 December 2021 origin, 786-hour parent history, two declared issues and 18 hourly forecast steps each. Changing or regenerating the fixture requires a separately identified scientific recipe and cannot silently close this baseline.

## Separate public development fixture

The owner's subsequent request activated RF-009A-PUBLIC. A [new public-source fixture](../fixtures/watauga-public-v1/README.md) now supplies independently generated geometry, configurations, complete weather and three serial input jobs for development. It has its own recipe and evidence identities, and zero model invocations. The historical restoration count remains 44/181 with 137 unavailable members; new bytes do not close that historical contract. A [custody-inventory/archive review](LOCAL_RECOVERY_DECISION_2026-10-10.md) found no new exact-hash recovery lead, so a broader scan remains contingent on a concrete named candidate.
