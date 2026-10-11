"""Failure boundaries for independently authored public fixture preparation."""
import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("public_domain_adapter", ROOT / "scripts/public_fixture/prepare_domain.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class PublicDomainTests(unittest.TestCase):
    def test_reach_closure_excludes_adjacent_downstream_branch(self):
        rows = [("wb-1", "nex-1", "cat-1"), ("nex-1", "wb-2", None),
                ("wb-2", "nex-2", "cat-2"), ("wb-3", "nex-2", "cat-3")]
        result = adapter.upstream_closure(rows, "wb-2")
        self.assertEqual(result["catchment_ids"], ["cat-1", "cat-2"])
        self.assertEqual(result["outlet_nexus"], "nex-2")
        self.assertNotIn("wb-3", result["nodes"])

    def test_null_network_rows_cannot_connect_unrelated_rivers(self):
        rows = [("wb-1", "nex-1", "cat-1"), (None, "wb-1", None),
                ("wb-2", "nex-2", "cat-2"), ("nex-2", None, None)]
        # A non-null node with null toid is malformed, rather than a bridge.
        with self.assertRaises(adapter.PreparationError):
            adapter.upstream_closure(rows, "wb-1")
        result = adapter.upstream_closure(rows[:-1], "wb-1")
        self.assertEqual(result["catchment_ids"], ["cat-1"])

    def test_duplicate_network_rows_do_not_duplicate_catchments(self):
        result = adapter.upstream_closure([("wb-1", "nex-1", "cat-1")] * 3, "wb-1")
        self.assertEqual(result["catchment_ids"], ["cat-1"])

    def test_cycle_or_split_rejected(self):
        cases = [[("wb-1", "nex-1", "cat-1"), ("nex-1", "wb-1", None)],
                 [("wb-1", "nex-1", "cat-1"), ("wb-1", "nex-2", "cat-1")]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(adapter.PreparationError):
                adapter.upstream_closure(rows, "wb-1")

    def test_nexus_is_not_an_inclusive_reach_request(self):
        with self.assertRaises(adapter.PreparationError):
            adapter.upstream_closure([("wb-1", "nex-1", "cat-1")], "nex-1")

    @staticmethod
    def row():
        return {"centroid_x": 1., "centroid_y": 2., "mean.slope": 85., "mean.slope_1km": .05,
                "mode.bexp_soil_layers_stag=2": 4., "geom_mean.dksat_soil_layers_stag=2": .001,
                "geom_mean.psisat_soil_layers_stag=2": .3, "mean.smcmax_soil_layers_stag=2": .45,
                "mean.smcwlt_soil_layers_stag=2": .1, "mean.Zmax": 1000., "mean.Coeff": .001,
                "mode.Expon": 6., "mean.refkdt": 3., "circ_mean.aspect": 180.,
                "mode.ISLTYP": 4., "mode.IVGTYP": 5.}

    def test_cfe_bottom_drainage_and_noah_terrain_use_distinct_fields(self):
        result = adapter.configuration_values(self.row(), lambda x, y: (-81.8, 36.2))
        self.assertEqual(result["cfe"]["slope"], .05)
        self.assertAlmostEqual(result["noah"]["terrain_slope"], 6.520639289381933)
        self.assertEqual(result["cfe"]["max_gw_storage"], 1.)

    def test_invalid_parameter_values_fail_without_clipping(self):
        for field, value in [("mean.slope_1km", 1.01), ("mode.ISLTYP", 4.5),
                             ("mean.Zmax", None), ("mean.Coeff", float("nan"))]:
            row = self.row()
            row[field] = value
            with self.subTest(field=field), self.assertRaises(adapter.PreparationError):
                adapter.configuration_values(row, lambda x, y: (-81.8, 36.2))

    def test_clock_and_envelope_rejections(self):
        with self.assertRaises(adapter.PreparationError):
            adapter.hourly_time("2022-01-01T00:30:00Z")
        with self.assertRaises(adapter.PreparationError):
            adapter.envelope(b"<html>HTTP 200</html>")

    def setUp(self):
        (ROOT / ".local/tmp").mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".local/tmp")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def synthetic_source(self):
        folder = self.base / "source"
        folder.mkdir()
        path = folder / "source.gpkg"
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE network (fid INTEGER PRIMARY KEY,id TEXT,toid TEXT,divide_id TEXT)")
            db.execute("INSERT INTO network VALUES (1,'wb-1','nex-1','cat-1')")
            geom = b"GP\x00\x03" + struct.pack("<i4d", 5070, 1., 2., 3., 4.)
            db.execute("CREATE TABLE divides (fid INTEGER PRIMARY KEY,divide_id TEXT,geom BLOB,areasqkm REAL)")
            db.execute("INSERT INTO divides VALUES (1,'cat-1',?,1)", (geom,))
            row = self.row()
            db.execute('CREATE TABLE "divide-attributes" (fid INTEGER PRIMARY KEY,divide_id TEXT,' +
                       ",".join(adapter.quote(key) + " REAL" for key in row) + ")")
            db.execute('INSERT INTO "divide-attributes" VALUES (' + ",".join("?" for _ in range(len(row)+2)) + ")", [1, "cat-1", *row.values()])
            for table in set(adapter.TABLE_KEYS) - {"network", "divides", "divide-attributes"}:
                db.execute(f"CREATE TABLE {adapter.quote(table)} (fid INTEGER PRIMARY KEY,id TEXT)")
                if table in ("flowpaths", "flowpath-attributes", "flowpath-attributes-ml"):
                    db.execute(f"INSERT INTO {adapter.quote(table)} VALUES (1,'wb-1')")
                elif table == "nexus":
                    db.execute(f"INSERT INTO {adapter.quote(table)} VALUES (1,'nex-1')")
            db.execute("CREATE TABLE gpkg_geometry_columns (table_name TEXT,column_name TEXT,srs_id INTEGER)")
            db.execute("INSERT INTO gpkg_geometry_columns VALUES ('divides','geom',5070)")
            db.execute("CREATE TABLE gpkg_spatial_ref_sys (srs_id INTEGER,definition TEXT)")
            db.execute("INSERT INTO gpkg_spatial_ref_sys VALUES (5070,'synthetic')")
            db.execute("CREATE TABLE gpkg_contents (table_name TEXT,min_x REAL,min_y REAL,max_x REAL,max_y REAL)")
            db.execute("INSERT INTO gpkg_contents VALUES ('divides',0,0,10,10)")
            db.commit()
        return path

    def synthetic_templates(self):
        root = self.base / "templates"
        root.mkdir()
        values = {"cfe": "soil_params.slop={slope}[m/m]\n", "noah": "lat={lat} lon={lon} start={start_datetime} end={end_datetime}\n",
                  "routing": "cpu_pool: {cpu_pool}\nnts: {nts}\ndt: {time_step_size}\n",
                  "realization": '{"time": {}}', "license": "MIT License\nAlabama  Water Institute"}
        rows = []
        for name, rel in adapter.TEMPLATES.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(values[name])
            rows.append({"path": rel, **adapter.binding(target)})
        (root / "SOURCE_RECEIPT.json").write_text(json.dumps({"commit": adapter.UPSTREAM_REVISION, "files": rows}))
        return root

    def generate(self, source, templates, destination="fixture", **changes):
        args = {"expected_sha256": adapter.binding(source)["sha256"], "expected_bytes": source.stat().st_size,
                "reach": "wb-1", "gauge_id": "03479000", "start_time_utc": "2021-12-01T00:00:00Z",
                "stop_time_utc_exclusive": "2021-12-02T00:00:00Z", "transform": lambda x,y: (-81.8,36.2)}
        args.update(changes)
        return adapter.prepare(source, self.base / destination, templates, **args)

    def test_source_hash_mismatch_refused_before_creation(self):
        source, templates = self.synthetic_source(), self.synthetic_templates()
        with self.assertRaises(adapter.PreparationError):
            self.generate(source, templates, expected_sha256="0" * 64)
        self.assertFalse((self.base / "fixture").exists())

    def test_generation_keeps_source_bytes_and_cannot_attest_execution(self):
        source, templates = self.synthetic_source(), self.synthetic_templates()
        before = adapter.binding(source)
        result = self.generate(source, templates)
        self.assertEqual(result["catchment_ids"], ["cat-1"])
        self.assertEqual(result["history_hours"], 24)
        self.assertFalse(result["execution_ready"])
        self.assertFalse(result["historical_fixture_restored"])
        self.assertEqual(adapter.binding(source), before)
        self.assertEqual(sorted(p.name for p in source.parent.iterdir()), ["source.gpkg"])
        self.assertEqual((self.base / "fixture/config/cat_config/CFE/cat-1.ini").read_text(), "soil_params.slop=0.05[m/m]\n")
        with closing(sqlite3.connect(self.base / "fixture/config/public-watauga.gpkg")) as db:
            self.assertEqual(db.execute("SELECT min_x FROM gpkg_contents").fetchone(), (None,))

    def test_no_overwrite_and_symlink_source(self):
        source, templates = self.synthetic_source(), self.synthetic_templates()
        self.generate(source, templates)
        with self.assertRaises(FileExistsError):
            self.generate(source, templates)
        link = source.parent / "alias.gpkg"
        link.symlink_to(source)
        with self.assertRaises(Exception):
            self.generate(link, templates, destination="fixture2")

    def test_changed_template_binding_refused(self):
        source, templates = self.synthetic_source(), self.synthetic_templates()
        (templates / adapter.TEMPLATES["cfe"]).write_text("soil_params.slop=99[m/m]\n")
        with self.assertRaises(adapter.PreparationError):
            self.generate(source, templates)

    def test_destination_outside_private_staging_refused(self):
        with self.assertRaises(adapter.PreparationError):
            adapter.fresh_directory(ROOT / "unwanted-fixture-write", [])
        self.assertFalse((ROOT / "unwanted-fixture-write").exists())


if __name__ == "__main__":
    unittest.main()
