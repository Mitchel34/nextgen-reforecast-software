# Native runtime work area

This directory contains a historical runtime identity and the work needed to make a reproducible public native runtime. It contains no inherited implementation, binaries, image layers or hydrologic data. The Python package implements offline inspection; it does not build or execute NextGen.

The supported reference is `profiles/nextgen-arm64-v3.json`: Linux ARM64, the V3 day-custody overlay using the `shared-history-v2` protocol, SLOTH/NoahOWP/CFE and channel-only t-route. Its immutable metadata binds the exact framework, source preimages, modified files, image, executable, Fortran BMI middleware and candidate Watauga example. Changing JSON formatting does not change identity; changing a pin requires a reviewed implementation update.

- [Build recipe](BUILD_RECIPE.md): pinned reference, incomplete dependency closure and bounded future build stages. No build has been executed for this repository.
- [Asset closure](ASSET_CLOSURE.json): all 181 candidate fixture members, historical residency, known hashes, and 17 native/source entries. These are portable staging paths; they are not source-cache paths or assertions that the files are present here.
- [Qualification procedure](../docs/RUNTIME_QUALIFICATION.md): what the current doctor checks and the evidence required for a qualified release.

All actual asset reads require an explicit local root. The inspector neither discovers the original research directories nor restores iCloud placeholders. It rejects symbolic links, dataless entries, path traversal and nonregular files. No reported path identifies a user's local source cache.

The historical fixture inventory has 132 dataless members. A historical binding supplies the missing `CONTRACT.json` hash; 131 other member hashes remain unknown in the public dossier. Restoring files or calculating new hashes does not by itself establish their intended identity or redistribution rights. The sealed contract and preparation manifests must resolve those identities before use.

The original research roots, the six design files and the feasibility dossier remain read-only sources. Ordinary inspection and test output belongs in this repository's ignored local directories.
