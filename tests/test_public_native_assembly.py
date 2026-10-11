"""Native layout and clock tests use synthetic bytes and invoke no models."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import csv
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
helper_spec = importlib.util.spec_from_file_location("public_domain_test_helper", ROOT / "tests/test_public_domain.py")
domain_tests = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(domain_tests)
spec = importlib.util.spec_from_file_location("public_native_assembler", ROOT / "scripts/public_fixture/assemble_native.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


class PublicNativeAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.helper = domain_tests.PublicDomainTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.base = self.helper.base
        self.origin = datetime(2021, 12, 1, tzinfo=timezone.utc)

    def csv_bytes(self, begin, hours, value="1"):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(assembly.FIELDS)
        writer.writerows([(begin + i * assembly.HOUR).strftime("%Y-%m-%d %H:%M:%S"), *([value] * 8)] for i in range(hours))
        return output.getvalue().encode()

    def test_pinned_native_end_is_last_provider_label(self):
        end, count = assembly.native_end_time(self.origin, self.origin + 18 * assembly.HOUR)
        self.assertEqual((end, count), ("2021-12-01 17:00:00", 18))
        self.assertEqual(int((datetime.strptime(end, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) - self.origin) / assembly.HOUR) + 1, 18)

    def test_canonical_decoded_timestamp_is_refused_for_native_provider(self):
        raw = self.csv_bytes(self.origin, 2).replace(b"2021-12-01 00:00:00", b"2021-12-01T00:00:00Z")
        with self.assertRaises(assembly.domain.PreparationError):
            assembly.native_rows(raw, self.origin, self.origin + 2 * assembly.HOUR)

    def test_missing_extra_duplicate_and_nonfinite_provider_rows(self):
        stop = self.origin + 2 * assembly.HOUR
        good = self.csv_bytes(self.origin, 2)
        variants = [self.csv_bytes(self.origin, 1), self.csv_bytes(self.origin, 3),
                    good.replace(b"2021-12-01 01:00:00", b"2021-12-01 00:00:00"),
                    self.csv_bytes(self.origin, 2, "nan")]
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(assembly.domain.PreparationError):
                assembly.native_rows(raw, self.origin, stop)

    def setup_bundle(self):
        source = self.helper.synthetic_source()
        templates = self.helper.synthetic_templates()
        edits = {
            "noah": '&timing\nstartdate="{start_datetime}"\nenddate="{end_datetime}"\nlat={lat}\nlon={lon}\n/\n',
            "realization": '{"global":{"forcing":{"provider":"NetCDF","path":"pending.nc"}},"time":{}}',
        }
        for name, content in edits.items():
            (templates / assembly.domain.TEMPLATES[name]).write_text(content)
        receipt = json.loads((templates / "SOURCE_RECEIPT.json").read_text())
        for row in receipt["files"]:
            row.update(assembly.domain.binding(templates / row["path"]))
        (templates / "SOURCE_RECEIPT.json").write_text(json.dumps(receipt))
        dr = self.helper.generate(source, templates)
        domain = self.base / "fixture"
        weather = self.base / "weather"
        weather.mkdir()
        payloads = []
        issues = [self.origin + 3 * assembly.HOUR, self.origin + 6 * assembly.HOUR]
        for rel, raw in [("provider/history/cat-1.csv", self.csv_bytes(self.origin, 24))] + [
            (f"provider/forecast/{issue.strftime('%Y%m%dT%H00Z')}/cat-1.csv", self.csv_bytes(issue, 18, "2")) for issue in issues]:
            target = weather / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            identity = assembly.domain.binding(target)
            payloads.append({"path": rel, "size_bytes": identity["bytes"], "sha256": identity["sha256"]})
        wr = {"schema_version": "public-forcing-preparation/0.1", "historical_benchmark_restored": False, "content_complete": True, "catchment_ids": ["cat-1"],
              "domain_sha256": dr["geometry"]["sha256"], "origin_time_utc": "2021-12-01T00:00:00Z",
              "stop_time_utc_exclusive": "2021-12-02T00:00:00Z",
              "issue_times_utc": [issue.strftime("%Y-%m-%dT%H:00:00Z") for issue in issues], "payloads": payloads}
        wr["preparation_identity_sha256"] = hashlib.sha256(assembly.domain.canonical(wr)).hexdigest()
        (weather / "PREPARATION.json").write_text(json.dumps(wr))
        source_root = self.base / "native-source"
        names = ["include/forcing/CsvPerFeatureForcingProvider.hpp", "include/forcing/AorcForcing.hpp",
                 "include/realizations/catchment/Formulation_Constructors.hpp",
                 "include/realizations/catchment/Formulation_Manager.hpp", "include/simulation_time/Simulation_Time.hpp", "src/NGen.cpp"]
        records = []
        for name in names:
            target = source_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"// Synthetic test bytes, not public source attestation.\n")
            records.append({"path": name, **assembly.domain.binding(target)})
        (source_root / "SOURCE_RECEIPT.json").write_text(json.dumps({"commit": assembly.REVISION, "files": records}))
        return domain, weather, templates, source_root / "SOURCE_RECEIPT.json"

    def test_serial_assembly_switches_weather_once_and_replays_from_origin(self):
        domain, weather, templates, receipt = self.setup_bundle()
        result = assembly.assemble(domain, weather, templates, self.base / "native-jobs", receipt)
        self.assertEqual([job["provider_hours_per_catchment"] for job in result["jobs"]], [24, 21, 24])
        self.assertEqual([job["history_hours"] for job in result["jobs"]], [24, 3, 6])
        self.assertFalse(result["execution_ready"])
        self.assertFalse(result["shared_history_execution_qualified"])
        folder = self.base / "native-jobs/serial-20211201T0300Z"
        rows = list(csv.reader(io.StringIO((folder / "forcings/cat-1.csv").read_text())))[1:]
        self.assertEqual([row[1] for row in rows], ["1"] * 3 + ["2"] * 18)
        realization = json.loads((folder / "config/realization.json").read_text())
        self.assertEqual(realization["global"]["forcing"]["provider"], "CsvPerFeature")
        self.assertEqual(realization["time"]["end_time"], "2021-12-01 20:00:00")
        self.assertIn('enddate="202112012100"', (folder / "config/cat_config/NOAH-OWP-M/cat-1.input").read_text())
        self.assertIn("nts: 252", (folder / "config/troute.yaml").read_text())

    def test_changed_weather_and_tampered_report_fail_before_writes(self):
        domain, weather, templates, receipt = self.setup_bundle()
        path = weather / "provider/history/cat-1.csv"
        path.write_bytes(self.csv_bytes(self.origin, 24, "9"))
        with self.assertRaises(assembly.domain.PreparationError):
            assembly.assemble(domain, weather, templates, self.base / "native-jobs", receipt)
        self.assertFalse((self.base / "native-jobs").exists())
        report = weather / "PREPARATION.json"
        parsed = json.loads(report.read_text())
        parsed["catchment_ids"] = ["cat-9"]
        report.write_text(json.dumps(parsed))
        with self.assertRaises(assembly.domain.PreparationError):
            assembly.assemble(domain, weather, templates, self.base / "native-jobs", receipt)

    def test_noah_assignment_is_not_changed_by_unbound_guess(self):
        with self.assertRaises(assembly.domain.PreparationError):
            assembly.rewrite_noah_end(b'enddate="202201010000"\n', self.origin, self.origin + assembly.HOUR)


if __name__ == "__main__":
    unittest.main()
