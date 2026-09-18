# Watauga offline planning example

This example is a declaration of the smallest historical Watauga experiment identified in the feasibility dossier. It contains **no weather, geometry, parameters, model binaries or observed discharge** and cannot run a hydrologic model. The 786 historical provider intervals, two issue times and gauge/reach mapping come from `MINIMAL_EXAMPLE_MANIFEST.json` in the preserved feasibility dossier. No newly executed hydrologic result is claimed.

The planner reports one domain, one output location, two independent branches and 36 expected output rows. History starts at `2021-12-01T00:00:00Z` and stops at `2022-01-02T18:00:00Z` exclusive. At each issue I the parent has consumed [origin,I); branch interval starts are I through I+17h and forecast targets are I+1h through I+18h. The declaration reserves two parent CPUs and one CPU for each of at most two concurrent branches on a four-CPU host. The one-hour wall-time cap is an illustrative planning bound, not a measured runtime or an enforced execution limit.

All six physical asset roles are intentionally absent. `plan` returns explicit missing-role blockers and an unconditional runtime-qualification blocker. `execution_ready` remains false. The real historical fixture was incomplete at feasibility review: 132 of its 181 files were dataless. Restoring its exact contract, source identities, authorized assets and native runtime is a separate milestone. A different initialization origin or convenient weather substitute cannot repair that fixture.

After identities and redistribution rights are established, each domain may declare resident files relative to the campaign JSON directory:

```json
{"role": "historical_forcing", "path": "inputs/history/catchment.csv", "sha256": null, "size_bytes": null}
```

This is an illustrative asset entry, not an actual file or a complete forcing inventory. Replace nulls with the independently established lowercase SHA-256 and positive byte size. Unknown identity fields and absent files remain blockers. Supply every required file, including all catchments and issue-specific forecast weather; supplying one representative file per role is insufficient for physical qualification. The offline planner verifies declared bytes only, and does not parse scientific input coverage, units or physical realization semantics.

Asset paths cannot be absolute, traverse `..`, include symlinks or refer to dataless placeholders. Reads are bounded by declared per-file and total byte limits; this increment caps them at 1 GiB per file and 4 GiB total. It never hydrates, downloads, extracts an archive or launches the model. The Python validator also enforces exact object fields, canonical UTC hours, unique ordered issues, supported eighteen-hour horizon, positive resource bounds and one unchanged history origin. The accompanying JSON Schema covers structure; the Python validator supplies cross-field checks.

Multiple nested output locations belong inside a single domain when the complete physical state configuration agrees. They increase output-row count without multiplying historical domain trajectories. An input-identity digest in a plan is a declaration digest; it is not proof of a complete hydrologic checkpoint, model-state equivalence or permission to reuse an existing runtime.
