"""Refuse incomplete native output even when Fortran STOP returns exit zero."""
from __future__ import annotations

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

FIELDS = ["RAIN_RATE", "GIUH_RUNOFF", "INFILTRATION_EXCESS", "DIRECT_RUNOFF",
          "NASH_LATERAL_RUNOFF", "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX",
          "Q_OUT", "POTENTIAL_ET", "ACTUAL_ET", "GW_STORAGE", "SOIL_STORAGE",
          "SOIL_STORAGE_CHANGE", "SURF_RUNOFF_SCHEME", "NWM_PONDED_DEPTH"]


def check_series(path, origin, hours, fields, header):
    reader = csv.reader(io.StringIO(c.read(path).decode("ascii")), skipinitialspace=True)
    if header and next(reader, None) != ["Time Step", "Time", *fields]:
        raise c.ReferenceError("native preflight output header differs")
    count = 0
    for i, row in enumerate(reader):
        if i >= hours or len(row) != len(fields) + 2 or row[0].strip() != str(i):
            raise c.ReferenceError("native preflight output row count, width or step differs")
        if row[1].strip() != (origin + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S"):
            raise c.ReferenceError("native preflight interval-start clock differs")
        values = [c.number(v) for v in row[2:]]
        runoff = values[fields.index("Q_OUT")] if header else values[0]
        if runoff < 0:
            raise c.ReferenceError("native preflight runoff/nexus flow is negative")
        count += 1
    if count != hours:
        raise c.ReferenceError("native preflight output is incomplete; zero exit is insufficient")


def validate(protocol, case_id, output_root, stdout_path=None, stderr_path=None):
    cases = [r for r in protocol["cases"] if r["case_id"] == case_id]
    if len(cases) != 1:
        raise c.ReferenceError("native preflight unknown or duplicate case")
    case = cases[0]
    hours = case["provider_hours"]
    origin = c.utc(case["origin_time_utc"])
    root = Path(output_root) / "ngen"
    cats = protocol["catchment_ids"]
    nexuses = protocol["nexus_ids"]
    actual_cats = sorted(p.stem for p in root.glob("cat-*.csv"))
    actual_nexus = sorted(p.name.removesuffix("_output.csv") for p in root.glob("nex-*_output.csv"))
    if actual_cats != cats or actual_nexus != nexuses:
        raise c.ReferenceError("native preflight full catchment/nexus file axis differs")
    for path in (stdout_path, stderr_path):
        if path is not None and b"FATAL ERROR" in c.read(path, 128 * 1024 * 1024).upper():
            raise c.ReferenceError("native log contains fatal error despite possible zero exit")
    for cat in cats:
        check_series(root / (cat + ".csv"), origin, hours, FIELDS, True)
    for nexus in nexuses:
        check_series(root / (nexus + "_output.csv"), origin, hours, ["flow_m3_s"], False)
    return {"native_output_contract_complete": True, "case_id": case_id,
            "complete_catchment_rows": len(cats) * hours, "complete_nexus_rows": len(nexuses) * hours,
            "checked_catchment_variables": FIELDS,
            "land_and_nexus_files": [{"path": p.relative_to(Path(output_root)).as_posix(), **c.binding(p)}
                                     for p in sorted(root.glob("*.csv"))]}
