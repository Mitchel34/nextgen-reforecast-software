# Decoded forcing validation contract — 10 October 2026

RF-004 now provides bounded local CSV content validation for UO-05/09 and UX-02/05/07. The implementation is [forcing.py](../src/ngen_reforecast/forcing.py), with independently authored [adversarial tests](../tests/test_forcing.py) and [synthetic examples](../examples/validation/README.md). These are adapter-development artifacts. They do not restore Watauga's original inputs or qualify a real archive, decoder, spatial extraction, scientific default or native runtime.

## API and expected contract

```python
manifest = load_forcing_manifest(path)
history = validate_history(
    manifest, base_dir,
    expected_catchment_ids=["cat-1", "cat-2"],
    start_time_utc="2022-01-01T00:00:00Z",
    stop_time_utc_exclusive="2022-01-01T03:00:00Z",
)
forecast = validate_forecast_issue(
    manifest, base_dir,
    expected_catchment_ids=["cat-1", "cat-2"],
    issue_time_utc="2022-01-01T00:00:00Z",
)
decision = evaluate_gap_policy(forecast, policy="fail")
```

The history and forecast calls use their respective manifests. The caller supplies the expected catchment axis and clocks independently from the manifest being tested, using the admitted domain and campaign. A self-consistent but shortened, shifted or smaller input cannot establish its own expected coverage. The caller must also bind this expectation to its preparation identity; accepting an arbitrary axis from an untrusted manifest would defeat that safeguard.

`validate_forecast_issue` always expects all 18 generated steps. Retaining leads 1–6 does not reduce required forcing coverage. Forecast provider row `I+(k−1)h` belongs to issue `I`, lead `k`, with source-valid/target label `I+kh`. History requires every catchment-hour in `[start, stop)`. Values are indexed by catchment/provider-hour rather than accepted from filenames or a plausible row count. Row order may vary; duplicate keys remain invalid.

## Manifest and CSV interpretation

The strict `forcing-manifest/0.1` and `forcing-manifest/0.2` manifests contain exactly:

- `schema_version`, `evidence_class` (`synthetic` or `source_declared`) and `role` (`history` or `forecast`);
- `payload`: relative POSIX `path`, decoded-CSV `sha256` and `size_bytes`;
- `catchment_ids`, `start_time_utc` and `stop_time_utc_exclusive`;
- exact `units`, a separate `source` metadata object and the fixed `transformation` declaration.

`source` binds `kind`, `product`, `issue_time_utc`, `objects`, `decoder_sha256` and `grid_sha256`. Its object declarations bind an opaque `object_key`, `generation`, positive `size_bytes` and `sha256`. A history source must declare `historical_analysis` with no issue. A forecast must declare `issue_forecast` with exactly the requested issue. Object keys/generations must be unique. Source objects are not downloaded or reread here. Their identifiers and fingerprints remain declarations; this layer neither parses archive-specific keys nor authenticates the declared issue against raw object attributes. A future source adapter must provide that evidence.

Version `0.2` adds an exact `segments` field to every source object. A completely fetched object uses its whole-object `sha256` and an empty segment list. A sparsely fetched archive object uses `sha256=null` and a nonempty list of `{start_byte, size_bytes, sha256}` identities for actually fetched bytes. Segments must be sorted, nonoverlapping and inside the declared whole-object size; each is at most 16 MiB and all objects together contain at most 4,096 segments. A segment hash must never be promoted to an unobserved whole-object hash. Provider ETags, generations, MD5 and CRC records belong in the acquisition receipt; none is silently reinterpreted as SHA-256. The validator checks the shape of these declarations and the decoded CSV, retaining every source/physical qualification blocker. It does not independently authenticate or reread segments. Version `0.1` still requires a whole-object SHA-256 and refuses the new field or a null hash.

The CSV header begins, in this exact order:

```text
catchment_id,provider_time_utc,precip_source_time_utc,other_source_time_utc,issue_time_utc,lead_hour
```

It then contains the eight weather variables below. Historical rows leave `issue_time_utc` and `lead_hour` empty. Forecast rows contain the exact canonical UTC issue and decimal leads `1` through `18`. All timestamps are canonical UTC integer hours (`YYYY-MM-DDTHH:00:00Z`). Headers, row widths and required variables are exact; duplicate columns are rejected.

| Output variable | Historical source column and unit | Forecast source column and unit |
|---|---|---|
| `precip_rate` | `APCP`, `kg m-2` | `RAINRATE`, `kg m-2 s-1` |
| `TMP_2maboveground` | same name, `K` | `T2D`, `K` |
| `SPFH_2maboveground` | same name, `kg kg-1` | `Q2D`, `kg kg-1` |
| `UGRD_10maboveground` | same name, `m s-1` | `U2D`, `m s-1` |
| `VGRD_10maboveground` | same name, `m s-1` | `V2D`, `m s-1` |
| `PRES_surface` | same name, `Pa` | `PSFC`, `Pa` |
| `DSWRF_surface` | same name, `W m-2` | `SWDOWN`, `W m-2` |
| `DLWRF_surface` | same name, `W m-2` | `LWDOWN`, `W m-2` |

These exact unit spellings define the adapter interface. They are not a requirement that upstream files use those literal strings; a separately qualified decoder must establish any equivalence. Every weather value must use ASCII decimal or scientific notation without whitespace or underscores and remain finite in its provider representation. Nonzero values cannot silently underflow to zero either when parsed or during precipitation conversion; precipitation negativity is checked before float conversion. This first validator does not apply broader climatological or physical plausibility bounds.

The interpretation follows the preserved [data/configuration audit](../reports/reforecast_software_feasibility_20260918T045854Z/DATA_AND_CONFIGURATION.md#time-and-forcing-contract): historical provider row `t` takes raw accumulated APCP labelled `t+1h`, divides once by 3,600, and uses other fields labelled `t`. Forecast RAINRATE is already a rate and is not divided again; forecast source labels are valid-hour ends. The fixed transformation objects exported as `HISTORY_TRANSFORMATION` and `FORECAST_TRANSFORMATION` bind these distinct rules. Any differing divisor, variable, unit or clock treatment fails. A prepared provider CSV containing `precip_rate` cannot be submitted unchanged as a raw APCP CSV; however, this validator cannot detect a dishonest or incorrect relabelling of upstream numeric values. Independent raw-source and decoder checks remain necessary.

Shortwave remains an explicitly unqualified interpretation. The history convention is `unresolved_same_label`; the forecast convention is `declared_source_interval_unqualified`. Neither a successful CSV check nor a declared source fingerprint resolves radiation timing or establishes a complete model-release history.

## Result, provenance and gap decisions

`forcing-validation/0.1` reports distinguish:

- `content_valid`: all tested manifest/CSV/expected-contract agreements passed;
- `blockers`: failed content checks, aggregated by code with counts and at most five examples each;
- `qualification_blockers`: unverified source truth, source-version/grid/decoder qualification, operational availability and shortwave interpretation, plus synthetic-only evidence when applicable;
- `source_metadata_status="declared_unverified"`, `source_truth_verified=false`, `operational_availability_verified=false`, `physical_qualification=false` and `execution_ready=false`.

The report carries separate hashes for the canonical manifest, observed decoded payload, source metadata, declared transformation and independently supplied expected contract. A sorted normalized-provider-content hash is returned only when every content check passes. This normalizes numeric parsing, variable names and the one supported precipitation treatment; it does not write model inputs. `validation_identity_sha256` binds the complete report, including all qualification limits and expected clocks/axis. Hashes provide content consistency, not authenticity or signatures. A change to source generation changes the validation identity even when weather bytes are unchanged.

The default gap policy is `fail`. `exclude_issue` is allowed only when a forecast's sole content failure is absent required rows; it excludes the entire issue, records its time and generated-row population, and requires the campaign layer to recalculate the retained population. History cannot be excluded. Duplicates, wrong units, shifted clocks, invalid values, mismatched identities and unsafe/unreadable files cannot be hidden by this policy. `approved_imputation` and all other policies are unsupported. No missing value is substituted, no origin is shortened, and no historical interval is skipped.

`evaluate_gap_policy` checks the report digest for accidental changes; it cannot authenticate a report supplied by someone who can recompute its hash. Preparation must obtain a fresh validation report from the bound current bytes. `accept_content` and `exclude_issue` do not clear qualification blockers or admit execution.

## Bounds and evidence

Each manifest is at most 1 MiB; each decoded CSV is at most 32 MiB, with at most 100,000 data rows. Catchment axes contain 1–1,024 unique identifiers, history at most 100,000 hours, and the expected catchment-hour product itself at most 100,000 rows. Source-object declarations are capped at 4,096. These limits describe one validation payload, not production-scale acquisition or an arbitrary domain guarantee.

The shared resident reader refuses symlinks in any path component, nonregular files, dataless placeholders and files beyond the bound before reading their payload; it detects size/time changes during the bounded read. There is no acquisition, cache write, model import or hydration. Malformed contracts, unsafe reads and exceeded bounds raise `CampaignError`/`ForcingError`. Content disagreements produce blocked reports. Callers must preserve that distinction and must not translate an exception into an accepted exclusion.

The tests exercise correct single conversion and unchanged forecast rates, valid hashes over scientifically wrong content, independent expected coverage, exact source/provider clocks, issue/lead and source roles, wrong units/treatments, missing/duplicate/extra rows, NaN/Inf, gap-policy limits, separate provenance identities, and resident-reader/bounds failures. Test writes are restricted to repository-local `.local/tmp`. Passing these tests supports the bounded software contract only. Real Watauga qualification and the [first physical experiment](FIRST_PHYSICAL_EXPERIMENT.md) remain separate.
