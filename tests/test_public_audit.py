"""Offline audit refuses corrupt ranges, escaped staging and altered providers."""
import csv
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_audit", ROOT / "scripts/public_fixture/audit_prepared.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class PublicAuditTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local/tmp").mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".local/tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_overlap_merge_checks_bytes_and_keeps_gaps(self):
        result = adapter.merge_segments([(4, b"efgh"), (0, b"abcdef"), (10, b"kl")])
        self.assertEqual(result, [
            {"start_byte": 0, "size_bytes": 8, "sha256": hashlib.sha256(b"abcdefgh").hexdigest()},
            {"start_byte": 10, "size_bytes": 2, "sha256": hashlib.sha256(b"kl").hexdigest()},
        ])
        with self.assertRaisesRegex(ValueError, "disagree"):
            adapter.merge_segments([(0, b"abcdef"), (4, b"XXgh")])

    def test_contained_ranges_do_not_drop_source_bytes(self):
        result = adapter.merge_segments([(0, b"abcdef"), (2, b"cd")])
        self.assertEqual(result[0]["size_bytes"], 6)
        self.assertEqual(result[0]["sha256"], hashlib.sha256(b"abcdef").hexdigest())

    def test_long_ranges_split_without_promoting_whole_hash(self):
        with patch.object(adapter, "MAX_SEGMENT_BYTES", 4):
            result = adapter.merge_segments([(100, b"abcdef")])
        self.assertEqual([r["start_byte"] for r in result], [100, 104])
        self.assertEqual([r["size_bytes"] for r in result], [4, 2])

    def test_symlink_ancestor_cannot_redirect_output(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "link").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            adapter.safe_staging(self.root / "link/output")
        with self.assertRaises(ValueError):
            adapter.safe_staging(ROOT / ".local/../public-output")
        self.assertEqual(adapter.safe_staging(self.root / "new"), self.root / "new")

    def test_receipt_hash_is_verified_before_trust(self):
        path = self.root / "receipt.json"
        value = {"some": "contract"}
        value["preparation_identity_sha256"] = adapter.digest(value)
        path.write_text(json.dumps(value))
        self.assertEqual(adapter.sealed_receipt(path), value)
        value["some"] = "altered"
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            adapter.sealed_receipt(path)

    def test_provider_is_compared_by_full_key_and_single_precipitation_conversion(self):
        examples = ROOT / "examples/validation"
        decoded = (examples / "history.csv").read_bytes()
        weather = {"payloads": []}
        groups = {}
        expected = []
        for row in csv.DictReader(decoded.decode().splitlines()):
            values = {out: float(row[source]) / (3600 if source == "APCP" else 1)
                      for source, out in adapter.HISTORY_VARIABLES.items()}
            cat, stamp = row["catchment_id"], row["provider_time_utc"]
            groups.setdefault(cat, []).append([stamp.replace("T", " ").removesuffix("Z"), *values.values()])
            expected.append({"catchment_id": cat, "provider_time_utc": stamp, "values": values})
        for cat, rows in groups.items():
            name = f"provider/history/{cat}.csv"
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(["time", *adapter.OUTPUT_UNITS])
            writer.writerows(rows)
            raw = output.getvalue().encode()
            (self.root / name).write_bytes(raw)
            weather["payloads"].append({"path": name, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertEqual(adapter.provider_matches(weather, self.root, decoded, "history"), adapter.digest(expected))
        first = weather["payloads"][0]
        raw = (self.root / first["path"]).read_bytes().replace(b"00:00:00", b"04:00:00")
        (self.root / first["path"]).write_bytes(raw)
        first.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            adapter.provider_matches(weather, self.root, decoded, "history")

    def test_ragged_provider_row_is_refused(self):
        values = ["2022-01-01 00:00:00", *([1] * 8), "unexpected"]
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["time", *adapter.OUTPUT_UNITS])
        writer.writerow(values)
        raw = output.getvalue().encode()
        path = self.root / "provider/history/cat-1.csv"
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        weather = {"payloads": [{"path": "provider/history/cat-1.csv", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]}
        decoded = (ROOT / "examples/validation/history.csv").read_bytes()
        with self.assertRaisesRegex(ValueError, "row width"):
            adapter.provider_matches(weather, self.root, decoded, "history")

    def contract(self):
        recipe = json.loads((ROOT / "fixtures/watauga-public-v1/recipe.json").read_text())
        domain = {"preparation_identity_sha256": recipe["domain"]["preparation_identity_sha256"],
                  "catchment_ids": recipe["domain"]["catchment_ids"],
                  "geometry": {"sha256": recipe["domain"]["geometry_sha256"]},
                  "start_time_utc": recipe["weather"]["origin_time_utc"],
                  "stop_time_utc_exclusive": recipe["weather"]["stop_time_utc_exclusive"]}
        weather = deepcopy(recipe["weather"])
        weather["source_objects"] = weather.pop("forecast_objects")
        return recipe, domain, weather

    def test_external_recipe_refuses_missing_duplicate_or_shifted_issue_axis(self):
        recipe, domain, weather = self.contract()
        self.assertEqual(adapter.expected_contract(recipe, domain, weather), recipe["weather"]["issue_times_utc"])
        for axis in ([], weather["issue_times_utc"][:1], [weather["issue_times_utc"][0]] * 2,
                     list(reversed(weather["issue_times_utc"])), ["2022-01-01T22:00:00Z", weather["issue_times_utc"][1]]):
            with self.subTest(axis=axis), self.assertRaises(ValueError):
                adapter.expected_contract(recipe, domain, {**weather, "issue_times_utc": axis})

    def test_external_recipe_refuses_shorter_history_or_incomplete_source_population(self):
        recipe, domain, weather = self.contract()
        changed = deepcopy(weather)
        changed["source_objects"].pop()
        with self.assertRaises(ValueError):
            adapter.expected_contract(recipe, domain, changed)
        changed = {**domain, "start_time_utc": "2022-01-01T00:00:00Z"}
        with self.assertRaises(ValueError):
            adapter.expected_contract(recipe, changed, weather)

    def test_retained_source_corruption_cannot_be_hidden_by_valid_decoded_weather(self):
        raw = self.root / "raw"
        raw.mkdir()
        (raw / "source.bin").write_bytes(b"bad")
        value = {"source_objects": [], "source_responses": [{
            "relative_cache_path": "source.bin", "response_size_bytes": 3,
            "response_sha256": hashlib.sha256(b"old").hexdigest(),
            "url": "https://noaa-nws-aorc-v1-1-1km.s3.amazonaws.com/2021.zarr/x/0",
            "byte_range_inclusive": None, "whole_object_sha256": hashlib.sha256(b"old").hexdigest(),
            "etag": "opaque-etag",
        }]}
        with self.assertRaisesRegex(ValueError, "response identity"):
            adapter.source_objects(value, self.root)
