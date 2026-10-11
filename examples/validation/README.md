# Synthetic forcing validation examples

These independently authored weather values demonstrate RF-004 content checks. They are **not Watauga inputs, observed weather, a physical experiment or a qualified model fixture**. Source-object, grid and decoder fingerprints are explicitly synthetic declarations, not upstream archive identities.

`history.manifest.json` binds three hourly provider rows for each of `cat-1` and `cat-2`, starting 2022-01-01 00:00 UTC. Each raw APCP accumulation is 3,600 kg m-2 solely to make the one-time division by 3,600 easy to inspect; these deliberately unrealistic amounts are not a meteorological plausibility test. The forecast example binds 18 leads for those two synthetic catchments at the same issue, with a RAINRATE of 3.6 kg m-2 s-1 preserved unchanged.

From the repository root, with the package installed:

```python
from pathlib import Path
from ngen_reforecast.forcing import (
    load_forcing_manifest, validate_history, validate_forecast_issue,
)

base = Path("examples/validation")
history = validate_history(
    load_forcing_manifest(base / "history.manifest.json"), base,
    expected_catchment_ids=["cat-1", "cat-2"],
    start_time_utc="2022-01-01T00:00:00Z",
    stop_time_utc_exclusive="2022-01-01T03:00:00Z",
)
forecast = validate_forecast_issue(
    load_forcing_manifest(base / "forecast.manifest.json"), base,
    expected_catchment_ids=["cat-1", "cat-2"],
    issue_time_utc="2022-01-01T00:00:00Z",
)
assert history["content_valid"] and forecast["content_valid"]
assert not history["execution_ready"] and not forecast["execution_ready"]
```

These samples deliberately use a separate synthetic origin and axis. They cannot replace the original Watauga recipe or its input hashes. The [full contract](../../docs/FORCING_VALIDATION_CONTRACT.md) describes tested rules and unresolved scientific qualifications.
