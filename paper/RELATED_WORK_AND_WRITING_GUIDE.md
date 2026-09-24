# Environmental Modelling & Software: related work and writing guide

Reviewed 23 September 2026. This targeted journal review supports the [manuscript development plan](DEVELOPMENT_PLAN.md), [draft](MANUSCRIPT.md) and [product objectives](../docs/PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md). It is a selected reading set, not a systematic literature review or proof of novelty. Nine journal articles were selected for proximity to NextGen, reproducible modeling, browser access, evaluation or user-centered design. Existing non-journal ecosystem sources and FAIR4RS remain relevant but are not counted as EM&S papers.

Read the sources as scientific context and examples of clear organization. The proposed adaptations below are our editorial and study-design judgments, not requirements imposed by those papers. Do not copy prose or reproduce figures without checking attribution and permissions. Journal formatting requirements remain a separate [live-guide check](JOURNAL_REQUIREMENTS.md).

## Selected references and inspected evidence

Full author lists and stable citation keys are in [references.bib](references.bib); publisher-deposited bibliographic records are in [RELATED_WORK_METADATA.json](RELATED_WORK_METADATA.json). Publication years below follow journal publication, not the year embedded in the DOI. An accessible paper or associated repository does not establish that we reproduced its experiment.

### R1 — NextGen deployment and end-to-end workflow

**Patel et al. (2025).** *NextGen In A Box (NGIAB): Open-Source containerization of the NextGen framework to enable community-driven hydrology modeling.* EM&S **193**, 106666. Key: `patel2025ngiab`. [DOI](https://doi.org/10.1016/j.envsoft.2025.106666); [NOAA full text](https://repository.library.noaa.gov/view/noaa/72761/noaa_72761_DS1.pdf).

Full text inspected. Useful anchors: §3.1/Fig. 2 architecture; Figs. 5 and 8 workflow/preparation; §4.2/Fig. 12 performance; hardware Tables 2–3; availability statement. Its Provo demonstration is historical simulation. Use it to acknowledge existing preparation, deployment and evaluation capabilities, and to separate workflow demonstration from benchmark evidence. It does not establish our issue-by-lead reforecast contract.

### R2 — Browser-based NextGen research

**Nassar et al. (2026).** *A cloud-based JupyterHub platform for community research with the NextGen water resources modeling framework.* EM&S **203**, 107031. Key: `nassar2026cloud`. [DOI](https://doi.org/10.1016/j.envsoft.2026.107031); [publisher](https://www.sciencedirect.com/science/article/pii/S1364815226001787); [author-uploaded full text](https://www.researchgate.net/publication/404875639_A_Cloud-based_JupyterHub_platform_for_community_research_with_the_NextGen_water_resources_modeling_framework).

Full text inspected. §2/Figs. 1–2 connect architecture to user sequence; §3.2 follows preparation, execution, calibration and evaluation; Appendix Table B lists forcing units. The Logan demonstration uses historical AORC inputs. Browser access and automated preparation already exist through notebooks; our proposed contribution must be evaluated more narrowly. Use the workflow sequence as an organizational model, without treating a notebook demonstration as evidence for our no-code usability target.

### R3 — State-aware NextGen scientific experiments

**Foroumandi, Moradkhani, Krajewski and Ogden (2025).** *Ensemble data assimilation for operational streamflow predictions in the next generation (NextGen) framework.* EM&S **185**, 106306. Key: `foroumandi2025assimilation`. [DOI](https://doi.org/10.1016/j.envsoft.2024.106306); [publisher](https://www.sciencedirect.com/science/article/pii/S1364815224003670); [author-uploaded full text](https://www.researchgate.net/publication/387272272_Ensemble_Data_Assimilation_for_Operational_Streamflow_Predictions_in_the_Next_Generation_NextGen_Framework).

Full text inspected. §§2.7–2.8 define metrics and experiments before implementation (§3) and results (§4); Fig. 3 explains sequence, and Table 2 describes basins. The daily CFE/NLDAS experiments include predicted priors after earlier assimilation. They are not an established equivalent of our archived-weather, multiple-lead campaign. Use as adjacent state/time research, not as justification for adding assimilation to the initial product or for the CFE mapping change.

### R4 — Repository, execution environment and model interface integration

**Choi et al. (2021).** *Toward open and reproducible environmental modeling by integrating online data repositories, computational environments, and model Application Programming Interfaces.* EM&S **135**, 104888. Key: `choi2021open`. [DOI](https://doi.org/10.1016/j.envsoft.2020.104888); [institutional record](https://digitalcommons.usu.edu/cee_facpub/3777/).

Publisher-indexed section text and institutional metadata inspected; complete visual layout not verified. §2.1/Fig. 1 introduces the architecture and §2.2 its hydrologic implementation using HydroShare/JupyterHub/pySUMMA. Use the general-design-to-specific-example progression to explain our acquisition, Linux execution and retained artifacts. Reusing that organizational idea does not select our hosting provider, stack or model API.

### R5 — Comparative evaluation of computational environments

**Choi et al. (2023).** *Comparing containerization-based approaches for reproducible computational modeling of environmental systems.* EM&S **167**, 105760. Key: `choi2023containers`. [DOI](https://doi.org/10.1016/j.envsoft.2023.105760); [author-uploaded accepted manuscript](https://www.researchgate.net/publication/371674344_Comparing_containerization-based_approaches_for_reproducible_computational_modeling_of_environmental_systems); [institutional record](https://experts.illinois.edu/en/publications/comparing-containerization-based-approaches-for-reproducible-comp/).

Accepted manuscript inspected. §2 defines approaches and evaluation; §3 separates quantitative and qualitative findings; §§4–5 discuss tradeoffs and conclusions. Tables 1–3 identify approaches, environment and scenarios. Six expert coauthors supplied competency ratings: these are not independent novice-user trials. Use its explicit comparison setup and developer/user distinction; our numerical equivalence, resource trials and external UX protocol still require their own evidence.

### R6 — Reproducibility terminology and executable artifacts

**Essawy et al. (2020).** *A taxonomy for reproducible and replicable research in environmental modelling.* EM&S **134**, 104753. Key: `essawy2020taxonomy`. [DOI](https://doi.org/10.1016/j.envsoft.2020.104753); [author manuscript](https://hydrology.usu.edu/dtarb/Essawy_2020_Taxonomy_AuthorVersion.pdf).

Author manuscript inspected. The study distinguishes repeatable, runnable, reproducible and replicable work with computational examples. Use its explicit definitions to clarify what each of our release and reproduction claims actually tests. Our E1–E4 UX evidence levels describe different questions and must not be presented as this paper's taxonomy. A repository, a working container and independent reproduction remain different evidence states.

### R7 — Evaluation linked to the intended purpose

**Bennett et al. (2013).** *Characterising performance of environmental models.* EM&S **40**, 1–20. Key: `bennett2013performance`. [DOI](https://doi.org/10.1016/j.envsoft.2012.09.011); [institutional full text](https://ris.utwente.nl/ws/files/7048737/characterising.pdf).

Full text inspected. §§2–3 establish context and evaluation data, §§4–5 cover quantitative/qualitative methods, and §6 gives a purpose-led procedure. Connect each research question to measurements and interpretation. This paper concerns environmental-model performance; it does not supply our branch-equivalence tolerance, fault policy or UX success threshold. Those remain predeclared project decisions. Scientific skill, execution equivalence, cost and usability need separate conclusions.

### R8 — Designing for actual use

**Houtkamp, Janssen, Lokers and de Groot (2025).** *Applying user-centred design to climate and environmental tools.* EM&S **192**, 106519. Key: `houtkamp2025ucd`. [DOI](https://doi.org/10.1016/j.envsoft.2025.106519); [institutional full text](https://edepot.wur.nl/694448).

Full text inspected. §2/Fig. 1 describes iterative user-centered design; §3 explains the study approach; §5 uses three cases. Its focus on users, context, content and sustained use supports evaluating our saved journeys before treating a finished interface as a usable product. The paper's cases are environmental/climate tools, not a NextGen hydrologist sample; our proposed participant numbers and acceptance rules are not validated by this citation.

### R9 — Environmental web application precedent

**Swain et al. (2016).** *A new open source platform for lowering the barrier for environmental web app development.* EM&S **85**, 11–26. Key: `swain2016tethys`. [DOI](https://doi.org/10.1016/j.envsoft.2016.08.003); [author institutional record and abstract](https://scholarcommons.sc.edu/eciv_facpub/49/).

Bibliographic metadata and institutional abstract inspected; full article layout not verified in this review. Tethys supplies environmental web-application development/hosting precedent. Cite it for context, not an inspected figure template, an adopted technology choice, or proof that our users can complete a study. This reference helps prevent framing a hosted environmental application as novel by itself.

## Section-by-section authoring map

The numbered sections follow the current draft so claims and links remain stable. “Borrow” means adapt the explanatory organization with original prose and our own evidence. Drafting notes in the manuscript are editorial aids to remove before submission.

| Our section | Related work to consult | Layout, framing and narrative decision | Evidence needed for our final prose |
|---|---|---|---|
| Abstract | R1, R2, R5 | Researcher problem → bounded software contribution → evaluation → measured findings → scope. Draft last; keep implementation details out unless essential. | Released features and completed Q1–Q5 findings; no invented savings or usability result |
| 1. Introduction | R1–R2, R8–R9 | Start with the scientist's desired study and preparation burden; explain existing solutions; end with the specific unresolved experiment contract and five questions. | Accurate version-specific comparison; no “first browser NextGen” or generic automation novelty claim |
| 2. Computational problem and scientific contract | R3, R6–R7 | Define experiment, state, forcing interval and forecast coordinates before implementation. Include a small time/state schematic and a table of immutable identities. | Our tested contracts and qualified inputs; papers do not establish our timestamp or initialization rules |
| 2.3. Parameter mapping and variants | R3, R7; separate upstream/source evidence | Explain why a correct execution can reproduce a problematic configuration; keep one-factor parameter science separate from runtime comparisons. | Existing CFE finding and future coupled qualification; no EM&S paper here verifies `mean.slope_1km` as our validated correction |
| 3. Software design and methods | R1–R2, R4–R6 | Follow the user journey, then show how browser, preparation, queue/worker, engine and archive fulfill it. Pair a system diagram with a user sequence. Move commands/configuration listings to supplement. | Inspected release code and matching architecture; planned features visibly labeled |
| 4. Evaluation protocol | R3, R5, R7–R8 | State questions, comparators, fixtures, controls, resources, failure cases and user tasks before results. Separate hydrology, computational fidelity and human use. | Frozen protocol, E03–E09 receipts and UX evidence; expert ratings are not external task completion |
| 5. Results | R1–R2, R5 | Present capability/coverage first, then Q1 equivalence, Q2 isolation, Q3 recovery, Q4 resources and Q5 transfer/usability. Keep historical motivation separate. | All admitted trials, failed cases, denominators and assistance; no literature result substituted for our measurements |
| 6. Discussion and limitations | R2, R5–R8 | Answer the questions, compare with existing workflows, then explain generalizability, scientific assumptions, user barriers and maintenance. Distinguish findings from future work. | Actual release/evaluation limits; no inferred hydrologic improvement from software fidelity |
| 7. Conclusion | R1, R5 | State the supported contribution and who can use it, followed by the main limitation and next justified extension. Do not repeat the feature list. | Claims already substantiated in results; no new novelty or scale claim |
| Availability and declarations | R1, R4, R6; FAIR4RS | Provide an artifact manifest: code, environment, inputs, outputs, analysis and reproduction instructions with exact versions and access terms. | Accessible permitted deposits; factual author declarations; current journal instructions |
| References and supplement | All selected sources | Keep methodological citations near their claims; cite software/data versions separately from descriptive papers. Put detailed recipes, units, inventories and assistance records in the supplement. | DOI/author checks, source access notes and a claim-to-artifact audit |

The draft's currently historical results subsections stay intact until new results exist. The eventual Q1–Q5 result organization is a writing target, not a new experiment or a claim that the present draft already contains those findings.

## How this changes the software and manuscript plan

1. **Keep the product story visible.** A hydrologist selects a location, eligible dates and forecast preferences, and receives an inspectable dataset. The paper must explain how scientific choices become qualified defaults and visible exceptions. Show the user journey before detailed process internals.
2. **Evaluate two kinds of reuse.** An operator reproduces the released experiment in a clean environment; a hydrologist completes the browser workflow without local setup. Preserve the [UX protocol](../docs/UX_EVALUATION_PROTOCOL.md) and its assistance/failure records. Neither exercise replaces the other.
3. **Compare responsibilities, not marketing labels.** Build a literature/interface matrix for location selection, acquisition, scientific defaults, issue/lead identity, initialization, recovery, provenance and publication. Mark unexamined capabilities unknown; do not turn absence from a paper into absence from its software.
4. **Tie every promised benefit to an experiment.** Q1–Q4 test computational claims; Q5 tests scoped transfer and use. Maintain separate costs for preparation, initialization, forecasts, validation, storage and recovery. A functional tutorial alone cannot establish ease of use, superiority or reduced effort.
5. **Keep the manuscript one coherent account.** Each section should answer a reader question and lead to the next: what study is needed, what defines it, how it runs, how it is tested, what happened, and what the evidence permits us to conclude. One manuscript lead integrates terminology and transitions across agents.

These are planning refinements. No hosting framework, provider, paid service, scientific default, additional forecast horizon or published-study recipe is adopted by this review.

## Agent handoff and review requirements

Each future manuscript assignment must identify its section, relevant R-number/citation key, the source passage or figure actually read, the intended organizational lesson, and our own evidence supporting the text. The editor checks that literature context, structural inspiration and project results remain distinguishable. Authors should read the cited primary material before finalizing claims.

For implementation assignments, connect the citation to existing requirements rather than creating a separate literature-driven backlog: WEB-01/02/03 use R1/R2/R8 for researcher access; WEB-04/05 and RF-003/008/012/014 use R4/R5/R6 for execution/artifacts; WEB-07 and RF-013/015 use R5/R7/R8 for evaluation. These are design inputs, not finish-to-start dependencies or permission to execute work.

## Review method and access limits

Searches targeted the journal title with NextGen/NGIAB, cloud workflows, reproducibility/containerization, performance evaluation and environmental user-centered/web design. Nearby citations were followed selectively. DOI, title, authors, journal, volume and pages/article number were checked against publisher-deposited Crossref records. Scientific/structural observations used publisher or author/institutional copies; search snippets were discovery aids rather than evidence of an entire paper's contents.

Publisher pages intermittently returned HTTP 403. R1 and R8 were inspected through institutional full-text copies; R2 and R3 through author uploads; R5 through an author-uploaded accepted manuscript, whose pagination can differ from the version of record. R9 remains abstract/metadata only. Source-specific records for R4, R6 and R7 are recorded in [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md). No article PDF is republished in this repository. The official journal author guide again returned HTTP 403 on 23 September, so exact submission formatting remains unverified. This does not prevent using published papers as writing examples.
