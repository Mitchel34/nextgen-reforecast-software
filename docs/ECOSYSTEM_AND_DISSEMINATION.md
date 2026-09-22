# Ecosystem and dissemination source review

Verified against official sources on 22 September 2026. This is a dated review of the owner-supplied roadmap, not a claim that the integrations or public physical runtime are implemented.

## Product boundaries

| Project or concept | Source-backed role | Implication for this project |
|---|---|---|
| NextGen | NOAA describes a model- and language-agnostic framework whose formulations combine models/modules: [NextGen-Info](https://github.com/NOAA-OWP/NextGen-Info) | Framework flexibility does not qualify arbitrary formulations for live process branching |
| National Water Model | NOAA documents hourly cycles, hourly deterministic output through 18 hours, HRRR/RAP meteorology and Analysis/Assimilation initialization for **CONUS**: [NWM configuration](https://water.noaa.gov/about/nwm) | State the region; other configurations differ. A research NextGen campaign is not automatically an archived operational NWM forecast |
| NGIAB | Containerized NextGen deployment and evaluation integration: [maintainer repository](https://github.com/CIROH-UA/NGIAB-CloudInfra), [2025 journal paper](https://repository.library.noaa.gov/view/noaa/72761/noaa_72761_DS1.pdf) | Reuse deployment where compatible; qualify the pinned image and custom state hooks. The paper's anticipated NWM v4 components do not establish completed operational deployment |
| DataStreamCLI | Preprocessing-to-execution workflow: [maintainer repository](https://github.com/CIROH-UA/datastreamcli) | Build an explicit adapter; workflow overlap does not demonstrate branch isolation or replay equivalence |
| ForcingProcessor | Catchment averaging of gridded products, including NWM: [maintainer repository](https://github.com/CIROH-UA/forcingprocessor) | Preserve source, weighting and interval provenance when adapting outputs |
| NextGen Forcings Engine | Separate project with CSV/NetCDF/BMI pathways and documented AORC/GFS/CFS/HRRR inputs: [NOAA repository](https://github.com/NOAA-OWP/ngen-forcing) | Do not conflate it with ForcingProcessor. Recent-data extraction utilities do not establish multi-year archive availability |
| NRDS | CIROH's April 2026 account describes CFE–NoahOWP and LSTM datastreams with T-Route: [dated maintainer article](https://hub.ciroh.org/blog/nextgen-research-datastream-april-2026/) | Attribute capabilities to that source; current service availability was not independently tested |
| TEEHR | Hydrologic evaluation infrastructure: [maintainer repository](https://github.com/RTIInternational/teehr) | A future export adapter must preserve issue/lead/valid-time identity and prevent accidental collapse into one time series |

These sources support ecosystem placement. They do not establish uniqueness of the proposed contribution, source-to-binary identity, data availability, or correctness of this project's future adapters. Version-pinned interface tests remain development work.

## AGU26 timing and eligibility

[AGU26](https://www.agu.org/agu26) is scheduled for **7–11 December 2026 at Moscone Center in San Francisco**. The [official presentation page](https://www.agu.org/annual-meeting/Present?tab=abstracts#late-session) was checked in the live browser because its dynamic content was absent from the text extractor.

Late-breaking submission is event-specific. The detailed page requires relevance to a listed event; unrelated submissions are rejected. It also requires AGU membership and waives the ordinary first-author limit for these sessions. On the review date, the page listed:

| Deadline | Listed event topics |
|---|---|
| 29 September 2026, 11:59 p.m. EDT | South American earthquakes and recent 2026 wildfires |
| 13 October 2026, 11:59 p.m. EDT | Grand Canyon flooding and Nepal debris avalanche/flash flooding |

The roadmap's 29 September date is therefore **not a general reopening for software abstracts**. No eligible connection between this reforecast-software project and a listed event has been established. The homepage summary did not include all deadlines visible on the detailed page. Recheck the live rules before relying on any date.

Plan software and manuscript work around evidence readiness. An already accepted related presentation may offer a separate dissemination route if its scope and organizers permit, but this review does not establish such an acceptance or permission. No abstract, conference registration, journal submission or external message was sent.

## Manuscript implications

Use the owner roadmap as design input and attributed historical context. Retain the distinction among historical inspected receipts, new offline tests, isolated CFE sensitivity, future physical qualification and independent researcher reproduction. Describe the proposed 20-hour example as a separate initialization/fixture design task; it does not replace the original 786-hour qualification history.

The target journal remains *Environmental Modelling & Software*. The existing [journal-requirements record](../paper/JOURNAL_REQUIREMENTS.md) still needs a successful current guide review before submission readiness can be certified. The AGU deadline does not justify inventing results, abbreviating initialization or skipping the public-runtime qualification gates.
