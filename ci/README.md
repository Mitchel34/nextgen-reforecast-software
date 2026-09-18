# Offline test workflow template

`tests.yml` defines the offline package suite on Linux/Python 3.11–3.14 with pinned GitHub action revisions and read-only repository permissions. It is inactive in this directory.

The initial publication attempt was rejected because the publishing credential lacks GitHub `workflow` scope. The code and manuscript are published independently; local validation is recorded in [the validation receipt](../docs/VALIDATION.json). No remote CI pass is claimed.

Once a credential authorized to update workflows is available, move `ci/tests.yml` to `.github/workflows/tests.yml`, commit and push, and verify all four matrix jobs. Retain the run URL and exact tested commit in the validation receipt. A configured workflow alone does not satisfy this check.
