# User guide: planning foundation

The current package plans campaigns and inspects an explicitly pinned historical runtime. It does not execute NextGen, generate forecasts or resume a physical model. This distinction is visible in command output and exit codes.

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
| `2` | Plan/runtime has blockers, or physical execution/recovery is not implemented |

Blocked `plan`, `report` and `doctor` commands still return useful reports. The status is intentional and useful in automation. Use `--output NEW_PATH` to save a plan/report/runtime inspection without overwriting prior evidence. Its parent directory must exist. Errors are emitted as JSON on stderr. Expected output counts are not observed archive counts.

## Current limits and next steps

`run` and `resume` return an explicit unavailable status. Archive verification, scientific export and physical recovery will be implemented against qualified outputs in later milestones. No cloud runner, ML model, GUI, universal routing support or portable full-land checkpoint is included. Restore and qualify the exact complete real fixture before attempting model execution; [the implementation plan](../IMPLEMENTATION_PLAN.md) tracks these dependencies.
