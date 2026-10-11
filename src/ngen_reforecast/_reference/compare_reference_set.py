"""Bind three independently executed references and test their antecedent prefix.

Prefix agreement is an execution consistency check, not forecast skill, spin-up
convergence, restart equivalence or a complete land checkpoint.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __package__:
    from . import common as c
else:
    import common as c


def prefix_differences(history, replay, history_hours, routing_interval_seconds):
    differences = []
    counts = {}
    axes = [("catchment_values", history_hours), ("nexus_values", history_hours),
            ("routing_values", history_hours * 3600 // routing_interval_seconds)]
    for name, hours in axes:
        if set(history[name]) != set(replay[name]):
            raise c.ReferenceError("reference entity axes differ")
        count = 0
        for feature in sorted(history[name]):
            left, right = history[name][feature], replay[name][feature]
            if len(left) < hours or len(right) < hours:
                raise c.ReferenceError("reference antecedent prefix is incomplete")
            for i in range(hours):
                if left[i] != right[i]:
                    count += 1
                    if len(differences) < 24:
                        differences.append({"axis": name, "feature_id": feature, "step_index": i,
                                            "history_values": left[i], "independent_replay_values": right[i]})
        counts[name] = count
    return counts, differences


def compare(protocol_path, reference_roots, destination):
    protocol = c.verify(c.load(protocol_path), "protocol_identity_sha256")
    cases = {r["case_id"]: r for r in protocol["cases"]}
    loaded = {}
    bindings = []
    for root in map(Path, reference_roots):
        report = c.verify(c.load(root / "REFERENCE.json"), "reference_identity_sha256")
        case = report["case_id"]
        if case not in cases or case in loaded or report["protocol_identity_sha256"] != protocol["protocol_identity_sha256"]:
            raise c.ReferenceError("reference case/protocol identity absent, duplicate or foreign")
        if c.binding(root / "arrays.json", 128 * 1024 * 1024) != report["arrays"] or c.binding(root / "lead_reference.json") != report["lead_reference"]:
            raise c.ReferenceError("complete reference arrays or lead extraction changed")
        arrays = c.load(root / "arrays.json", 128 * 1024 * 1024)
        leads = c.load(root / "lead_reference.json")
        loaded[case] = (report, arrays, leads)
        bindings.append({"case_id": case, "reference_identity_sha256": report["reference_identity_sha256"],
                         "reference_report": c.binding(root / "REFERENCE.json"),
                         "arrays": report["arrays"], "lead_reference": report["lead_reference"]})
    if set(loaded) != set(cases) or len(cases) != 3:
        raise c.ReferenceError("one history and both independent issue references required")
    history_cases = [r["case_id"] for r in protocol["cases"] if r["issue_time_utc"] is None]
    if len(history_cases) != 1:
        raise c.ReferenceError("unique antecedent history reference required")
    history_id = history_cases[0]
    history = loaded[history_id][1]
    checks = []
    leads = []
    for case in protocol["cases"]:
        if case["issue_time_utc"] is None:
            continue
        report, replay, extracted = loaded[case["case_id"]]
        n = int((c.utc(case["issue_time_utc"]) - c.utc(case["origin_time_utc"])).total_seconds() / 3600)
        counts, examples = prefix_differences(history, replay, n, protocol["routing_output_interval_seconds"])
        if len(extracted) != 18 or [row["lead_hours"] for row in extracted] != list(range(1, 19)):
            raise c.ReferenceError("one complete 18-lead forecast extraction required per issue")
        checks.append({"case_id": case["case_id"], "antecedent_hours": n,
                       "antecedent_routing_steps": n * 3600 // protocol["routing_output_interval_seconds"],
                       "serialized_outputs_exactly_equal": not any(counts.values()),
                       "differing_rows": counts, "first_differences": examples})
        leads.extend(extracted)
    destination = Path(destination)
    destination.mkdir(exist_ok=False, parents=True)
    c.write_new(destination / "lead_reference.json", leads)
    result = c.seal({"schema_version": "independent-physical-reference-set/0.1",
                     "experiment_id": protocol["experiment_id"], "fixture_id": protocol["fixture_id"],
                     "protocol_identity_sha256": protocol["protocol_identity_sha256"],
                     "references": sorted(bindings, key=lambda r: r["case_id"]),
                     "independent_reference_count": 3, "complete_issue_lead_rows": len(leads),
                     "prefix_consistency": checks, "all_antecedent_prefixes_equal": all(r["serialized_outputs_exactly_equal"] for r in checks),
                     "lead_reference": c.binding(destination / "lead_reference.json"),
                     "comparison_semantics": "exact serialized-output equality before the weather switch; no tolerance fitted to results",
                     "shared_history_executed": False, "checkpoint_qualified": False,
                     "forecast_skill_validated": False, "spinup_convergence_validated": False,
                     "historical_e03_restored": False}, "reference_set_identity_sha256")
    c.write_new(destination / "REFERENCE_SET.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("protocol")
    p.add_argument("destination")
    p.add_argument("reference_roots", nargs=3)
    a = p.parse_args()
    print(compare(a.protocol, a.reference_roots, a.destination)["reference_set_identity_sha256"])


if __name__ == "__main__":
    main()
