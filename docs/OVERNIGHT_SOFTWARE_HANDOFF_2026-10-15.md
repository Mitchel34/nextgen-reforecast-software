# Overnight software handoff — 15 October 2026

Both approved engineering milestones are implemented and independently reviewed: explicit receipt supersession and the bounded preparation dispatcher contract. The final integrated validation passes **123 targeted Python tests**. Active engineering stops at these completed milestones; no annual forecast, acquisition, training, service or paid resource was started.

| Capability ready for review | Evidence and practical limit |
|---|---|
| Complete-year planning retained | All 8,760 non-leap or 8,784 leap-year hourly issues, the explicit original origin/full history, retained-lead choice and source leads 1–18 remain bound |
| Explicit receipt supersession | [Journal contract](PREPARATION_RECEIPT_JOURNAL_CONTRACT.md): original checkpoint and every revision retained, reasons and expected prior hashes required, exact replay idempotent, stale/sibling/conflicting updates refused atomically |
| Bounded selection and result protocol | [Dispatch contract](PREPARATION_DISPATCH_CONTRACT.md): deterministic history-first selection; at most two tasks/two forecast issue hours; complete-study and exact active-journal binding; candidate declarations only, with zero dispatches |
| Engineering validation | 123 tests: 21 dispatcher, 20 journal and 82 prior orchestration/request/readiness/adapter/pinned-admission regressions, including four annual synthetic cases |

The journal milestone is [commit `fd139e0`](https://github.com/Mitchel34/nextgen-reforecast-software/commit/fd139e0c4c6aecb91832f373d00a9cb8928e5438). Public verification matched all eight changed Git blobs and observed zero Actions runs. The dispatcher milestone is the commit containing this handoff and [its source-bound receipt](evidence/preparation-dispatch-increment-20261015.json). The final handoff response reports its exact remote commit after normal fast-forward publication. Every progress commit uses `[skip ci]`; no workflow dispatch or paid CI is requested.

## Measured engineering resources

| Final serial batch | Tests | Wall seconds | Sampled peak RSS |
|---|---:|---:|---:|
| Journal milestone, small integration/regressions | 99 | 2.009 | 59,472 KiB |
| Journal milestone, annual cases | 3 | 18.925 | 84,832 KiB |
| Dispatcher milestone, small integration/regressions | 119 | 2.763 | 61,216 KiB |
| Dispatcher milestone, annual cases | 4 | 24.235 | 87,040 KiB |

The milestone batches overlap; their counts are not added as distinct tests. Each batch used one serial process, numerical thread limits of one, niceness 10, a 30-second wall stop and a sampled 256 MiB RSS stop. Load/free-memory checks ran before each batch, under the documented pause thresholds. No final batch hit a stop. The initial memory-stop attempt and streaming-hash correction from the preceding planner milestone remain in its historical evidence; no failed evidence was reset or removed.

These are local software-test costs. Hands-on researcher effort, total workflow turnaround and physical model compute are three separate **unmeasured** quantities. “50 steps to 10” and “40% faster” remain illustrative targets. No full Python-suite, fresh Node/browser, installed-wheel or real-user benchmark result is claimed.

## Actual-data execution gaps

The dispatcher interface invokes no adapter. History and forecast passes are caller declarations; no artifact is reverified or reused, and source qualification/execution readiness remain false. The existing forcing adapter still admits only a complete request within its two-issue/history/catchment limits. An annual task subset cannot become a smaller substitute study to bypass those limits or the original full history.

The journal is a **64-revision**, one-or-two-update protocol pilot. A complete annual base can be retained, but an empty base cannot progress all 4,381 default annual tasks within that bound. No history compaction, reset or automatic new journal manufactures capacity. Trusted latest-tip storage, atomic persistence, cross-process compare-and-swap, durable queue/locking and actual physical recovery remain unimplemented. A valid old journal cannot reveal a newer external journal without an independently trusted current identity.

Automatic source acquisition/decoding and domain qualification, actual full-year preparation, hosted execution/recovery, current-result verification and verified archive download remain unfinished. Existing scientific input/runtime/reference/profile admission checks are unchanged. Original research folders were not traversed or hydrated; private inputs, historical local commits and the pre-existing untracked main-checkout receipt remain preserved and excluded from publication.

## Next decisions for the morning

1. Select the next bounded engineering increment: a trusted local state adapter with atomic journal/tip persistence, compare-and-swap and deterministic crash/concurrent-writer tests. The current pure contracts supply its input identities; they do not provide storage semantics.
2. For any actual selected-site/year run, resolve one complete scientific/domain/origin/source/reference/runtime/protocol and costed resource package before launch. Current acquisition, physical-run, training and spending holds remain in force; this handoff requests no new authority.
3. Schedule real researcher benchmarking only after the supported end-to-end path exists, measuring human steps/effort, workflow elapsed time and model compute separately.

No access or source-concurrency blocker was observed during this increment. A later remote or local change must be reconciled rather than overwritten; publication uses ordinary fast-forward pushes and retains unrelated files.
