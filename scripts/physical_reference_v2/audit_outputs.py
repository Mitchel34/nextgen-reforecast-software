"""Seal complete serialized physical outputs before extracting any forecast lead.

No native model is imported or executed. NetCDF normalization is a separate,
bound read-only adapter; this auditor uses only Python's standard library.
"""
from __future__ import annotations

import argparse
import csv
from datetime import timedelta
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __package__:
    from . import common as c
else:
    import common as c
if __package__:
    from . import execute_stage as e
else:
    import execute_stage as e

CFE_FIELDS = ["RAIN_RATE", "GIUH_RUNOFF", "INFILTRATION_EXCESS", "DIRECT_RUNOFF",
              "NASH_LATERAL_RUNOFF", "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX",
              "Q_OUT", "POTENTIAL_ET", "ACTUAL_ET", "GW_STORAGE", "SOIL_STORAGE",
              "SOIL_STORAGE_CHANGE", "SURF_RUNOFF_SCHEME", "NWM_PONDED_DEPTH"]
HOUR = timedelta(hours=1)
ROUTE_FIELDS = ["feature_id", "valid_time_utc", "flow_m3_s", "velocity_m_s", "depth_m"]


def native_csv(path, origin, hours, fields, header=True):
    rows = csv.reader(io.StringIO(c.read(path).decode("ascii")), skipinitialspace=True)
    if header and next(rows, None) != ["Time Step", "Time", *fields]:
        raise c.ReferenceError("catchment output header differs from frozen schema")
    values = []
    for i, row in enumerate(rows):
        if i >= hours or len(row) != 2 + len(fields):
            raise c.ReferenceError("native output has unexpected row count or width")
        if row[0].strip() != str(i) or row[1].strip() != (origin + i * HOUR).strftime("%Y-%m-%d %H:%M:%S"):
            raise c.ReferenceError("native output step or interval-start clock differs")
        numeric = [c.number(x) for x in row[2:]]
        nonnegative = [fields.index("Q_OUT")] if "Q_OUT" in fields else ([0] if fields == ["flow_m3_s"] else [])
        if any(numeric[j] < 0 for j in nonnegative):
            raise c.ReferenceError("negative catchment runoff or nexus flow")
        values.append(numeric)
    if len(values) != hours:
        raise c.ReferenceError("native output clock is incomplete")
    return values


def routing_csv(path, origin, hours, feature_ids, interval_seconds=300):
    if interval_seconds not in (300, 3600):
        raise c.ReferenceError("unsupported routing output interval")
    step_delta = timedelta(seconds=interval_seconds)
    steps = hours * 3600 // interval_seconds
    rows = csv.reader(io.StringIO(c.read(path, 128 * 1024 * 1024).decode("ascii")))
    if next(rows, None) != ROUTE_FIELDS:
        raise c.ReferenceError("normalized routing header differs")
    result = {feature: [] for feature in feature_ids}
    seen = set()
    for row in rows:
        if len(row) != 5 or row[0] not in result:
            raise c.ReferenceError("routing row width or feature identity differs")
        feature = row[0]
        stamp = c.utc(row[1])
        step = int((stamp - origin).total_seconds() / interval_seconds)
        if stamp != origin + step * step_delta or not 1 <= step <= steps or (feature, step) in seen:
            raise c.ReferenceError("routing output clock is duplicate or outside the frozen axis")
        if step != len(result[feature]) + 1:
            raise c.ReferenceError("routing feature clock is out of order or incomplete")
        v = [c.number(x) for x in row[2:]]
        if any(x < 0 for x in v):
            raise c.ReferenceError("negative routed flow, velocity or depth")
        result[feature].append(v)
        seen.add((feature, step))
    if any(len(v) != steps for v in result.values()):
        raise c.ReferenceError("routing output omits a reach or interval")
    return result


def audit(protocol_path, case_id, output_root, routing_csv_path, normalization_path, execution_path, admission_path, destination):
    protocol = c.verify(c.load(protocol_path), "protocol_identity_sha256")
    if protocol["schema_version"] != "public-physical-reference-protocol/0.1":
        raise c.ReferenceError("unsupported independent reference protocol")
    cases = [case for case in protocol["cases"] if case["case_id"] == case_id]
    if len(cases) != 1:
        raise c.ReferenceError("case identity absent or ambiguous")
    case = cases[0]
    origin = c.utc(case["origin_time_utc"])
    hours = case["provider_hours"]
    output_root = Path(output_root)
    raw = c.inventory(output_root, protocol["bounds"]["job_output_bytes"])
    execution = c.verify(c.load(execution_path), "execution_identity_sha256")
    _, admitted = e.admission(protocol_path, admission_path, execution["admission_file_sha256"])
    if execution["schema_version"] != "physical-job-execution/0.1" or execution["case_id"] != case_id or execution["protocol_identity_sha256"] != protocol["protocol_identity_sha256"] or execution["raw_outputs"] != raw:
        raise c.ReferenceError("successful independent model execution does not bind these outputs")
    if execution["admission_identity_sha256"] != admitted["admission_identity_sha256"] or execution["runtime_identity_sha256"] != admitted["runtime_identity_sha256"] or execution["assembly_identity_sha256"] != admitted["assembly_identity_sha256"]:
        raise c.ReferenceError("execution admission/runtime/input identities differ")
    ledger = execution["reservation_ledger"]
    if not 1 <= len(ledger) <= 9 or [r["process_number"] for r in ledger] != list(range(1, len(ledger) + 1)):
        raise c.ReferenceError("execution ledger is incomplete or exceeds the model allowance")
    for row in ledger:
        c.verify(row, "reservation_identity_sha256")
    stages = execution["process_receipts"]
    if len(stages) != 2:
        raise c.ReferenceError("native and routing process evidence required")
    expected_input = c.seal({"case_id": case_id, "files": admitted["case_inputs"][case_id]}, "case_input_identity_sha256")["case_input_identity_sha256"]
    for receipt, stage in zip(stages, ("native", "routing")):
        c.verify(receipt, "process_receipt_identity_sha256")
        reservation = c.verify(receipt["reservation"], "reservation_identity_sha256")
        if receipt["returncode"] != 0 or receipt["termination_reason"] is not None or receipt.get("post_launch_verification_error") is not None or reservation["stage"] != stage or reservation["case_id"] != case_id or reservation["argv"] != e.argv_for(admitted, stage):
            raise c.ReferenceError("model receipt does not prove successful fixed stages")
        if stage == "native" and receipt.get("native_output_contract", {}).get("native_output_contract_complete") is not True:
            raise c.ReferenceError("native output completion evidence is absent")
        if reservation["admission_file_sha256"] != execution["admission_file_sha256"] or ledger[reservation["process_number"] - 1] != reservation or receipt["case_input_identity_sha256_after"] != expected_input or reservation["case_input_identity_sha256"] != expected_input:
            raise c.ReferenceError("model stage input, admission or global ledger binding differs")
    if stages[0]["reservation"]["process_number"] >= stages[1]["reservation"]["process_number"] or sum(s["elapsed_seconds"] for s in stages) > protocol["bounds"]["logical_job_wall_seconds"]:
        raise c.ReferenceError("model stages are unordered or exceed the combined job deadline")
    if stages[-1]["outputs_after"] != raw:
        raise c.ReferenceError("outputs differ from successful routed model receipt")
    native = output_root / "ngen"
    cats = protocol["catchment_ids"]
    nexuses = protocol["nexus_ids"]
    observed_cats = sorted(path.stem for path in native.glob("cat-*.csv"))
    if observed_cats != cats:
        raise c.ReferenceError("complete catchment file axis differs")
    observed_nex = sorted(path.name.removesuffix("_output.csv") for path in native.glob("nex-*_output.csv"))
    if observed_nex != nexuses:
        raise c.ReferenceError("complete nexus file axis differs")
    catchment = {cat: native_csv(native / (cat + ".csv"), origin, hours, CFE_FIELDS) for cat in cats}
    nexus = {nex: native_csv(native / (nex + "_output.csv"), origin, hours, ["flow_m3_s"], False) for nex in nexuses}
    norm = c.verify(c.load(normalization_path), "normalization_identity_sha256")
    if norm["schema_version"] != "routing-normalization/0.1" or norm["case_id"] != case_id or norm["protocol_identity_sha256"] != protocol["protocol_identity_sha256"]:
        raise c.ReferenceError("routing normalization identity differs")
    if norm["normalized_csv"] != c.binding(routing_csv_path):
        raise c.ReferenceError("normalized routing payload differs")
    sources = {row["path"]: row for row in raw}
    for row in norm["raw_sources"]:
        if sources.get(c.relative(row["path"])) != row:
            raise c.ReferenceError("routing raw NetCDF source binding differs")
    expected_raw = {p for p in sources if p.startswith("troute/") and p.endswith(".nc")}
    if expected_raw != {row["path"] for row in norm["raw_sources"]}:
        raise c.ReferenceError("normalization does not bind every raw routing NetCDF")
    route_dt = protocol["routing_output_interval_seconds"]
    routing = routing_csv(routing_csv_path, origin, hours, protocol["routing_feature_ids"], route_dt)
    if protocol["selected_routing_feature_id"] not in routing:
        raise c.ReferenceError("selected reach absent")
    arrays = {"schema_version": "physical-reference-arrays/0.1", "case_id": case_id,
              "origin_time_utc": case["origin_time_utc"], "physical_stop_time_utc_exclusive": case["stop_time_utc_exclusive"],
              "valid_time_utc": [(origin + (i + 1) * HOUR).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(hours)],
              "catchment_fields": CFE_FIELDS, "catchment_values": catchment,
              "catchment_variable_metadata": protocol["catchment_variable_metadata"],
              "nexus_fields": ["flow_m3_s"], "nexus_values": nexus,
              "nexus_variable_metadata": {"flow_m3_s": {"units": "m3 s-1", "semantics": "interval lateral discharge into nexus"}},
              "routing_fields": ["flow_m3_s", "velocity_m_s", "depth_m"],
              "routing_variable_metadata": {"flow_m3_s": {"units": "m3 s-1"}, "velocity_m_s": {"units": "m s-1"}, "depth_m": {"units": "m"}},
              "routing_valid_time_utc": [(origin + timedelta(seconds=(i + 1) * route_dt)).strftime("%Y-%m-%dT%H:%M:%SZ")
                                         for i in range(hours * 3600 // route_dt)],
              "routing_values": routing}
    destination = Path(destination)
    destination.mkdir(exist_ok=False, parents=True)
    arrays_path = destination / "arrays.json"
    c.write_new(arrays_path, arrays)
    leads = []
    if case["issue_time_utc"] is not None:
        issue = c.utc(case["issue_time_utc"])
        n_history = int((issue - origin) / HOUR)
        if hours - n_history != 18:
            raise c.ReferenceError("independent issue does not contain 18 leads")
        for lead in range(1, 19):
            i = n_history + lead - 1
            leads.append({"issue_time_utc": case["issue_time_utc"], "lead_hours": lead,
                          "valid_time_utc": arrays["valid_time_utc"][i],
                          "routing_feature_id": protocol["selected_routing_feature_id"],
                          "flow_m3_s": routing[protocol["selected_routing_feature_id"]][(i + 1) * 3600 // route_dt - 1][0],
                          "catchment_q_out_m": {cat: catchment[cat][i][CFE_FIELDS.index("Q_OUT")] for cat in cats}})
    c.write_new(destination / "lead_reference.json", leads)
    report = c.seal({"schema_version": "independent-physical-reference/0.1", "experiment_id": protocol["experiment_id"],
                     "fixture_id": protocol["fixture_id"], "case_id": case_id,
                     "protocol_identity_sha256": protocol["protocol_identity_sha256"],
                     "execution_identity_sha256": execution["execution_identity_sha256"],
                     "admission_identity_sha256": admitted["admission_identity_sha256"],
                     "runtime_identity_sha256": admitted["runtime_identity_sha256"],
                     "assembly_identity_sha256": admitted["assembly_identity_sha256"],
                     "case_input_identity_sha256": expected_input,
                     "raw_outputs": raw, "routing_normalization_identity_sha256": norm["normalization_identity_sha256"],
                     "arrays": c.binding(arrays_path), "lead_reference": c.binding(destination / "lead_reference.json"),
                     "complete_catchment_rows": len(cats) * hours, "complete_nexus_rows": len(nexuses) * hours,
                     "complete_routing_rows": len(routing) * hours * 3600 // route_dt, "forecast_lead_rows": len(leads),
                     "serialization_scope": "native precision17 CSV and pinned routing float32 NetCDF values; not complete land state",
                     "historical_e03_restored": False, "forecast_skill_validated": False,
                     "shared_history_or_checkpoint_qualified": False}, "reference_identity_sha256")
    c.write_new(destination / "REFERENCE.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "case_id", "output_root", "routing_csv", "normalization", "execution", "admission", "destination"):
        parser.add_argument(name)
    args = parser.parse_args()
    report = audit(args.protocol, args.case_id, args.output_root, args.routing_csv, args.normalization, args.execution, args.admission, args.destination)
    print(report["reference_identity_sha256"])


if __name__ == "__main__":
    main()
