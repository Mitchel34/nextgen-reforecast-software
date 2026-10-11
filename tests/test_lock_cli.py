"""CLI lock publication and generated/retained projections remain offline."""
from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from ngen_reforecast.campaign import ASSET_ROLES
from ngen_reforecast.cli import main


class LockCLITests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parents[1] / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.call("init", self.root / "campaign")
        self.path = self.root / "campaign/campaign.json"
        self.spec = json.loads(self.path.read_text())

    def call(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(arg) for arg in args])
        return code, out.getvalue(), err.getvalue()

    def bind_synthetic_assets(self):
        for domain in self.spec["domains"]:
            domain["assets"] = []
            for role in sorted(ASSET_ROLES):
                path = f'{domain["domain_id"]}-{role}.txt'
                data = path.encode()
                (self.path.parent / path).write_bytes(data)
                domain["assets"].append({"role": role, "path": path,
                    "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
        self.path.write_text(json.dumps(self.spec))

    def test_unbound_template_does_not_publish_lock(self):
        target = self.root / "lock.json"
        code, out, err = self.call("lock", self.path, "--output", target)
        self.assertEqual(code, 1, out)
        self.assertIn("input identity", err)
        self.assertFalse(target.exists())

    def test_create_verify_tamper_and_no_overwrite(self):
        self.bind_synthetic_assets()
        target = self.root / "lock.json"
        code, out, err = self.call("lock", self.path, "--output", target)
        self.assertEqual(code, 0, err)
        self.assertFalse(json.loads(out)["execution_ready"])
        original = target.read_bytes()
        code, _, _ = self.call("lock", self.path, "--output", target)
        self.assertEqual(code, 1)
        self.assertEqual(original, target.read_bytes())
        code, out, err = self.call("verify-lock", target, "--asset-root", self.path.parent)
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["input_bytes_verified"])
        self.assertFalse(json.loads(out)["execution_ready"])
        first = self.spec["domains"][0]["assets"][0]
        (self.path.parent / first["path"]).unlink()
        code, out, err = self.call("verify-lock", target, "--asset-root", self.path.parent)
        self.assertEqual(code, 2, err)
        self.assertFalse(json.loads(out)["input_bytes_verified"])

    def test_lead_projection_changes_ledger_not_physical_horizon(self):
        self.spec["schema_version"] = "1.1"
        self.spec["retained_leads"] = {"min_lead_hours": 1, "max_lead_hours": 6, "projection": "export"}
        self.path.write_text(json.dumps(self.spec))
        counts = {}
        for kind in ("generated", "retained"):
            path = self.root / f"{kind}.csv"
            code, out, err = self.call("ledger", self.path, "--output", path, "--kind", kind)
            self.assertEqual(code, 0, err)
            counts[kind] = json.loads(out)["rows"]
            if kind == "retained":
                self.assertEqual(json.loads(out)["kind"], "retained")
            else:
                self.assertNotIn("kind", json.loads(out))
            with path.open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), counts[kind])
            self.assertEqual(max(int(row["lead_hour"]) for row in rows), 18 if kind == "generated" else 6)
        self.assertEqual(counts["generated"], counts["retained"] * 3)


if __name__ == "__main__":
    unittest.main()
