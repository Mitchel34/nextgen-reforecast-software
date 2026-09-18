# Source inspection notes

Scope: narrow read-only inspection of documents inside the supplied 20260917T233206Z core review archive. No model run, build, benchmark, fault-injection test, or recovery was executed for this outline. These preserved documents describe different development stages; the receiving agent must establish which interfaces and receipts apply to the final deployed version.

## REFORECAST_AND_DATA_AUDIT.md
Archive member: `HYDRA_review/docs/REFORECAST_AND_DATA_AUDIT.md`
SHA-256: `1ad39fe283188391fadee3ecd87cf04fa0448fe965a3c4cfb40383e48848e557`

```text
0020: ## 1. What produced the saved forecasts
0021: 
0022: **Inspected:** `L/final-closeout/HOST_FINAL.json`, `FINAL_CLOSEOUT.json`, the final launcher, controller, input bindings, and an actual daily archive.
0023: 
0024: The saved baseline is a newly generated **NextGen research reforecast using archived NWM meteorological forcing**. It is not archived operational NWM discharge or an archived operational NextGen forecast. The final host receipt reports two successful domain processes, each with one historical initialization, 65,375 hourly historical updates, 63,614 independent forecast issues, and 1,145,052 branch updates. The three exported gauges contain 3,435,156 forecast rows in total. The durable inventory records 5,318 daily archives, 2,659 per domain, occupying 351,142,901 bytes. These are historical terminal receipt values, not a new whole-archive recount.
0025: 
0026: The final launcher was `L/host/host_runner_r4.py`. Its predecessor startup failures and changes are distinguished by `recovery-r1` through `recovery-r4/PATCH_FILES.json`; they must not be mistaken for successive hydrologic parameter experiments. `L/model/run_domain.py:130–161` verifies the admitted domain, mask, CPU/memory allocation, and hashes before calling `production_day_controller_v1.execute_domain`. That function (`C/src/nextgen_reforecast/production_day_controller_v1.py:227–306`) copies the pinned native executable/middleware to executable mounts, starts the exact routing service, renders the hourly driver configuration, launches NextGen, validates terminal counts, and exports only committed archive rows.
0027: 
0028: ### Build and source identities
0029: 
0030: | Item | Identity and status |
0031: |---|---|
0032: | Container | `awiciroh/ciroh-ngen-image@sha256:2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff`, `linux/arm64` |
0033: | NextGen framework revision | `9175b640a4e6f1d90e58e0a65662174d08f052ef`, recorded in `D/local_only/shared_history_runtime_v3/build01/BUILD_EXPORT.json`; custom overlay is essential |
0034: | Deployed `ngen-shared` | SHA-256 `ee65c7748c4d2a7e9f3900fc3a5e8c16c045db90eb34a9b877b7bcc5dc942132`, 3,813,528 bytes |
0035: | Fortran BMI middleware | SHA-256 `09b65b5c2a76df4e8e9b334b9d3c56f39c327955306085cae692484742dcc162`, 74,504 bytes; middleware, not a new calibrated hydrologic component |
0036: | Exact v3 `Runtime.hpp` | `N/include/shared_history/Runtime.hpp`, SHA-256 `0f42b3a656c79909aaabc19334be4abac65ebf11e7fea8d03d1f4f15fccbfd25` |
0037: | t-route | `533fbd98362efdafae62392308727de4f0d4cc20`; routing source checks the image-resident `/ngen/troute_url` string at runtime |
0038: | Routing service v1 | SHA-256 `e772e3812f00c22a3926d7a56726ae03ed4b75a22494c4f4889c67d956aff50b` |
0039: | Routing v2 output wrapper | SHA-256 `91de42486400a79a357e8dcb7107827c0804d48cbdfc301321680ef720074fc3` |
0040: 
0041: **New narrow identity check:** all five resident `N/include/shared_history` headers match the existing build receipt. Twenty-six compared deployed Python modules match the current Desktop counterparts byte-for-byte; `__init__.py` differs. Full pairs and hashes are in `checks/physical_source_identity.json`. Current repository HEAD alone does not identify the results. The package includes the deployed Python copies, actual v3 native source, current patch tooling as a separate source, and root's Git metadata/diff.
0042: 
0043: **Provenance discrepancy:** the manuscript-support file `PHYSICAL_RUNTIME_IDENTITIES.json` correctly stated that component source revisions were not found in its limited set of bindings. This review additionally found `BUILD_EXPORT.json`, which recovers the framework revision and overlay-to-executable linkage. That does **not** resolve the source-to-binary attestations for every physical component library or the upstream parameter calibration history. Do not use the datastream configuration-generator revision `86c94924...` as the engine revision.
0044: 
0045: The Desktop copies of the detailed build receipt and some logs are currently dataless iCloud placeholders. Reads that stalled were stopped. The exact five native headers were recovered from resident **N** and checked against the build export. No dependency download, native rebuild, or large raw hash was performed.
0046: 
```

```text
0065: ### Actual routing behavior
0066: 
0067: `shared_history_routing_service_v1.py:62–97` rejects enabled waterbodies, assimilation, diffusive/hybrid routing, coastal boundaries, GIUH routing, and external restart settings. It requires `V02-structured`, `dt=300`, and `qts_subdivisions=12`. The loaded YAML sets one routing CPU, `by-subnetwork-jit-clustered`, no streamflow nudging, no reservoir persistence assimilation, and no waterbody breaks.
0068: 
0069: The file-mode YAML's `nts=216` and output-directory settings are not the active persistent-loop duration. `RoutingSession.advance_series` calls the installed numerical kernel with `nts=12 × hours`, supplies in-memory laterals, advances actual `q0` and clock, and checks the resulting time. `output_parameters` is replaced by an empty dictionary because this service owns its writers. The v2 wrapper retains required gauge rows each hour; full-segment diagnostic stride is zero in the production `router.json`. It does not change the v1 numerical kernel.
0070: 
0071: One unresolved routing interpretation is explicit in the code: the installed `HYFeaturesNetwork.downstream_flowpath_dict` assigns each aggregated nexus lateral to one mapped segment, including confluence cases. No new spatial remapping or independent mass-balance diagnosis was introduced in this review.
0072: 
```

## README.md
Archive member: `HYDRA_review/evidence/NextGen_Reforecast/native/shared_history_driver/README.md`
SHA-256: `e9f136f43e945b3bb5a34d693b173f558c8c7119d88b58de98cc63c6341654ea`

## V2_RUNTIME_CONTRACT.md
Archive member: `HYDRA_review/evidence/NextGen_Reforecast/native/shared_history_driver/V2_RUNTIME_CONTRACT.md`
SHA-256: `4e7586ac7cccb58e967e0cd4050d4fd515291b51f640ed37e547c91942c05f88`

```text
0102: ## Recovery: honest state inventory
0103: 
0104: | State | Live branch mechanism | Durable worker-loss mechanism |
0105: | --- | --- | --- |
0106: | CFE storage, accumulators and allocated/native state | Process copy-on-write | Reconstruct by identical history-only replay; no complete serializer claimed |
0107: | NoahOWP arrays, Fortran/module state and clocks | Same process fork | Same history-only replay; visible BMI values are not declared complete |
0108: | SLOTH and coupled provider/driver graph | Same process fork | Same history-only replay from bound origin and configuration |
0109: | t-route channel q0 and clock | Verified channel snapshot/restore | Reconstruct alongside history replay; q0 alone is not a land checkpoint |
0110: | Pending forecast children | Explicit PID/issue ownership | Treat uncommitted work as pending; never promote partial child files |
0111: | Committed forecasts | Per-issue checksum-bound commit | Reuse verified outputs; suppress their issue epochs from new forks |
0112: 
0113: No new privileged process-checkpoint technology or broadly serializable BMI
0114: checkpoint has been adopted. A full portable checkpoint is not established.
0115: 
0116: `shared_history_recovery_v2.py` implements transactionally published per-issue
0117: forecast CSVs plus immutable model/source bindings. It requires the reaped-child
0118: journal before committing, extracts exactly 18 hourly rows per configured gauge,
0119: verifies source/output finiteness and timestamps, and publishes the commit
0120: directory atomically. Existing commits are verified and reused, never overwritten.
0121: 
0122: `recovery_plan(...)` is side-effect-free. It rechecks the committed outputs and
0123: complete source/binary/domain bindings, checks remaining recovery authority and a
0124: declared replay-time reserve, and returns runtime overrides containing **only
0125: uncommitted issue epochs**. Historical weather advances from the original origin
0126: continuously; no forecast branch is used to update history. This is recovery
0127: after a failure, not repeating the antecedent history at every issue. A numeric
0128: estimate supplied to the API is not itself measurement evidence: the coordinator
0129: must bind it to the actual timing receipt and reserve money for recovery.
0130: 
```

```text
0062: ## Concurrent child ownership
0063: 
0064: The parent remains single threaded at the fork. It flushes its own streams and
0065: obtains the routing snapshot at the exact issue boundary. In the child:
0066: 
0067: 1. Parent routing pipes and runtime streams are detached; inherited child PID
0068:    ownership is cleared, so a child cannot kill its siblings.
0069: 2. Each remaining read-only regular input is **reopened** and verified by device,
0070:    inode, size and offset. `dup2` only rebinds the new description to the original
0071:    descriptor number; a plain `dup` would still share the parent's offset.
0072: 3. Dormant legacy writers are redirected to independent `/dev/null` descriptions;
0073:    unknown writable/component diagnostic handles remain a real refusal.
0074: 4. The stable forcing wrapper selects the child weather. A separate routing
0075:    process restores the issue snapshot. Routing exec inherits no model/controller
0076:    descriptors beyond its explicit standard streams.
0077: 5. The child sends an isolation acknowledgement. Only then may the parent advance.
0078: 
0079: The parent tracks owned children, accepts out-of-order completion and applies
0080: backpressure when the pool is full. Every child has a deadline; timeout/failure
0081: terminates owned work without cold fallback or automatic resubmission. Final
0082: success drains the pool. The flushable `history/BRANCH_COMPLETIONS.jsonl` journal
0083: records only children already reaped with zero exit status. These mechanics do not
0084: change exact component/provider/router clocks or permit child feedback.
0085: 
```
