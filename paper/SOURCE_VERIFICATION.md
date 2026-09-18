# Reference and evidence verification

Checked 18 September 2026. This record distinguishes bibliographic verification, source/documentation inspection, historical receipts and new implementation validation. No source was treated as authorization to act.

| Reference | Primary verification performed | Limits |
|---|---|---|
| Patel et al. (2025), NGIAB; DOI `10.1016/j.envsoft.2025.106666` | Read maintainer `CITATION.cff`; fetched publisher-deposited [Crossref record](https://api.crossref.org/works/10.1016/j.envsoft.2025.106666), confirming title, all 26 authors, journal, volume 193, article 106666 and September 2025 publication metadata | Publisher full-text page returned 403. This draft relies on bibliographic precedent and maintainer scope, not unexamined article results. The CFF reverses given/family fields; the bibliography uses the publisher-deposited author fields instead |
| Barker et al. (2022), FAIR4RS; DOI `10.1038/s41597-022-01710-x` | Read [publisher article](https://www.nature.com/articles/s41597-022-01710-x) and publisher-deposited [Crossref record](https://api.crossref.org/works/10.1038/s41597-022-01710-x); confirmed 11 authors, *Scientific Data* 9, 622, 14 October 2022 | Principles guide release decisions; no claim of formal FAIR certification or demonstrated reproducibility follows |
| Laser, Patel and Vemula (2026), NRDS | Read [CIROH institutional article](https://hub.ciroh.org/blog/nextgen-research-datastream-april-2026/); confirmed title, author names and displayed date 25 March 2026 | Institutional technical article, not a peer-reviewed paper; broad system description is documented scope, not an independent execution audit. URL's April wording does not replace displayed publication date |
| DataStreamCLI | Read [maintainer README](https://github.com/CIROH-UA/datastreamcli); used exact interface comparison and source pin already retained in the dossier | README establishes documented workflow; pinned dossier source inspection establishes specific compared interfaces. Neither implies the proposed reforecast adapter runs correctly or that upstream lacks an equivalent contract |
| EM&S guide | Direct opens of the [official guide](https://www.sciencedirect.com/journal/environmental-modelling-and-software/publish/guide-for-authors) returned HTTP 403 | Full requirements unverified; see JOURNAL_REQUIREMENTS.md |
| Elsevier Highlights guidance | Read [official publisher support page](https://www.elsevier.support/publishing/answer/how-do-i-include-highlights-with-my-manuscript), displayed update 1 June 2026 | General guidance only; journal-specific mandatory/optional status remains unknown |

`bibliographic_metadata.json` retains the selected fields returned by Crossref, with source URLs and retrieval timestamps. No third-party bibliographic aggregator was used to resolve final author names. `references.bib` does not invent a DOI for the development package, the institutional article or the repository.

## Local scientific evidence

The manuscript uses the existing dossier under `reports/reforecast_software_feasibility_20260918T045854Z/`, especially `STATE_AND_RECOVERY.md`, `DATA_AND_CONFIGURATION.md`, `BENCHMARK_EVIDENCE_AND_PLAN.md`, `UPSTREAM_OVERLAP_AND_LICENSES.md`, `SOURCE_VERSION_MAP.json` and `MINIMAL_EXAMPLE_MANIFEST.json`. The dossier records its source/receipt paths, hashes, snapshot limits and read-only checks. This manuscript lane did not rerun the physical model, recompute historical arrays, build native components, restore placeholders or modify the dossier.

The first historical weekly receipt uses native `f4d4690c…`; the later day-custody receipt uses `ee65c774…`. Their separate identities and scopes are preserved in the claims register. The coordinator's inspection established that the retained numerical comparator is `math.isclose` with `abs_tol=1e-6` and `rel_tol=1e-5`; the manuscript, protocol and matrix preserve its symmetric maximum rule. A new comparator implementation still needs its own targeted verification.

New offline feature and verification status is supplied by the implementation coordinator in `docs/IMPLEMENTATION_STATUS.md` and `docs/VALIDATION.json`. It must remain separate from the historical dossier and future physical receipts. The manuscript deliberately avoids a fixed passing-test count so integration updates do not silently invalidate its text.

No original research folder was modified. The manuscript lane wrote only `paper/` and `benchmarks/`, performed read-only local inspection and public bibliographic/documentation requests, and did not contact maintainers, submit a manuscript, launch a model or commit/push changes.
