# Offline test workflow

The active workflow is [`.github/workflows/tests.yml`](../.github/workflows/tests.yml). It installs the package and runs the offline suite on Linux/Python 3.11–3.14, using pinned action revisions and read-only repository permissions.

Activation was blocked on 18 September 2026 because the publishing credential lacked GitHub `workflow` scope. A fresh permission check on 22 September found that scope available, and the workflow was moved into its active location. Consult [implementation status](../docs/IMPLEMENTATION_STATUS.md) and the [validation receipt](../docs/VALIDATION.json) for verified run results. A workflow definition alone is not a passing test result.
