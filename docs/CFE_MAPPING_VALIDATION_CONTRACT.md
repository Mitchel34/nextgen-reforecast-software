# CFE drainage mapping audit — 10 October 2026

RF-005A provides a bounded, read-only check of the CFE bottom-drainage mapping in [configuration.py](../src/ngen_reforecast/configuration.py), supported by [adversarial tests](../tests/test_configuration.py). Its scope is one parameter's declared source and actual configuration bytes. A successful audit is not complete CFE configuration validation, scientific default approval, native-library attestation or a coupled forecast experiment.

This implements part of the follow-up identified in [CFE_PARAMETER_FINDING.md](CFE_PARAMETER_FINDING.md). It preserves the distinction between reproducing the inherited baseline and evaluating a separate candidate. It does not rewrite or repair configuration files, rescale outputs, reuse an incompatible antecedent trajectory or change the original research folders.

## Callable and CLI interfaces

```python
manifest = load_configuration_manifest(path)
report = validate_configuration(
    manifest, base_dir,
    expected_catchment_ids=["cat-1", "cat-2"],
)
```

The caller supplies the expected catchment axis from the separately reviewed domain; the input manifest cannot establish its own expected coverage. There must be exactly one attribute row and exactly one bound configuration for every expected catchment. Duplicate, missing and extra catchments fail.

```text
ngen-reforecast validate-cfe configuration.json --catchment cat-1 --catchment cat-2
```

The CLI reads assets relative to the manifest directory. Exit 0 means the narrow content checks passed; `execution_ready` remains false. Exit 2 reports failed content checks. Exit 1 reports a malformed contract or a CLI-level error. `--output` uses the existing atomic, no-overwrite publication path for a report. This operator-facing command is an internal development interface, not the intended ordinary researcher's browser workflow.

## Bound evidence and supported variants

The strict `cfe-mapping-manifest/0.1` object contains `schema_version`, `evidence_class`, `variant`, `catchment_ids`, `attributes`, `source`, `mapping`, `generator`, `cfe_library` and `configurations`.

Each attribute/configuration/library asset binds a relative POSIX path, SHA-256 digest and positive byte length. Asset paths must be distinct. The attribute CSV header is exactly `catchment_id,mean.slope,mean.slope_1km`; both source columns contain finite ASCII decimal values. `source` separately declares a hydrofabric digest plus the units and meanings of both fields. `generator` declares a full lowercase Git revision or an explicit `null` when unknown, plus its configuration family. These declarations are bound metadata, not proof that that generator produced the files or that a hydrofabric field has the declared derivation. An unknown generator does not prevent a narrow byte/mapping audit, but it remains a qualification gap and must never be replaced with invented provenance.

| Variant | Required source field | Content interpretation |
|---|---|---|
| `inherited_diagnostic` | `mean.slope` | Reproduce the declared inherited mapping exactly; retain known mapping and out-of-range warnings |
| `candidate_1km` | `mean.slope_1km` | Require a declared dimensionless bottom-drainage modifier, exact matching generated values and the selected 0–1 range |

Both variants require mapping purpose `cfe_bottom_drainage`, canonical target `soil_params.slop`, identity transformation and target units `1`. No angle conversion, division, clipping or substitution with Noah terrain slope or routing reach slope is admitted. A candidate's source metadata must explicitly declare units `1` and meaning `bottom_drainage_modifier`; passing that declaration check does not independently verify either statement.

The selected candidate range follows the parameter description in the [pinned CFE header](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/include/cfe.h#L70-L80). It is a constraint for this audit's candidate profile, not validation of all CFE versions or all calibrated configurations. Inherited values outside that range are retained as diagnostic evidence with warnings; they are never silently clipped or declared suitable for release.

## Assignment parsing and numeric checks

Each configuration must contain exactly one assignment to `soil_params.slop` or its `soil_params.slope` alias. Both aliases, or the same alias twice, fail even when their values agree. The [pinned CFE parser](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/src/bmi_cfe.c#L521-L586) recognizes those literal keys; it does not trim the key before comparison. The audit therefore rejects key whitespace that could make its interpretation differ from that parser.

The accepted assignment format is a signed ASCII decimal or scientific-notation number immediately followed by `[1]` or `[m/m]`. Source values and generated assignments are compared exactly with decimal arithmetic, without a matching tolerance. Missing units, different units, trailing material, hexadecimal notation, underscores, Unicode digits and nonfinite numbers fail. Numeric conversion must also remain finite as a C double, and a nonzero decimal cannot underflow to zero. The 0 and 1 candidate boundaries are accepted.

Configuration text is restricted to ASCII with LF or CRLF lines. Other control separators and NULs fail; drainage assignments cannot be created by Python-specific line splitting. A line starting with `#` is ignored. This deliberately narrow parser does not claim to interpret every possible CFE configuration syntax or validate unrelated assignments. A file containing only the valid drainage assignment can pass this audit while remaining an incomplete, unrunnable model configuration.

## Reports, bounds and remaining qualifications

`cfe-mapping-validation/0.1` reports contain observed asset hashes and byte lengths, source/configuration decimal pairs, blockers, warnings and separate hashes of the manifest, source metadata, mapping and generator metadata. `validation_identity_sha256` binds the entire report, including the external expected axis and qualification limits. Changing the source declaration, generator revision, library bytes or mapping changes that identity. Hash consistency is not source authenticity or a signature.

Every report preserves:

- `source_metadata_status="declared_unverified"`;
- `generator_status="unknown"` for a null revision, otherwise `"declared_unverified"`;
- `loaded_library_attested=false`;
- `complete_configuration_validated=false`;
- `execution_ready=false`.

A declared CFE library is opened only as bounded resident bytes for hashing; no loader, subprocess, native symbol or model initializer is called. Even a correctly hashed non-ELF synthetic file can satisfy this byte-binding portion of a synthetic test. Such a result does not establish that a file is an ELF library, that it loads on Linux ARM64, that the model uses it, that its source matches the pinned revision, or that its dependencies resolve. Those are separate runtime checks and remain qualification blockers here.

The manifest is limited to 1 MiB, the attribute table to 4 MiB and 1,024 rows, the library to 32 MiB, and each of at most 1,024 configuration files to 256 KiB. Configuration assets collectively may declare at most 16 MiB. Reads use the smaller of the declared size and the applicable cap, so understating a file's size cannot bypass the aggregate bound. Shared safe readers refuse symlinks, placeholders, nonregular inputs and oversized files before their payload is read, and detect changes during reading. Unavailable or mismatched assets yield blocked content reports.

The source-field units and derivation, generator execution, actual loaded library and complete configuration remain unqualified. A changed scientific candidate requires independently evolved antecedent history from the same original origin and its separately bounded coupled comparison. Agreement between a serial reference and shared-history execution would not, by itself, certify the drainage parameterization. The [first physical experiment](FIRST_PHYSICAL_EXPERIMENT.md) retains the original diagnostic baseline, while release-profile qualification remains separate.

The tests establish these parsing, identity, axis and evidence boundaries using synthetic bytes only. They do not establish the proposed candidate's hydrologic accuracy or reproduce the previously reported isolated-CFE sensitivity experiment.
