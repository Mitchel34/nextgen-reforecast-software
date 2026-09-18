# Architecture and implementation boundary

The first increment contains an offline control plane. Campaign planning and runtime inspection are independently testable and do not import the historical research implementation.

```mermaid
flowchart LR
    Spec[Strict campaign JSON] --> Validate[Schema and time/resource validation]
    Validate --> Assets[Bounded resident input checks]
    Assets --> Plan[Deterministic plan and blockers]
    Plan --> Ledger[Expected issue/lead ledger]
    Plan --> Report[Planning report]
    Profile[Pinned historical V3 profile] --> Doctor[Offline runtime inspection]
    Local[Explicit local asset root] --> Doctor
    Doctor --> Closure[Identity and qualification gaps]
```

`campaign.py` owns parsing, campaign contracts, bounded local asset identity checks and expected output keys. `runtime.py` owns the exact historical profile and its source/build/fixture closure inspection. `cli.py` owns command dispatch, structured errors, row bounds and atomic publication of new output files. The Python package has no third-party runtime dependencies and does not activate containers or network clients.

A specification identity hashes the canonical declared configuration. A plan identity hashes the observed planning result, so changing input availability or disabling asset checks produces a different plan. Domain input identities record declared scientific inputs; they are not serialized physical state or proof that those files contain the required forcing interval. Missing identities remain explicit.

## Future physical integration

The historical adapter must be extracted and qualified before `run` or `resume` can be implemented. Its contract is:

```mermaid
flowchart LR
    Origin[Bound origin and realization] --> History[Continuous historical state]
    H[Historical forcing] --> History
    History --> Boundary[Exact issue boundary]
    Boundary --> Child[Independent land and routing branch]
    F[Issue-specific forecast forcing] --> Child
    Child --> Validate[Clock / key / numeric / zero-exit checks]
    Validate --> Commit[Immutable verified issue commit]
    Commit --> Archive[Daily archive and lineage]
```

The parent continues under historical forcing only after isolation is acknowledged. Each child owns its input file descriptions, router and output writers. No child-to-parent state edge is permitted. New River's two nested gauge outputs are products of one domain trajectory. A source key, a matching clock and a routing q0 snapshot do not establish a complete portable land-state checkpoint.

Recovery reconstructs history from the same original origin and bound assets and suppresses only forecast issues with valid existing commits. It cannot silently shorten the historical interval, substitute missing meteorology or restore land state from discharge outputs. The existing replay helper and historical receipts motivate this design; fresh public-package replay tests are still required.

The manuscript analyzes these choices and their measured consequences. The generated campaign report describes one plan or, after execution is implemented, one specific run. Neither replaces the user/developer documentation or numerical qualification evidence.
