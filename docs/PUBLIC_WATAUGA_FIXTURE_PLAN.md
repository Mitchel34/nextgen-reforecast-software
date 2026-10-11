# Public Watauga development fixture — 10 October 2026

The owner authorized regenerating missing Watauga inputs from public data as a **new fixture** so software development can continue, and requested a broader local lookup only if evidence supports one. This activates RF-009A-PUBLIC alongside unresolved historical restoration. It supports UO-01–05/09 and UX-02/05/07: public-source preparation will eventually run behind the researcher's gauge/date request.

## Decision

Prepare `watauga-public-rebuild-v1` from newly acquired, version-bound public geometry, attributes, historical weather and issue-specific forecast weather. Independently authored preparation code produces new configurations and input manifests. Keep every original and historical receipt intact. Existing numerical reference outputs and the old E03 identity cannot be attached to the regenerated fixture.

**Preparation completed on 10 October:** 31 catchments, 31 CFE/31 Noah configurations, 24,366 historical and 1,116 forecast catchment-hour rows. Independent core validation checked 815 retained response hashes and exact decoded-to-provider correspondence for all 25,482 rows. Three serial input jobs contain 291 bound files. The [frozen machine-readable recipe](../fixtures/watauga-public-v1/recipe.json), [component manifest](../fixtures/watauga-public-v1/manifest.json) and [local access guide](../fixtures/watauga-public-v1/README.md) identify the completed development fixture. Source selection and input assembly completed in that preparation phase. The subsequent [v2 physical increment](PUBLIC_WATAUGA_REFERENCE_RESULTS_V2_2026-10-10.md) preserves this v1 record, introduces two explicit source-compatible Noah defaults and supplies new diagnostic references. Release scientific qualification remains open.

The evidence-driven archive follow-up found no new exact historical-file lead. Its checked name/size matches have different declared hashes. This supports regeneration as the active development path while leaving historical recovery open to a concrete new backup or exact-hash candidate. It does not establish that no other backup exists.

## Prepared case and remaining freeze gates

| Part | Working case | Must be bound before data admission |
|---|---|---|
| Requested location | USGS `03479000`, Watauga | Official gauge identity/coordinates and explicit outlet-selection method |
| Public domain | Newly acquired VPU06 hydrofabric; 31-catchment inclusive upstream closure of `wb-1017693` | Public source URL/version metadata and whole-file hashes; official NLDI COMID `19743430` crosswalk, explicit flowpath output, catchment/flowpath/nexus axes and geometry hashes |
| Historical window | `2021-12-01T00:00:00Z` to `2022-01-02T18:00:00Z`, exclusive; 786 provider intervals | Complete real-source coverage, source versions and extraction/clock/unit treatment; no silent imputation |
| Forecast issues | `2022-01-01T23:00:00Z` and `2022-01-02T00:00:00Z`, 18 leads each | Actual source initialization/valid-time attributes and complete issue-specific weather; source presence does not prove historical operational availability |
| Spatial forcing extraction | Polygon overlap weights in metric CRS EPSG:5070 | Exact source grids, cell boundaries, transformed geometry, complete polygon coverage and weight hashes; no renormalization of missing weather |
| Configuration | Independently generated public-source CFE/Noah/routing/realization | All defaults, source columns/units, transformations, template/adaptor revisions and resulting bytes; candidate `mean.slope_1km` remains a separately identified development treatment |
| Runtime | Separately admitted Linux runtime | Actual loaded identities, complete packaging/build provenance and all applicable runtime guards |
| New references | Three v2 diagnostic references generated in the subsequent increment | Separate input/runtime/protocol identity, complete canonical output seals; public access and release qualification remain open |

Independent source review selects official NLDI COMID `19743430`, mapped by the public network to flowpath `wb-1017693`, including that reach's contributing catchment. Its terminal nexus is `nex-1017694`. A gauge URI also appears on adjacent `wb-1017846`; selecting the nexus or gauge attribute alone would add a side branch and give 32 catchments. The selected flowpath is 56.92 m from the official gauge point, compared with 1,105.57 m for that adjacent reach. Treat routed flowpath discharge as a full-reach spatial surrogate for the gauge; this is not an exact interior-gauge routing solution. Preserve the conflicting metadata and selection evidence. Numerical reach/nexus labels do not establish equivalence with historical routing identities. If dates, source version, outlet, axis, parameter choice or extraction method change after the first freeze, issue a new linked recipe revision and disclose the change.

## Preparation work and evidence

1. Verify public source availability and acquire only a bounded regional fabric and required source segments. Reject HTTP-200 HTML responses masquerading as datasets. Preserve failed probes and download sizes.
2. Derive and validate the outlet/closure from public tables. Generate fresh configurations from identified source attributes/templates. Record the CFE drainage, Noah terrain slope and routing reach slope separately.
3. Decode complete AORC history and all 36 issue/lead forecast-weather fields with their actual source attributes. Bound provider labels, issue labels, units, missing values and precipitation conversion. A source provider's generation/ETag/checksum plus hashes of fetched byte ranges must be distinguished from an unavailable whole-object SHA-256.
4. Materialize independently generated input files only under ignored project-local staging. Publish preparation code, source/recipe identities, aggregate validation and access instructions; dataset/template redistribution depends on the recorded artifact-specific terms.
5. Audit content and completeness, then seal the input identity. Report any source-unit, radiation, parameter, decoder or runtime qualification gap explicitly. Passing byte/content checks cannot clear an unresolved scientific gap.

The [public forcing investigation](PUBLIC_FORCING_FEASIBILITY_2026-10-10.md), [domain preparation](PUBLIC_WATAUGA_DOMAIN_2026-10-10.md), and [local recovery decision](LOCAL_RECOVERY_DECISION_2026-10-10.md) record current evidence. The original [first physical experiment](FIRST_PHYSICAL_EXPERIMENT.md), benchmark protocol/matrix and native profile remain their own historical contracts. This new fixture has **zero model invocations in this preparation phase**. It is not placed into E03's existing five-invocation allowance. Before native execution, declare a separate bounded reference/qualification experiment and its independent outputs.

## Current resource and protection limits

Original Reforecast, NextGen, HYDRA and thesis folders remain read-only, including caches and Git metadata; no hydration. Existing private staged copies may be inspected only for comparison or acquisition estimates, never presented as newly acquired public inputs. Public sources and derived data belong under `.local/public-fixture-20261010/`.

Initial public forcing probes and decoder dependencies were limited to 32 MiB; domain acquisition/dependencies to 48 MiB, with the named regional archive and extracted GeoPackage admitted separately at 64/128 MiB per file. Verified metadata identifies 56 required AORC chunks (75,943,446 compressed bytes) and sparse regional ranges from all 36 NWM forecast objects. Whole forecast objects total approximately 5.56 GB and are not bulk downloaded.

The bounded weather materialization step admits at most **768 MiB HTTP payload including earlier probes and decoder dependencies**, 1 GiB raw plus derived weather staging, 16 MiB per response, 2,000 requests, 30 seconds per request and two retries for transient failures only. The adapter's current execution uses a tighter 700 MiB payload cap, leaving margin for prior acquisition. Maintain at least 8 GiB host free space and keep aggregate new-fixture staging within 2 GiB. Preserve generation/ETag identities and hashes of each fetched segment. No paid/cloud execution, global dependency installation, recruitment, submission or scientific simulation is part of this preparation step.

## Manuscript interpretation

A completed public input fixture will support claims about source accessibility, deterministic preparation, provenance and tested content contracts. It will not reproduce the missing historical bytes or inherit historical equivalence, hydrologic skill, convergence, speedup or recovery results. New physical results require their own source-bound references and declared comparisons. Keep acquisition/preparation evidence separate from model runtime and benchmark performance.
