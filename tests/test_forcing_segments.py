"""Sparse archive provenance must never invent an unobserved whole-object hash."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from ngen_reforecast.campaign import CampaignError
from ngen_reforecast.forcing import _manifest, validate_history


class SegmentManifestTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1] / "examples/validation"
        self.value = json.loads((self.root / "history.manifest.json").read_text())
        self.value["schema_version"] = "forcing-manifest/0.2"
        self.value["source"]["objects"][0].update(sha256=None, segments=[
            {"start_byte": 0, "size_bytes": 16, "sha256": "1" * 64},
            {"start_byte": 100, "size_bytes": 23, "sha256": "2" * 64},
        ])

    def test_sparse_declaration_passes_content_without_authenticating_source(self):
        value = _manifest(self.value)
        self.assertIsNone(value["source"]["objects"][0]["sha256"])
        report = validate_history(value, self.root,
                                  expected_catchment_ids=["cat-1", "cat-2"],
                                  start_time_utc="2022-01-01T00:00:00Z",
                                  stop_time_utc_exclusive="2022-01-01T03:00:00Z")
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["source_truth_verified"])
        self.assertFalse(report["execution_ready"])
        self.assertTrue(report["qualification_blockers"])

    def test_whole_object_declaration_requires_empty_segments(self):
        value = deepcopy(self.value)
        value["source"]["objects"][0].update(sha256="3" * 64, segments=[])
        self.assertEqual(_manifest(value), value)
        value["source"]["objects"][0]["segments"] = self.value["source"]["objects"][0]["segments"]
        with self.assertRaises(CampaignError):
            _manifest(value)

    def test_sparse_declaration_without_segments_is_refused(self):
        self.value["source"]["objects"][0]["segments"] = []
        with self.assertRaises(CampaignError):
            _manifest(self.value)

    def test_old_manifest_cannot_silently_accept_sparse_hash(self):
        self.value["schema_version"] = "forcing-manifest/0.1"
        self.value["source"]["objects"][0].pop("segments")
        with self.assertRaises(CampaignError):
            _manifest(self.value)

    def test_ranges_refuse_overlap_reordering_and_object_overrun(self):
        cases = ([0, 0], [100, 0], [0, 101], [0, 123])
        for starts in cases:
            with self.subTest(starts=starts):
                value = deepcopy(self.value)
                for segment, start in zip(value["source"]["objects"][0]["segments"], starts):
                    segment["start_byte"] = start
                with self.assertRaises(CampaignError):
                    _manifest(value)

    def test_ranges_refuse_noninteger_negative_zero_and_large_sizes(self):
        for field, bad in (("start_byte", True), ("start_byte", -1),
                           ("start_byte", 0.5), ("size_bytes", 0),
                           ("size_bytes", 16 * 1024 * 1024 + 1)):
            with self.subTest(field=field, bad=bad):
                value = deepcopy(self.value)
                value["source"]["objects"][0]["segments"][0][field] = bad
                with self.assertRaises(CampaignError):
                    _manifest(value)

    def test_segments_refuse_unknown_fields_and_invalid_hash(self):
        for field, bad in (("sha256", "MD5-is-not-SHA256"), ("url", "unbound")):
            value = deepcopy(self.value)
            value["source"]["objects"][0]["segments"][0][field] = bad
            with self.assertRaises(CampaignError):
                _manifest(value)

    def test_source_identity_cannot_duplicate_generation(self):
        self.value["source"]["objects"].append(deepcopy(self.value["source"]["objects"][0]))
        with self.assertRaises(CampaignError):
            _manifest(self.value)

    def test_segment_count_is_bounded_across_objects(self):
        self.value["source"]["objects"][0]["size_bytes"] = 10_000
        self.value["source"]["objects"][0]["segments"] = [
            {"start_byte": i, "size_bytes": 1, "sha256": "1" * 64}
            for i in range(4097)
        ]
        with self.assertRaisesRegex(CampaignError, "segment count"):
            _manifest(self.value)

    def test_returned_manifest_is_independent_of_mutated_input(self):
        sealed = _manifest(self.value)
        self.value["source"]["objects"][0]["segments"][0]["sha256"] = "3" * 64
        self.assertEqual(sealed["source"]["objects"][0]["segments"][0]["sha256"], "1" * 64)
