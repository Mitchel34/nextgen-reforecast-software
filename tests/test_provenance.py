"""Planning snapshot identity and custody failures using synthetic bytes only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ngen_reforecast.campaign import ASSET_ROLES, CampaignError
from ngen_reforecast.provenance import (
    EVIDENCE_FIELDS, MAX_EVIDENCE_BYTES, ProvenanceError, load_lock, seal_lock, verify_lock,
)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parents[1] / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        template = Path(__file__).parents[1] / "src/ngen_reforecast/templates/campaign.json"
        self.spec = json.loads(template.read_text())
        self.spec["domains"] = [{"domain_id": "fixture", "locations": [
            {"location_id": "gauge", "reach_id": "123"}], "assets": []}]
        for role in sorted(ASSET_ROLES):
            data = f"synthetic {role}\n".encode()
            path = f"{role}.txt"
            (self.root / path).write_bytes(data)
            self.spec["domains"][0]["assets"].append({
                "role": role, "path": path, "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            })

    def test_deterministic_detached_lock_keeps_unknowns_and_false_readiness(self):
        first = seal_lock(self.spec, self.root)
        second = seal_lock(dict(reversed(list(self.spec.items()))), self.root)
        self.assertEqual(first, second)
        self.assertEqual(first["unknown_evidence"], list(EVIDENCE_FIELDS))
        report = verify_lock(first, self.root)
        self.assertTrue(report["input_bytes_verified"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["scientific_semantics_verified"])
        self.spec["domains"][0]["locations"][0]["reach_id"] = "999"
        self.assertEqual(first["campaign"]["domains"][0]["locations"][0]["reach_id"], "123")

    def test_scientific_context_changes_identity_without_claiming_validation(self):
        initial = seal_lock(self.spec, self.root)
        for field in EVIDENCE_FIELDS:
            evidence = dict.fromkeys(EVIDENCE_FIELDS)
            evidence[field] = {"declared_version": "candidate1"}
            lock = seal_lock(self.spec, self.root, evidence)
            self.assertNotEqual(initial["experiment_identity_sha256"], lock["experiment_identity_sha256"])
            self.assertNotEqual(initial["domain_identities"], lock["domain_identities"])
            self.assertEqual(lock["metadata_status"], "declared_unvalidated")
            self.assertFalse(lock["execution_ready"])

    def test_shorthand_normalizes_to_same_lock_and_retention_changes_identity(self):
        self.spec["schema_version"] = "1.1"
        self.spec["retained_leads"] = {"min_lead_hours": 1, "max_lead_hours": 18, "projection": "export"}
        explicit = seal_lock(self.spec, self.root)
        shorthand = copy.deepcopy(self.spec)
        shorthand.pop("issue_times_utc")
        shorthand["issue_schedule"] = {
            "start_time_utc": "2022-01-01T23:00:00Z",
            "stop_time_utc_exclusive": "2022-01-02T01:00:00Z", "cadence_hours": 1,
        }
        self.assertEqual(explicit, seal_lock(shorthand, self.root))
        shorthand["retained_leads"]["max_lead_hours"] = 6
        retained = seal_lock(shorthand, self.root)
        self.assertNotEqual(explicit["experiment_identity_sha256"], retained["experiment_identity_sha256"])
        self.assertNotEqual(explicit["domain_identities"], retained["domain_identities"])

    def test_asset_change_after_seal_fails_recheck(self):
        lock = seal_lock(self.spec, self.root)
        path = self.root / self.spec["domains"][0]["assets"][0]["path"]
        path.write_bytes(b"x" * path.stat().st_size)
        report = verify_lock(lock, self.root)
        self.assertFalse(report["input_bytes_verified"])
        self.assertIn("asset_hash_mismatch", [x["code"] for x in report["blockers"]])
        with self.assertRaises(ProvenanceError):
            seal_lock(self.spec, self.root)

    def test_missing_roles_and_unknown_asset_identity_cannot_be_sealed(self):
        for mutation in ("role", "sha256", "size_bytes"):
            spec = copy.deepcopy(self.spec)
            if mutation == "role":
                spec["domains"][0]["assets"].pop()
            else:
                spec["domains"][0]["assets"][0][mutation] = None
            with self.subTest(mutation=mutation), self.assertRaises(ProvenanceError):
                seal_lock(spec, self.root)

    def test_metadata_tamper_and_readiness_forgery_fail(self):
        lock = seal_lock(self.spec, self.root)
        for field, value in (("execution_ready", True), ("lock_sha256", "0" * 64),
                             ("unknown_evidence", []), ("metadata_status", "qualified")):
            changed = {**lock, field: value}
            with self.subTest(field=field), self.assertRaises(ProvenanceError):
                verify_lock(changed, self.root)
        changed = copy.deepcopy(lock)
        changed["campaign"]["issue_times_utc"].pop()
        with self.assertRaises(ProvenanceError):
            verify_lock(changed, self.root)

    def test_nested_domains_remain_distinct_and_bind_locations(self):
        second = copy.deepcopy(self.spec["domains"][0])
        second.update(domain_id="nested", locations=[{"location_id": "nested-gauge", "reach_id": "456"}])
        self.spec["domains"].append(second)
        first = seal_lock(self.spec, self.root)
        self.assertNotEqual(first["domain_identities"][0]["identity_sha256"],
                            first["domain_identities"][1]["identity_sha256"])
        self.spec["domains"][1]["locations"][0]["reach_id"] = "789"
        changed = seal_lock(self.spec, self.root)
        self.assertEqual(first["domain_identities"][0], changed["domain_identities"][0])
        self.assertNotEqual(first["domain_identities"][1], changed["domain_identities"][1])

    def test_unsafe_inputs_and_nonfinite_or_oversized_evidence_refused(self):
        evidence = dict.fromkeys(EVIDENCE_FIELDS)
        for item in ({"x": float("nan")}, {"x": "a" * MAX_EVIDENCE_BYTES}, {}):
            evidence["runtime"] = item
            with self.subTest(item_type=type(item)), self.assertRaises(CampaignError):
                seal_lock(self.spec, self.root, evidence)
        path = self.root / self.spec["domains"][0]["assets"][0]["path"]
        original = path.read_bytes()
        path.unlink()
        other = self.root / "other.txt"
        other.write_bytes(original)
        path.symlink_to(other)
        with self.assertRaises(ProvenanceError):
            seal_lock(self.spec, self.root)

    def test_lock_reader_rejects_duplicate_keys_symlinks_and_oversized_files(self):
        lock = seal_lock(self.spec, self.root)
        path = self.root / "lock.json"
        path.write_text(json.dumps(lock))
        self.assertEqual(load_lock(path), lock)
        link = self.root / "linked.json"
        link.symlink_to(path)
        with self.assertRaises(ProvenanceError):
            load_lock(link)
        path.write_text('{"schema_version":"a","schema_version":"b"}')
        with self.assertRaises(CampaignError):
            load_lock(path)
        with path.open("wb") as handle:
            handle.truncate(8 * 1024 * 1024 + 1)
        with self.assertRaises(ProvenanceError):
            load_lock(path)


if __name__ == "__main__":
    unittest.main()
