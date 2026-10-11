# Campaign planning contract — schemas 1.0 and 1.1

Implemented 10 October 2026 for RF-002/RF-006, UO-01/UO-05 and UX-02/UX-07. This is an offline planning contract. It defines expected keys, clocks and counts; it does not acquire weather, verify scientific inputs, execute NextGen or export verified model results.

## Compatibility and normalization

The [schema 1.0 document](../schemas/campaign.schema.json), original example and default generated ledger remain unchanged. Schema 1.0 still requires an explicit `issue_times_utc` list, `hourly18h` and `horizon_hours: 18`, with all leads 1–18. A regression test pins the original example's specification and plan identities. New fields and cadence shorthand are rejected in 1.0.

[Schema 1.1](../schemas/campaign-1.1.schema.json) adds an explicit retained lead interval and an optional cadence shorthand. There is no automatic migration to 1.1. A caller selects `schema_version: "1.1"` and supplies all fields below; the remaining campaign fields, asset rules and resource limits retain their existing meanings. The [retained-lead example](../examples/watauga/campaign-retained.json) is a planning example with incomplete assets, separate from the original fixed benchmark definition.

`normalize_campaign(spec)` returns a detached, validated campaign dictionary without reading asset bytes. `load_campaign(path)` applies the same normalization after a bounded resident JSON read. For schema 1.1, normalization replaces cadence shorthand with its explicit issue list. It does not change the origin, extend history, remove issues, repair unsupported leads or insert model defaults.

The canonical normalized dictionary is the input to `specification_sha256`. Equivalent shorthand and explicit lists therefore have identical specification hashes and plans. Changing the retained interval changes the specification hash and plan identity; changing from schema 1.0 to 1.1 also changes those identities even when all 18 leads remain selected. This specification hash is not a complete scientific lock. The domain input identity still identifies the existing profile/origin/assets subset, not the output selection, and is not evidence of physical-state correctness.

## Execution and retained leads

Schema 1.1 requires:

```json
{
  "schema_version": "1.1",
  "profile": "hourly18h",
  "horizon_hours": 18,
  "retained_leads": {
    "min_lead_hours": 1,
    "max_lead_hours": 6,
    "projection": "export"
  }
}
```

This excerpt omits the other required campaign fields. Both lead limits must be integers, with `1 <= min_lead_hours <= max_lead_hours <= 18`. Booleans, fractional numbers, reversed intervals, zero and lead 19 fail validation. A contiguous interval is supported; arbitrary sparse lead lists are not. Selecting 6–6 preserves the actual lead-six key and target time rather than renumbering it as lead one.

`projection: "export"` is the only accepted projection policy. It binds the intended downstream output selection in the normalized campaign. Future execution and commit verification must preserve evidence for all 18 generated steps before exporting the selected subset. The current planner produces expectation ledgers only; an actual commit verifier and scientific export remain separate work packages. Fewer retained rows imply no measured or assumed CPU saving.

For every issue `I` the following requirements stay fixed, including when only leads 1–6 are retained:

- The child executes 18 hourly steps.
- Forecast provider rows label interval starts `I` through `I + 17 h`.
- Forecast targets are `I + 1 h` through `I + 18 h`.
- The declared historical provider interval begins at the unchanged original origin and covers through the final issue plus 18 hours.
- An issue must follow the origin by at least one hour. The adopted antecedent duration is reported; the planner does not establish spin-up convergence.

## Issue schedules and date meaning

Schema 1.1 requires exactly one of `issue_times_utc` and `issue_schedule`. Explicit lists support regular or irregular events and must be strictly increasing, unique, canonical UTC hours. The new cadence shorthand is:

```json
{
  "issue_schedule": {
    "start_time_utc": "2022-01-01T16:00:00Z",
    "stop_time_utc_exclusive": "2022-01-02T00:00:00Z",
    "cadence_hours": 3
  }
}
```

This expands to the three issues 16:00, 19:00 and 22:00 UTC on 1 January. Start is included; stop is excluded. The stop need not fall on a cadence step. Cadence is an integer between 1 and 100,000 hours; it sets issue spacing while the model timestep remains hourly. The schedule never implies that parent history may skip hours between issues.

Every timestamp must use `YYYY-MM-DDTHH:00:00Z` and be a valid calendar hour. Offsets, local times, minute/second fractions and invalid calendar dates fail. The stop must follow the start. Expansion is counted before allocation and limited to 100,000 issues; both the submitted and normalized campaign are bounded by 4 MiB. The existing historical interval limit of 100,000 hours and full final 18-hour coverage also apply. No issues are truncated to satisfy a bound.

These endpoints mean **issue times**, not forecast valid times. A browser may present calendar dates, but its request adapter must declare their translation to this UTC interval and show the resulting valid-time range. This engine contract does not resolve watershed coverage, source availability or release defaults on behalf of that adapter.

## APIs and counts

| Interface | Meaning |
|---|---|
| `normalize_campaign(spec)` | Validate and detach the campaign; expand 1.1 shorthand to explicit issues without asset reads |
| `load_campaign(path)` | Bounded resident JSON read, duplicate-key/nonfinite rejection, followed by normalization |
| `plan_campaign(spec, base_dir, check_assets=True)` | Normalize, calculate a deterministic plan and optionally inspect resident asset identities; always `execution_ready: false` in this increment |
| `iter_ledger(spec)` | Compatibility API: all expected generated keys, 18 per issue/location |
| `iter_expected_rows(spec, kind="generated")` | Explicit generated or retained expected keys; only `generated` and `retained` are accepted |

Both ledgers stream rows in domain, issue, location, lead order. Keys preserve domain/location/reach, issue time, actual lead and valid time. A ledger caller must bound how much it exports. A key ledger contains no model values or proof of completion.

For `N` issues, `L` output locations across the campaign, and `D` independent domains:

| Plan field | Definition |
|---|---|
| `totals.branch_count` | `N * D` |
| `totals.expected_forecast_rows` | `N * L * 18`, preserving its original generated-row meaning |
| `totals.generated_forecast_rows` (1.1) | `N * L * 18` |
| `totals.retained_forecast_rows` (1.1) | `N * L * (max_lead_hours - min_lead_hours + 1)` |
| `totals.total_parent_history_hours` | Declared historical interval hours times `D`; nested output locations do not duplicate a domain's history |
| `time_contract.antecedent_history_hours_at_first_issue` (1.1) | First issue minus unchanged origin, in hours |

Schema 1.1 plans also expose the retained selection, `time_contract.execution_horizon_hours: 18` and `required_source_lead_hours: {"min": 1, "max": 18}`. Schema 1.0 plan shape and IDs are preserved. The two-issue, one-location retained example plans 36 generated rows and 12 retained rows for leads 1–6, with the same 786-hour declared history interval.

## Validation evidence and remaining dependencies

The focused [campaign tests](../tests/test_campaign.py) exercise fixed 1.0 identities; 1–18, 1–6 and 6–6 selection; multiple domains and nested outputs; unchanged source/history requirements; hourly, three-hour, daily and irregular schedules; canonical equivalence; detached normalization; malformed clocks; conflicting declarations; expansion/read bounds; leap-day/year/calendar edges; and existing asset/path/CPU failures. These are software-contract tests over local planning fixtures.

YAML, selected UTC-hour-of-day shorthand, arbitrary retained lead lists, variable physical horizons and continuous-simulation mode remain unsupported. JSON is the working format. Scientific forcing validation, a complete provenance lock, runtime qualification, commit verification, physical exports and automatic browser input preparation require their own evidence. Neither this example nor a successful plan admits the original Watauga physical experiment or qualifies a release profile; the [first-experiment contract](FIRST_PHYSICAL_EXPERIMENT.md) still applies.
