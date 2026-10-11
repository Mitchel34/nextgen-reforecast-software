# NextGen Reforecast browser prototype

A local, dependency-free interaction prototype for minimal researcher inputs, exact issue/lead review, honest preparation blockers and a downloadable study request. It is not hosted, does not acquire data or execute models, and produces no scientific dataset. See the [request contract](../docs/BROWSER_REQUEST_CONTRACT.md).

For maintainers to preview locally from the repository:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory web
```

Open [the local preview](http://127.0.0.1:8765). This is a developer preview command; the product objective remains a hosted browser experience requiring no local terminal/model installation for researchers. The page uses browser ES modules and should be served over HTTP rather than opened as a `file:` URL.

Choose “Try Watauga example”, optionally change the longest lead to 6 hours, then review. Both selected days are proposed UTC issue dates. The default January 1–2 example has 48 hourly issues; it is not the original two-issue scientific benchmark. Download produces request JSON with `execution_ready: false` and explicit unresolved preparation steps. Editing any field clears the review/download. No server receives form values, and refreshing the page clears them.

“No forecast leads” records an unimplemented continuous-simulation preference without a campaign translation. Arbitrary IDs and dates do not become eligible by being accepted in the form. Even Watauga metadata is a documented demonstration, not live resolution.

Tests (Node 20 or later and Python 3.11 or later for translation integration; no package install):

```sh
node --test web/tests/*.test.mjs
```

Files: `request.mjs` is the pure versioned request/time contract, `app.mjs` the interaction layer, `index.html`/`styles.css` the accessible responsive layout, and `tests/request.test.mjs` boundary tests. [Internal QA](QA_2026-10-10.md) records tested interactions and limitations. No usability participant was recruited and no user-study result is claimed.
