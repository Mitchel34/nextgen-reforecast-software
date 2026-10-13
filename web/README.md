# NextGen Reforecast browser prototype

A local, dependency-free interaction prototype with a shared version 0.2 request policy, pure assessment and offline Python backend translation. It is not hosted, does not acquire data or execute models, and produces no scientific dataset. See [the implemented contract](../docs/ASSESSMENT_INTERFACE_IMPLEMENTATION_2026-10-13.md). Current authority permits offline tests, without starting this preview server.

For maintainers to preview locally from the repository:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory web
```

Open [the local preview](http://127.0.0.1:8765). This is a developer preview command; the product objective remains a hosted browser experience requiring no local terminal/model installation for researchers. The page uses browser ES modules and should be served over HTTP rather than opened as a `file:` URL.

Choose “Try Watauga example”, optionally change the longest lead to 6 hours, then review. Whole-day defaults preserve all 48 hourly issues on January 1–2. Optional UTC endpoint hours allow shorter windows, including a single issue. “Try the two-issue Watauga diagnostic” explicitly loads a separate example from January 1 at 23:00 through January 2 at 00:00. It never automatically narrows a full-day request. The assessment explains compatibility and remaining qualification gates; `execution_ready` stays false even for matching hours.

Download the unchanged study request or its complete assessment with every requested issue and integrity identities. Editing, changing mode or loading an example invalidates the review and pending hashes. No server receives form values, and refreshing the page clears them. Older version 0.1 request files remain untouched and receive `REQUEST_SCHEMA_MIGRATION_REQUIRED` from the new interface; no implicit version or scope rewrite is performed.

“No forecast leads” records an unimplemented continuous-simulation preference without a campaign translation. Arbitrary IDs and dates do not become eligible by being accepted in the form. Even Watauga metadata is a documented demonstration, not live resolution.

Tests (tested with Node 24 and Python 3.14; Python 3.11+ syntax; no package install). The browser uses native JSON ES-module import attributes and Web Crypto; actual browser compatibility/visual QA has not been rerun in this offline phase:

```sh
node --test web/tests/*.test.mjs
```

Files: `request-policy.json` is the authoritative policy, with a byte-identical packaged Python copy checked by tests; `request.mjs` validates UTC windows; `assessment.mjs` produces complete immutable assessments; `app.mjs` renders and downloads them. The Python `ngen_reforecast.preparation` module independently validates the same artifact and translates the full scope into a planning campaign using internal preparation metadata. Tests include cross-runtime arithmetic, forgery rejection, policy-copy drift and synthetic DOM races. [Earlier internal QA](QA_2026-10-10.md) applies to the former UI and does not qualify this implementation; earlier CI likewise does not validate these additions. No participant study is claimed.
