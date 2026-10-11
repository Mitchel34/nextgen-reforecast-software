# Public Watauga forcing preparation — 10 October 2026

The public-data route produced complete weather inputs for the **new** `watauga-public-rebuild-v1` development fixture. It uses the separately resolved public 31-catchment reach domain, a history beginning `2021-12-01T00:00:00Z`, and issues `2022-01-01T23:00:00Z` and `2022-01-02T00:00:00Z`. This is prospective input preparation. It does not restore the original fixture or establish physical equivalence, calibrated performance, hydrologic convergence, operational historical availability or a qualified scientific release.

The independently authored [preparation recipe](../scripts/public_fixture/prepare_forcing.py), [optional dependency pins](../scripts/public_fixture/requirements.txt), [adversarial tests](../tests/test_public_forcing.py) and [public evidence summary](evidence/public-forcing-feasibility-20261010.json) accompany the actual private preparation. Source bytes, geometry, spatial weights and derived weather remain in ignored project-local staging; original research directories were not used or hydrated.

## Public source verification

[NOAA's AORC registry](https://registry.opendata.aws/noaa-nws-aorc/) describes hourly eight-variable AORC v1.1 weather, cloud Zarr access and precipitation accumulated over the hour ending at its label. It requests attribution, prohibits implied NOAA endorsement and requires modified data to be distinguished from original data. Its current 2 April 2026 notice reports a masking defect and ongoing Zarr regeneration. The selected required cells passed fill/finite checks, while the broader source-quality notice remains a release qualification concern. Each acquired response has an observed SHA-256, size and ETag; the current store must not be mistaken for an immutable historical generation.

The [NOAA NWM short-range registry](https://registry.opendata.aws/noaa-nwm-pds/) describes hourly, 18-hour short-range forecasting and a four-week AWS rollover. For these older issues, anonymous access to the [public Google Cloud NWM bucket](https://storage.googleapis.com/storage/v1/b/national-water-model/o?prefix=nwm.20220101%2Fforcing_short_range%2Fnwm.t23z.short_range.forcing.&maxResults=30) confirmed all 36 required CONUS forcing objects. The retained inventory records each object's key, generation, whole size, MD5 and CRC32C declarations. Sparse requests bind that generation and ETag and retain the exact downloaded byte segments with their own SHA-256. Whole NetCDF SHA-256 values remain unknown because the complete files were not downloaded.

The 36 full forecast objects total **5,555,249,651 bytes**. The recipe acquired only the required HDF5 metadata and spatial weather chunks, plus the AORC chunks and exact coordinate vectors. Weather acquisition used **376,585,861 response bytes and 878 requests**; a cross-year coordinate supplement added **91,010 bytes and 132 requests**. The final preparation replay used **zero HTTP requests**. Earlier bounded feasibility and dependency probes fit inside the separate 768 MiB request budget. Observed weather staging was 440 MiB with retained raw responses shared through hard links rather than duplicated payloads.

## Actual decoding and spatial extraction

All catchment values use polygon intersection area in EPSG:5070. Source-cell edges are transformed with quarter-cell densification, and spatial weights retain their own identity. Missing required cells fail preparation; their weights cannot be renormalized onto remaining cells. Source geometry, the separately supplied axis, the grid and the recipe are bound to the preparation identity.

The recipe validates actual AORC units, dimension order, integer packing, Zstd codec, fill/scale/offset, time encoding and each requested source hour. Actual latitude and longitude vectors agree across 2021 and 2022. It uses each year's own packing metadata. Forecast files are validated against their actual initialization and valid-time attributes, coordinate clocks, v2.1 configuration, variable units, temporal attributes, HDF5 dimensions and spherical Lambert conformal projection.

The published NWM coordinate vectors preserve small rounding of nominal kilometre centers: observed maximum residuals were 0.125 m in x and 0.0625 m in y. An initial overly strict arithmetic-coordinate check failed closed. The retained failed replay is followed by the final replay, which hashes the exact published vectors, checks the declared projection and nominal grid within a 0.25 m tolerance, and defines cell edges from adjacent coordinate midpoints. Required Watauga cell centers have 1,000 m local spacing.

| Input | Source clock and units | Provider treatment |
|---|---|---|
| Historical precipitation | AORC accumulated `APCP_surface`, `kg/m^2`, label `t+1h` | Provider row `t`; divide by 3,600 once |
| Other historical variables | AORC source label `t`, declared temperature/humidity/wind/pressure/radiation units | Provider row `t`; decode packing then area weight |
| Forecast precipitation | NWM `RAINRATE`, `mm s^-1`, `time: mean`, valid label `I+kh` | Provider row `I+(k-1)h`; retain the rate. Liquid-water depth `mm/s` is numerically equivalent to `kg/m^2/s` |
| Other forecast variables | NWM valid label `I+kh`; source `time: point` (`SWDOWN` says `time point`) | Provider row `I+(k-1)h`; decode packing then area weight |

Radiation values and source temporal attributes are retained explicitly. These checks do not settle whether the adopted sampling is the correct physical integration for a final released model profile. Archive object generations uploaded later also do not prove causal availability at the original issue time.

Decoded source CSVs use canonical UTC timestamps ending in `Z`. Native provider CSVs use UTC rendered as `%Y-%m-%d %H:%M:%S`, as required by the pinned ngen `CsvPerFeature` parser. The time rendering and one precipitation conversion are recorded transformations.

## Completed evidence and remaining gates

- History contains **24,366** catchment-hours: 31 catchments × 786 hours in `[2021-12-01T00Z, 2022-01-02T18Z)`.
- Each forecast issue contains **558** catchment-hours: 31 × 18; both issues total **1,116**.
- All eight weather values are finite for every required row. There are no missing or duplicate required rows. Precipitation is nonnegative.
- All **25,482** native provider rows were compared numerically with the decoded source transformation; every value agrees exactly with its declared conversion.
- The two final decoded forecast CSVs equal the initial acquisition draft bytes. Historical midpoint geometry arithmetic changed the draft by at most `1.40e-9 Pa` for pressure and smaller absolute differences for other variables; the final preparation has its own identity and does not reuse the draft identity.
- **11 focused tests** pass for source clocks, unit/codec/dimension changes, packed-value decoding, missing-cell refusal, path escapes and sparse response identity/range checks.

Final private component receipt: `.local/public-fixture-20261010/forcing/prepared-v3/PREPARATION.json`, identity `085efd5725eb87c222258c053a3aae5914f25f231f66e9bb31d2e8959afea070`. The exact executed final recipe is retained separately; an earlier acquisition draft and the failed intermediate replay remain preserved. The final decoded content/source audit, native assembly, runtime/configuration admission and prospective independent physical references remain distinct acceptance steps. No model was executed by this preparation task.
