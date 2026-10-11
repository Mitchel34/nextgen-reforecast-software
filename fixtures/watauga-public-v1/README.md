# Watauga public development fixture

`watauga-public-rebuild-v1` is a newly prepared fixture for software development. Its [frozen recipe](recipe.json) and [component manifest](manifest.json) identify public source versions, geometry, the expected catchment/issue clocks, generated inputs and validation. It does not restore or replace historical E03.

| Component | Prepared and checked |
|---|---|
| Domain | 31 polygons; inclusive upstream closure of flowpath `wb-1017693`, selected through USGS NLDI COMID `19743430` |
| Configuration | 31 new CFE files using candidate `mean.slope_1km`, 31 Noah namelists, routing and realization files |
| Historical weather | Eight variables, 786 hours, 24,366 catchment-hour rows |
| Forecast weather | Two issues × 18 hourly leads; 1,116 catchment-hour rows |
| Source/content audit | 815 retained response hashes; complete clocks/keys/finite values; all 25,482 provider rows match decoded transformations |
| Serial input assembly | Three jobs, 291 bound files: history plus two independent origin-to-issue replays followed by forecast weather |

The public source and preparation details are in the [domain report](../../docs/PUBLIC_WATAUGA_DOMAIN_2026-10-10.md) and [weather report](../../docs/PUBLIC_FORCING_FEASIBILITY_2026-10-10.md). Conflicting gauge attributes are recorded. The selected routed reach is a spatial surrogate for the gauge inside that reach; the terminal nexus is not the selected discharge output.

## Local developer inputs

Payloads are retained under ignored `.local/public-fixture-20261010/` staging. They are not included in Git while artifact-specific redistribution terms remain unresolved.

- Domain/configuration component: `fixture-v2/DOMAIN_PREPARATION.json`.
- Weather component: `forcing/prepared-v3/PREPARATION.json`.
- Core content validation: `admission-v3/AUDIT.json` and three `forcing-manifest/0.2` manifests.
- Final assembled jobs: `native-assembly-v2/ASSEMBLY.json`, with `history/`, `serial-20220101T2300Z/` and `serial-20220102T0000Z/` inputs.

The independently authored tools in [scripts/public_fixture](../../scripts/public_fixture/) use optional pinned GIS/HDF5/Zarr dependencies, kept separate from the standard-library package. Domain preparation consumes a bounded, hash-bound public regional GeoPackage and pinned template receipt. Weather preparation acquires only required archive chunks/ranges; `--replay-from` validates retained bytes without network access. Assembly consumes those sealed receipts and pinned NextGen source contracts. All writes require fresh project-local staging; originals remain read-only.

The actual audit is reproducible from the repository root, using a fresh output directory:

```sh
PYTHONPATH=src python3 scripts/public_fixture/audit_prepared.py \
  --domain .local/public-fixture-20261010/fixture-v2/DOMAIN_PREPARATION.json \
  --weather .local/public-fixture-20261010/forcing/prepared-v3/PREPARATION.json \
  --output .local/public-fixture-20261010/new-audit
```

The repository's recipe supplies the expected population independently of the weather receipt. The audit refuses missing issues, shortened history, changed source/payload bytes, malformed provider rows and inconsistent transformations. Sparse NetCDF source declarations retain `sha256=null` for the unobserved whole object and bind actual fetched segments separately.

## Remaining qualification

Input contents and serial layout are complete for this development recipe. No model ran and execution readiness remains false. Native library/static-table paths, clean-build/component provenance, Noah endpoints, the routing cut, source-field units/derivation and scientific sampling/default choices still require qualification. Current AORC source-quality notices and historical availability limits remain recorded. A separate bounded experiment must freeze this new runtime/input identity and generate new independent physical references before equivalence or performance claims. Browser-driven acquisition and hosted execution remain future integration work.
