"""Create a distinct diagnostic fixture with pinned, supported Noah options.

The failed v1 configuration remains sealed. This adapter changes exactly two
Noah model options, preserves all other input bytes, and initializes no model.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_domain as domain
from ngen_reforecast.campaign import _asset_path, _pairs, _nonfinite

NOAH_ARCHIVE = "NoahOWP-0abb891b48b043cc626c4e4bbd0efe54ad357fe1.tar.gz"
NOAH_ARCHIVE_SHA256 = "59f2c8cbba8f0b4b638e21e29c6a2ec2ea01d126ccbe12a71efc4a3d1de4f9d0"
RANGES = {
    "precip_phase_option": (1, 7), "runoff_option": (1, 8), "drainage_option": (1, 8),
    "frozen_soil_option": (1, 2), "dynamic_vic_option": (1, 3), "dynamic_veg_option": (1, 9),
    "snow_albedo_option": (1, 2), "radiative_transfer_option": (1, 3), "sfc_drag_coeff_option": (1, 2),
    "canopy_stom_resist_option": (1, 2), "snowsoil_temp_time_option": (1, 3),
    "soil_temp_boundary_option": (1, 2), "supercooled_water_option": (1, 2),
    "stomatal_resistance_option": (1, 3), "evap_srfc_resistance_option": (1, 4),
    "subsurface_option": (1, 3), "crop_model_option": (0, 0),
}
REPLACEMENTS = {"stomatal_resistance_option": (4, 1), "evap_srfc_resistance_option": (5, 1)}


def option_values(raw):
    """Parse the closed, integer-only diagnostic model_options namelist."""
    text = "\n".join(line.split("!", 1)[0] for line in raw.decode("ascii").splitlines())
    groups = re.findall(r"(?ms)^\s*&model_options\s*$(.*?)^\s*/\s*$", text)
    if len(groups) != 1:
        raise domain.PreparationError("one Noah model_options group required")
    options = {}
    for line in groups[0].splitlines():
        line = line.strip().rstrip(",").strip()
        if not line:
            continue
        match = re.fullmatch(r"([a-z_]+)\s*=\s*([+-]?\d+)", line, flags=re.ASCII)
        if not match or match[1] in options or match[1] not in RANGES:
            raise domain.PreparationError("malformed, duplicate or unknown Noah model option")
        options[match[1]] = int(match[2])
    if set(options) != set(RANGES):
        raise domain.PreparationError("complete pinned Noah model option set required")
    return options


def validate_noah_options(raw):
    options = option_values(raw)
    for name, value in options.items():
        lower, upper = RANGES[name]
        if not lower <= value <= upper:
            raise domain.PreparationError(f"unsupported pinned Noah option: {name}={value}")
    if options["subsurface_option"] == 3:
        raise domain.PreparationError("pinned Noah subsurface option 3 is documented unimplemented")
    return options


def default_source(runtime_root):
    archive_path = Path(runtime_root) / "downloads" / NOAH_ARCHIVE
    raw = domain.bounded_bytes(archive_path, 2 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != NOAH_ARCHIVE_SHA256:
        raise domain.PreparationError("pinned Noah archive differs")
    sources, bindings = {}, []
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for suffix in ("src/NamelistRead.f90", "src/OptionsType.f90", "run/namelist.input"):
            matches = [member for member in archive.getmembers() if member.name.endswith("/" + suffix)]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > 1024 * 1024:
                raise domain.PreparationError("pinned Noah option source member differs")
            payload = archive.extractfile(matches[0]).read()
            sources[suffix] = payload
            bindings.append({"archive": NOAH_ARCHIVE, "archive_sha256": NOAH_ARCHIVE_SHA256,
                             "member": matches[0].name, **domain.binding(archive_path, payload)})
    parsed = re.findall(r"is_within_bound\(\s*([a-z_]+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", sources["src/NamelistRead.f90"].decode())
    guards = {name: (int(lower), int(upper)) for name, lower, upper in parsed}
    if len(parsed) != 16 or guards != {name: value for name, value in RANGES.items() if name != "crop_model_option"}:
        raise domain.PreparationError("pinned Noah model option range guards differ")
    defaults = validate_noah_options(sources["run/namelist.input"])
    if any(defaults[name] != new for name, (_, new) in REPLACEMENTS.items()):
        raise domain.PreparationError("documented Noah compatibility default differs")
    if b"NO CROP MODEL CURRENTLY SUPPORTED" not in sources["src/OptionsType.f90"] or b"NOT IMPLEMENTED YET" not in sources["src/OptionsType.f90"]:
        raise domain.PreparationError("pinned implementation exclusions differ")
    return bindings, defaults


def repair_options(raw):
    old = option_values(raw)
    if any(old[name] != previous for name, (previous, _) in REPLACEMENTS.items()):
        raise domain.PreparationError("expected original incompatible Noah options differ")
    text = raw.decode("ascii")
    for name, (previous, new) in REPLACEMENTS.items():
        pattern = rf"(?m)^(\s*{name}\s*=\s*){previous}(\s*(?:!.*)?)$"
        text, count = re.subn(pattern, lambda m: m[1] + str(new) + m[2], text)
        if count != 1:
            raise domain.PreparationError("one exact Noah option assignment required")
    result = text.encode("ascii")
    new = validate_noah_options(result)
    if any(old[name] != value for name, value in new.items() if name not in REPLACEMENTS):
        raise domain.PreparationError("unexpected scientific model option change")
    return result, old, new


def sealed_input(root):
    path = Path(root) / "ADMISSION.json"
    report = json.loads(domain.bounded_bytes(path, 8 * 1024 * 1024), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    expected = report.pop("admission_identity_sha256")
    if hashlib.sha256(domain.canonical(report)).hexdigest() != expected:
        raise domain.PreparationError("parent admission identity differs")
    report["admission_identity_sha256"] = expected
    if report["schema_version"] != "public-diagnostic-input-admission/0.1" or report["fixture_id"] != "watauga-public-rebuild-v1":
        raise domain.PreparationError("sealed v1 diagnostic parent required")
    files, total = {}, 0
    if not 1 <= len(report["files"]) <= 512:
        raise domain.PreparationError("parent file bound exceeded")
    for asset in report["files"]:
        rel = _asset_path(asset["path"], "parent asset")
        if rel in files or not isinstance(asset["bytes"], int) or asset["bytes"] < 0:
            raise domain.PreparationError("invalid parent asset declaration")
        total += asset["bytes"]
        if total > 32 * 1024 * 1024:
            raise domain.PreparationError("parent input byte bound exceeded")
        raw = domain.bounded_bytes(Path(root) / rel, min(asset["bytes"], 2 * 1024 * 1024))
        if domain.binding(Path(root) / rel, raw) != {key: asset[key] for key in ("bytes", "sha256")}:
            raise domain.PreparationError("parent input payload differs")
        files[rel] = raw
    return report, files


def repair(parent_root, runtime_root, recipe_path, destination):
    parent, files = sealed_input(parent_root)
    source_bindings, defaults = default_source(runtime_root)
    recipe_raw = domain.bounded_bytes(recipe_path, 1024 * 1024)
    recipe = json.loads(recipe_raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    if recipe["fixture_id"] != "watauga-public-rebuild-v2" or recipe["parent_fixture_id"] != parent["fixture_id"] or recipe["parent_admission_identity_sha256"] != parent["admission_identity_sha256"]:
        raise domain.PreparationError("new scientific recipe parent identity differs")
    if recipe["domain"]["catchment_ids"] != parent["catchment_ids"]:
        raise domain.PreparationError("new scientific recipe catchment axis differs")
    if recipe["configuration"]["noah_model_option_changes"] != {name: {"previous": previous, "new": new} for name, (previous, new) in REPLACEMENTS.items()}:
        raise domain.PreparationError("new scientific recipe options differ")
    changes, options = [], None
    for job in parent["jobs"]:
        for cat in parent["catchment_ids"]:
            rel = job["path"] + f"/config/cat_config/NOAH-OWP-M/{cat}.input"
            previous = files[rel]
            files[rel], before, after = repair_options(previous)
            if options is not None and after != options:
                raise domain.PreparationError("Noah model options differ across catchments/jobs")
            options = after
            changes.append({"path": rel, "previous": domain.binding(Path(parent_root) / rel, previous),
                            "new": domain.binding(Path(parent_root) / rel, files[rel]),
                            "option_changes": {name: {"previous": before[name], "new": after[name]} for name in REPLACEMENTS}})
    if len(changes) != len(parent["jobs"]) * len(parent["catchment_ids"]):
        raise domain.PreparationError("Noah config axis incomplete")
    destination = domain.fresh_directory(destination, [Path(parent_root), Path(runtime_root)])
    for rel, raw in files.items():
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(raw)
    for job in parent["jobs"]:
        for name in ("outputs/ngen", "outputs/troute"):
            (destination / job["path"] / name).mkdir(parents=True)
    after_parent, _ = sealed_input(parent_root)
    after_sources, after_defaults = default_source(runtime_root)
    if after_parent != parent or after_sources != source_bindings or after_defaults != defaults:
        raise domain.PreparationError("parent or pinned sources changed during preparation")
    result = {**parent, "schema_version": "public-diagnostic-input-admission/0.2",
              "fixture_id": recipe["fixture_id"], "parent_fixture_id": parent["fixture_id"],
              "parent_admission_identity_sha256": parent["admission_identity_sha256"],
              "recipe": domain.binding(recipe_path, recipe_raw), "adapter": domain.binding(Path(__file__)),
              "source_contracts": parent["source_contracts"] + source_bindings,
              "files": [{"path": rel, **domain.binding(destination / rel, raw)} for rel, raw in sorted(files.items())],
              "scientific_configuration_changes": changes, "noah_option_values": options,
              "noah_option_guard_count": 16, "noah_model_option_fields_checked": 17,
              "noah_implementation_exclusions": {"crop_model_option": "only0 supported", "subsurface_option": "3 unimplemented"},
              "documented_default_options": defaults,
              "noah_options_compatible_with_pinned_source": True,
              "physical_reference_validated": False, "native_model_invocations": 0,
              "release_scientifically_qualified": False}
    result.pop("admission_identity_sha256")
    result["scientific_configuration_identity_sha256"] = hashlib.sha256(domain.canonical({
        "fixture_id": recipe["fixture_id"], "noah_options": options,
        "config_files": [asset for asset in result["files"] if "/cat_config/" in asset["path"]]})).hexdigest()
    result["admission_identity_sha256"] = hashlib.sha256(domain.canonical(result)).hexdigest()
    (destination / "ADMISSION.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent_root", "runtime_root", "recipe_path", "destination"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = repair(args.parent_root, args.runtime_root, args.recipe_path, args.destination)
    print(json.dumps({"fixture_id": result["fixture_id"], "admission_identity_sha256": result["admission_identity_sha256"],
                      "scientific_configuration_identity_sha256": result["scientific_configuration_identity_sha256"], "native_model_invocations": 0}))


if __name__ == "__main__":
    main()
