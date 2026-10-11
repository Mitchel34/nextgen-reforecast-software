# User guide: planning and pinned diagnostic execution

The current package plans campaigns, binds offline input identities and inspects an explicitly pinned historical runtime. The pinned Watauga v2 diagnostic execution path is documented below; other campaigns and physical recovery are not admitted. These commands serve developers/operators; the intended researcher experience uses the browser and automatic preparation. This distinction is visible in command output and exit codes.

## Install

Python 3.11 or later on Linux or macOS is required. Campaign loading and asset inspection require POSIX no-follow directory-descriptor APIs; these commands are not supported on Windows in this increment. Successful Python installation alone does not qualify a platform. From this repository, create an isolated environment and install the package:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
ngen-reforecast --version
```

There are no third-party Python runtime dependencies. The Python build backend is a build-time dependency. Local native runtime support and model dependencies are separate from successful Python installation. No container image or model input is downloaded during package installation or by the commands below.

## Create and inspect a campaign

```sh
ngen-reforecast init my-campaign
ngen-reforecast plan my-campaign/campaign.json
ngen-reforecast ledger my-campaign/campaign.json --output my-campaign/expected.csv
ngen-reforecast report my-campaign/campaign.json --output my-campaign/plan.md
```

`init` creates a new directory with a Watauga planning template and instructions. It includes no scientific data. Existing directories/files are not overwritten. The template's missing files and input identities deliberately produce blockers; fill the relative paths, SHA-256 identities and byte sizes from your exact retained inputs. Do not substitute a differently initialized history merely to make a check pass.

`plan` reads a strict JSON campaign specification, checks UTC schedule and resource/profile constraints, calculates expected counts and checks bounded resident assets. A blocker is an actionable missing or inconsistent requirement. Even matching inputs cannot establish numerical runtime qualification or physical forecast skill; the current foundation always reports `execution_ready: false`.

`ledger` writes only the expected keys: domain, location, reach, issue time, lead and valid time. It contains no discharge values and does not assert any forecast was generated. Overlapping valid times from distinct issue/lead combinations remain distinct rows. The default output cap is one million rows; choose a bounded `--max-rows` up to ten million when needed. The ledger is streamed to a temporary file and published only when its row count matches the plan.

`report` renders the same planning facts in Markdown, including blockers and evidence limits. It is a campaign planning report, distinct from the accompanying research manuscript.

See [the schema](../schemas/campaign.schema.json) and [Watauga example](../examples/watauga/README.md) for the exact input fields and conventions. All times are explicit UTC. The initial profile is hourly with eighteen forecast leads. Geometry, realization, parameters, forcing and routing inputs retain distinct asset roles. File paths must stay within the campaign directory; missing, changed, dataless or symlinked assets cannot silently qualify.

## Select retained leads and schedules

Schema 1.0 remains unchanged. [Schema 1.1](../schemas/campaign-1.1.schema.json) and the [retained-lead example](../examples/watauga/campaign-retained.json) add a contiguous lead interval and UTC cadence shorthand with an exclusive stop. The [campaign contract](CAMPAIGN_CONTRACT.md) explains normalization and compatibility. JSON is the supported format; YAML is deferred.

```sh
ngen-reforecast plan examples/watauga/campaign-retained.json
ngen-reforecast ledger examples/watauga/campaign-retained.json --kind retained --output retained-keys.csv
```

Selecting leads 1–6 retains six expected keys per issue/location while all 18 model steps and source leads remain required. `--kind generated` is the default and includes all 18. These are expected key ledgers, not an export of simulated discharge. Shorter retention does not imply lower model compute cost.

## Bind and recheck a planning snapshot

Once an internal campaign has every required role and correct resident hash/size:

```sh
ngen-reforecast lock my-campaign/campaign.json --output planning-lock.json
ngen-reforecast verify-lock planning-lock.json --asset-root my-campaign
```

`lock` refuses incomplete/mismatched inputs and existing output paths. `verify-lock` checks both snapshot consistency and current input bytes. The [provenance contract](PROVENANCE_CONTRACT.md) keeps unvalidated metadata and unknown scientific information explicit. A successful identity check always retains `execution_ready: false`. It is not a prepared physical execution lock.

## Inspect runtime assets

```sh
ngen-reforecast doctor profiles/nextgen-arm64-v3.json
ngen-reforecast doctor profiles/nextgen-arm64-v3.json --asset-root /path/to/your/runtime-assets
```

The profile records the historical Linux ARM64 V3 build. `doctor` checks its identity and any explicitly supplied assets, reports unsupported environments and explains missing qualifications. It does not run binaries, start Docker, fetch source, build components or read cloud credentials. The historical binary and image identities do not themselves qualify a new public build. See [runtime qualification](RUNTIME_QUALIFICATION.md) and [the native build recipe](../native/BUILD_RECIPE.md).

## Output and exit status

| Status | Meaning |
|---|---|
| `0` | Requested non-executing action completed, such as writing a template or expected ledger |
| `1` | Invalid input, I/O problem, output collision or bounded-output failure |
| `2` | Plan/runtime has blockers, planning-lock input bytes fail recheck, or physical execution/recovery is not implemented |

Blocked `plan`, `report` and `doctor` commands still return useful reports. The status is intentional and useful in automation. Use `--output NEW_PATH` to save a plan/report/runtime inspection without overwriting prior evidence. Its parent directory must exist. Errors are emitted as JSON on stderr. Expected output counts are not observed archive counts.

## Current limits and next steps

The fixed Watauga v2 `run`, archive verification and diagnostic export are implemented below; `resume` and general physical recovery remain unavailable. The local browser interaction prototype prepares a researcher request; it is not a hosted execution service. No cloud runner, ML model, universal routing support or portable full-land checkpoint is included. Execution requires its exact separately admitted bundle; [the implementation plan](../IMPLEMENTATION_PLAN.md) tracks these dependencies.

## Validate prepared scientific contents (operator interface)

`0.1.0a3` adds bounded offline content checks. These are preparation-service building blocks; ordinary researchers will not be asked to assemble manifests or enumerate catchments. Supply expected clocks and the complete domain axis independently of the input's own declarations.

```sh
ngen-reforecast validate-forcing examples/validation/history.manifest.json \
  --catchment cat-1 --catchment cat-2 \
  --history-start 2022-01-01T00:00:00Z --history-stop 2022-01-01T03:00:00Z
ngen-reforecast validate-forcing examples/validation/forecast.manifest.json \
  --catchment cat-1 --catchment cat-2 --issue-time 2022-01-01T00:00:00Z
ngen-reforecast validate-cfe path/to/cfe-mapping.manifest.json \
  --catchment cat-1 --catchment cat-2 --output new-mapping-report.json
```

The checked-in weather examples are synthetic contract fixtures. The first two commands do not inspect real archive coverage or generate model inputs. See the [forcing contract](FORCING_VALIDATION_CONTRACT.md) and [CFE mapping contract](CFE_MAPPING_VALIDATION_CONTRACT.md) for schemas, bounds and qualification limits. The CFE command checks only drainage mapping and bound bytes, not all required configuration keys.

Exit 0 means tested contents conform. Exit 2 means content blockers remain, including when `--gap-policy exclude_issue` explicitly records an incomplete forecast exclusion. Exit 1 indicates a malformed/unsafe/unreadable contract or an output publication error. Outputs never overwrite an existing file. `content_valid=true` always coexists with `execution_ready=false`; source authenticity, field derivation, actual loaded libraries and physical suitability require separate evidence. The validators do not themselves admit execution; the separate pinned `prepare`/`run` path is described below.

## Execute the pinned Watauga v2 diagnostic

Version0.1.0a5 adds `prepare`, `run`, `status`, `verify` and `export` for the exact operator profile in [the execution contract](PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md). Recovery remains unavailable. The operator must supply the already admitted fixture, runtime transfer and sealed reference arrays; package installation does not acquire them or close release rights.

```sh
ngen-reforecast prepare examples/watauga/campaign-execution-v2.json --bundle /path/to/bundle/BUNDLE.json --output execution-lock.json
ngen-reforecast run execution-lock.json --asset-root /path/to/bundle --execution-root /path/to/new-attempt --archive /path/to/new-archive --docker-host unix:///path/to/dedicated/docker.sock
ngen-reforecast status /path/to/new-archive --lock execution-lock.json
ngen-reforecast verify /path/to/new-archive --lock execution-lock.json
ngen-reforecast export /path/to/new-archive --lock execution-lock.json --output /path/to/new-export
```

The [example bundle declaration](../examples/watauga/execution-bundle.json) illustrates the required relative layout; it contains no inputs. `prepare` verifies every source file and binds the installed implementation, unchanged scientific inputs, fresh run/protocol/admission, exact reference set and warning policy. A planning example with different dates/resources is not runnable. Existing `plan` and `lock` remain offline planning commands with their original evidence meaning.

`run` uses an explicitly supplied local Docker socket and an already available immutable Linux ARM64 image. No image pull/build, worker start, host mount or network access occurs. An exclusive persistent claim prevents duplicate launches of the same lock. Occupied archives reuse only a fully verified identical result. Failure preserves reservations and available evidence, returns nonzero, and does not automatically retry. A fresh complete campaign is the atomic commit unit; per-issue recovery is still open.

The archive contains raw output, stage/normalization receipts, complete audited arrays, comparison evidence, `generated.csv` (all36issue/lead rows) and `retained.csv` (12rows for the example's leads1–6), plus a sealed manifest. `CURRENT.json` appears only after the complete result is verified and durably published. `verify` and `export` reject any changed byte. Equal serialized arrays establish this narrow diagnostic replay, without demonstrating scientific release qualification or a hosted researcher experience.
