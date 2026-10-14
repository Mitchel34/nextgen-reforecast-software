# Reviewed readiness publication — 14 October 2026

The owner explicitly requested committing and pushing the completed NextGen software work. The destination is the verified existing public repository [Mitchel34/nextgen-reforecast-software](https://github.com/Mitchel34/nextgen-reforecast-software), following its established `main` publication workflow. This record describes the reviewed pre-push snapshot; remote/public verification is performed after the one ordinary push and reported separately. It does not claim a new CI run or scientific experiment.

## Reviewed snapshots

| Original local milestone | Sanitized publication commit | Scope |
|---|---|---|
| `e0b03a9588670b95224586ade0137f6bd91ab5a4` | `b7e2f8eb7c6a4163bd7608aa2a0e02358e41199d` | Evidence-bound preparation result contract |
| `64e03e24c1033da2248d970b4aaecf4fbd37a909` | `52067edcede007f69b261cd50f600b96e5df8184` | Bounded resident forcing adapter and readiness-report browser inspection |

The original local commits are preserved. The publication copies descend directly from the verified public base `cf80266ef599c5c022a9d43d4d03a02a5ecffe0a`; the original milestone commits are not ancestors of the publication branch. This prevents host-specific receipt fields from entering newly published history. No force push or history overwrite is used.

Implementation and test bytes remain exact. Only the two evidence receipts are sanitized in these publication snapshots: host-specific worktree/checkout locations and private capture-directory references are removed; capture names, hashes, sizes, outcomes and qualification limits remain. Unreviewed checkout files are excluded. The second receipt distinguishes its original local overnight-receipt identity from the newly sanitized public receipt identity. No private raw logs, model inputs, credentials, binaries or research artifacts are added.

The [preflight evidence](evidence/readiness-publication-preflight-20261014.json) binds source/evidence verification, publication ancestry, the independently reviewed sanitation and current remote base. The existing historical implementation receipts retain their checkpoint statements; a local “no public push” statement is not represented as the outcome of this later authorized publication.

## Validation and limits

Retained hash-matched evidence records 45 targeted Python and 58 Node tests for the first milestone, then 60 targeted Python and 77 serial Node tests for the resumed adapter/browser milestone. Independent reviews completed. The earlier failed browser batch and its corrected display assumption remain explicit in the evidence; production file guards were preserved. No tests, physical models, downloads, servers or research jobs are rerun as part of publication.

The adapter admits at most two issues for local decoded-byte checking. A twelve-month request retains all 8,760 hourly issues and receives an explicit adapter-limit blocker. Every issue retains its full 18-hour forcing requirement. Content success retains source truth/version/availability/radiation qualification blockers; execution and release readiness remain false. Automatic preparation, hosted submission/execution/recovery, verified scientific archive delivery, live browser/participant evaluation and measured workflow performance remain unfinished. “50 steps to 10” and “40% faster” remain illustrative targets.

## Publication checks

Repository metadata confirms public visibility and default branch `main`. The remote base remains `cf80266ef599c5c022a9d43d4d03a02a5ecffe0a`, and `main` is unprotected at this checkpoint. Publication uses a normal fast-forward push; concurrent remote advancement causes refusal rather than overwriting it. The original checkout's unreviewed item is preserved separately and excluded.

All publication commits contain `[skip ci]`. The existing workflow triggers only `push` and `pull_request`; [GitHub's documented skip marker](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs) prevents those runs. No workflow, permission or billing configuration is changed, and no PR or workflow dispatch is created. Post-push verification checks the exact remote SHA, unauthenticated public availability, published source/evidence bytes and absence of new runs for the publication commits.
