# Development

Keep the original research workspaces read-only. Use the new public repository and its ignored `.local/` and `.venv/` directories for all work. Preserve the original outline and completed feasibility dossier.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
mkdir -p .local/tmp
TMPDIR="$PWD/.local/tmp" PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

The core currently uses only the standard library. Unit tests exercise parsing, asset identity and path bounds, time arithmetic, explicit execution limits and transactional CLI output; they do not run hydrologic models. The [CI template](../ci/tests.yml) is designed to repeat the offline suite on Python 3.11–3.14 using pinned action revisions. Activation is blocked because the current publishing credential lacks GitHub `workflow` scope; no remote CI run has occurred. See [activation instructions](../ci/README.md).

The coordinator owns CLI/package integration; the campaign and runtime modules have focused contracts and independent tests. New functionality must retain deterministic scientific identities and explain how a new check differs from source inspection, a synthetic test and a physical-model qualification. Do not add a passing-looking mock in place of an unqualified runtime.

Use [the benchmark protocol](../benchmarks/PROTOCOL.md) for future experiments. Keep measured evidence in a new timestamped directory, including failed attempts, input/build identities, hardware, resources and tolerances. Do not modify historical receipts or compare changed CPU allocations as an equal-resource algorithmic speedup.

No project-wide release license has yet been selected. Track inherited dependency/data/source notices separately, and do not copy private research implementation, binaries or datasets into public commits without resolving their specific redistribution scope.
