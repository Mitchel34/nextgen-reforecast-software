"""Adversarial synthetic admission checks; these invoke no physical models."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("public_native_qualification", ROOT / "scripts/public_fixture/qualify_native.py")
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)


class PublicNativeQualificationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="qualification-test-", dir=ROOT / ".local")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.cats = ["cat-1", "cat-2", "cat-3"]

    def geometry(self, path):
        with sqlite3.connect(path) as c:
            c.execute("CREATE TABLE divides (divide_id TEXT, areasqkm REAL)")
            c.execute("CREATE TABLE flowpaths (id TEXT, divide_id TEXT, toid TEXT)")
            c.execute('CREATE TABLE "flowpath-attributes" (link TEXT, Length_m REAL, n REAL, nCC REAL, BtmWdth REAL, TopWdth REAL, TopWdthCC REAL, ChSlp REAL, So REAL)')
            for i, downstream in [(1, 3), (2, 3), (3, 4)]:
                c.execute("INSERT INTO divides VALUES (?,?)", (f"cat-{i}", float(i)))
                c.execute("INSERT INTO flowpaths VALUES (?,?,?)", (f"wb-{i}", f"cat-{i}", f"nex-{downstream}"))
                c.execute('INSERT INTO "flowpath-attributes" VALUES (?,?,?,?,?,?,?,?,?)',
                          (f"wb-{i}", 100.0, .03, .06, 2.0, 3.0, 6.0, 1.0, .01))

    def test_own_catchment_mapping_retains_confluence_tributaries_and_cut(self):
        path = self.base / "geometry.gpkg"
        self.geometry(path)
        result = admission.routing_crosswalk(path, self.cats, "wb-3")
        self.assertEqual(result["shared_confluence_nexuses"], {"nex-3": 2})
        self.assertEqual([result["catchments"][cat]["numeric_routing_id"] for cat in self.cats], [1, 2, 3])
        self.assertEqual(result["selected_outlet"]["reach_id"], "wb-3")
        self.assertFalse(result["nexus_aggregate_lateral_assignment_admitted"])

    def test_wrong_reach_missing_parameter_and_wrong_outlet_refused(self):
        for kind in ("wrong-reach", "missing-parameter", "wrong-outlet"):
            with self.subTest(kind=kind):
                path = self.base / (kind + ".gpkg")
                self.geometry(path)
                with sqlite3.connect(path) as c:
                    if kind == "wrong-reach":
                        c.execute("UPDATE flowpaths SET divide_id='cat-2' WHERE id='wb-1'")
                    elif kind == "missing-parameter":
                        c.execute('DELETE FROM "flowpath-attributes" WHERE link="wb-1"')
                    else:
                        c.execute("UPDATE flowpaths SET toid='nex-9' WHERE id='wb-1'")
                with self.assertRaises(admission.domain.PreparationError):
                    admission.routing_crosswalk(path, self.cats, "wb-3")

    def test_nonpositive_channel_parameter_refused(self):
        path = self.base / "geometry.gpkg"
        self.geometry(path)
        with sqlite3.connect(path) as c:
            c.execute('UPDATE "flowpath-attributes" SET n=0 WHERE link="wb-2"')
        with self.assertRaises(admission.domain.PreparationError):
            admission.routing_crosswalk(path, self.cats, "wb-3")

    def test_noah_inclusive_endpoint_is_one_exact_assignment(self):
        stop = datetime(2022, 1, 2, 18, tzinfo=timezone.utc)
        raw = b'&timing\n enddate = "202201021800"\n/\n'
        self.assertIn(b'"202201021700"', admission.noah_last_label(raw, stop, stop - timedelta(hours=1)))
        for bad in (raw.replace(b"1800", b"1600"), raw + raw):
            with self.assertRaises(admission.domain.PreparationError):
                admission.noah_last_label(bad, stop, stop - timedelta(hours=1))

    def route_bytes(self):
        return b'        qlat_file_pattern_filter: "nex-*"\n        stream_output_type: ".nc"\n        stream_output_internal_frequency: 60\n'

    def test_routing_reads_named_catchment_flux_and_retains_every_step(self):
        text = admission.route_catchment_input(self.route_bytes()).decode()
        self.assertIn('qlat_file_pattern_filter: "cat-*"', text)
        self.assertIn('qlat_file_value_col: "Q_OUT"', text)
        self.assertIn('stream_output_type: ".nc"', text)
        self.assertIn('stream_output_internal_frequency: 5', text)
        for raw in (self.route_bytes().replace(b"nex-*", b"other-*"), self.route_bytes() + self.route_bytes()):
            with self.assertRaises(admission.domain.PreparationError):
                admission.route_catchment_input(raw)

    def setup_assembly(self):
        root = self.base / "source"
        root.mkdir()
        origin = datetime(2021, 12, 1, tzinfo=timezone.utc)
        jobs = []
        for name, count in [("history", 786), ("issue-a", 785), ("issue-b", 786)]:
            stop = origin + count * timedelta(hours=1)
            config = root / name / "config"
            config.mkdir(parents=True)
            self.geometry(config / "public-watauga.gpkg")
            for cat in self.cats:
                cfe = config / f"cat_config/CFE/{cat}.ini"
                noah = config / f"cat_config/NOAH-OWP-M/{cat}.input"
                cfe.parent.mkdir(parents=True, exist_ok=True)
                noah.parent.mkdir(parents=True, exist_ok=True)
                cfe.write_bytes(b"soil_params.slop=0.043414704501628876[m/m]\n")
                noah.write_text(f'enddate="{stop.strftime("%Y%m%d%H%M")}"\n')
            realization = {"global": {"formulations": [{"params": {}}]}, "routing": {"old": "embedded"},
                           "time": {"start_time": origin.strftime("%Y-%m-%d %H:%M:%S"),
                                    "end_time": (stop - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                                    "output_interval": 3600}}
            (config / "realization.json").write_text(json.dumps(realization))
            (config / "troute.yaml").write_bytes(self.route_bytes())
            jobs.append({"path": name, "stop_time_utc_exclusive": stop.strftime("%Y-%m-%dT%H:00:00Z"),
                         "origin_time_utc": "2021-12-01T00:00:00Z", "provider_hours_per_catchment": count})
        report = {"schema_version": "public-native-input-assembly/0.1", "new_fixture": True,
                  "catchment_ids": self.cats, "jobs": jobs,
                  "files": [{"path": str(p.relative_to(root)), **admission.domain.binding(p)} for p in sorted(root.rglob("*")) if p.is_file()]}
        report["assembly_identity_sha256"] = hashlib.sha256(admission.domain.canonical(report)).hexdigest()
        (root / "ASSEMBLY.json").write_text(json.dumps(report))
        recipe = {"fixture_id": "watauga-public-rebuild-v1", "domain": {"catchment_ids": self.cats,
                  "geometry_sha256": admission.domain.binding(root / "history/config/public-watauga.gpkg")["sha256"]},
                  "gauge": {"routed_flowpath_id": "wb-3"}}
        path = self.base / "recipe.json"
        path.write_text(json.dumps(recipe))
        return root, path

    def test_corrupt_asset_and_report_are_refused(self):
        root, _ = self.setup_assembly()
        target = root / "history/config/cat_config/CFE/cat-1.ini"
        target.write_text("corrupt")
        with self.assertRaises(admission.domain.PreparationError):
            admission.read_assembly(root)
        doc = json.loads((root / "ASSEMBLY.json").read_text())
        doc["new_fixture"] = False
        (root / "ASSEMBLY.json").write_text(json.dumps(doc))
        with self.assertRaises(admission.domain.PreparationError):
            admission.read_assembly(root)

    def test_component_source_archive_hash_change_is_refused(self):
        runtime = self.base / "runtime"
        (runtime / "downloads").mkdir(parents=True)
        first = next(iter(admission.ARCHIVES))
        (runtime / "downloads" / first).write_bytes(b"unbound archive")
        with self.assertRaises(admission.domain.PreparationError):
            admission.contract_sources(runtime)

    def test_new_revision_preserves_source_and_candidate_parameters(self):
        root, recipe = self.setup_assembly()
        before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        with patch.object(admission, "contract_sources", return_value=([{"synthetic": True}], {})):
            result = admission.qualify(root, self.base / "runtime", recipe, self.base / "new")
        self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()})
        self.assertTrue(result["input_contract_admitted"])
        self.assertFalse(result["runtime_admitted"])
        self.assertFalse(result["release_scientifically_qualified"])
        self.assertEqual(result["native_model_invocations"], 0)
        for job in result["jobs"]:
            folder = self.base / "new" / job["path"]
            config = json.loads((folder / "config/realization.json").read_text())
            self.assertNotIn("routing", config)
            self.assertEqual(config["global"]["formulations"][0]["params"]["output_variables"], admission.CFE_OUTPUTS)
            self.assertEqual((folder / "config/cat_config/CFE/cat-1.ini").read_bytes(), before[job["path"] + "/config/cat_config/CFE/cat-1.ini"])

    def test_existing_destination_and_external_axis_change_refused(self):
        root, recipe = self.setup_assembly()
        destination = self.base / "exists"
        destination.mkdir()
        with patch.object(admission, "contract_sources", return_value=([], {})), self.assertRaises(FileExistsError):
            admission.qualify(root, self.base / "runtime", recipe, destination)
        data = json.loads(recipe.read_text())
        data["domain"]["catchment_ids"] = ["cat-9"]
        recipe.write_text(json.dumps(data))
        with self.assertRaises(admission.domain.PreparationError):
            admission.qualify(root, self.base / "runtime", recipe, self.base / "new")
        self.assertFalse((self.base / "new").exists())


if __name__ == "__main__":
    unittest.main()
