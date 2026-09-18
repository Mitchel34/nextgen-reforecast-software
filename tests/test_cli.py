"""Public CLI behavior and atomic output contracts, without model execution."""
from contextlib import redirect_stderr, redirect_stdout
import csv
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from ngen_reforecast.cli import _publish_new, main


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def call(self, *args):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(list(map(str, args)))
        return status, stdout.getvalue(), stderr.getvalue()

    def example(self):
        destination = self.root / "example"
        status, out, err = self.call("init", destination)
        self.assertEqual(status, 0, err)
        self.assertFalse(json.loads(out)["inputs_included"])
        return destination / "campaign.json"

    def test_init_creates_portable_template_and_refuses_existing_directory(self):
        campaign = self.example()
        original = campaign.read_bytes()
        status, _, error = self.call("init", campaign.parent)
        self.assertEqual(status, 1)
        self.assertIn("FileExistsError", error)
        self.assertEqual(campaign.read_bytes(), original)

    def test_template_plan_reports_blockers_without_claiming_execution(self):
        campaign = self.example()
        status, out, error = self.call("plan", campaign)
        self.assertEqual(status, 2, error)
        plan = json.loads(out)
        self.assertFalse(plan["execution_ready"])
        self.assertTrue(plan["blockers"])
        self.assertGreater(plan["totals"]["expected_forecast_rows"], 0)
        status2, out2, _ = self.call("plan", campaign)
        self.assertEqual(status, status2)
        self.assertEqual(out, out2)

    def test_ledger_writes_schedule_only_and_refuses_overwrite(self):
        campaign = self.example()
        target = self.root / "ledger.csv"
        status, out, error = self.call("ledger", campaign, "--output", target)
        self.assertEqual(status, 0, error)
        summary = json.loads(out)
        self.assertEqual(summary["forecasts_generated"], 0)
        with target.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), summary["rows"])
        self.assertEqual(set(rows[0]), {
            "domain_id", "location_id", "reach_id", "issue_time_utc", "lead_hour", "valid_time_utc"
        })
        original = target.read_bytes()
        status, _, _ = self.call("ledger", campaign, "--output", target)
        self.assertEqual(status, 1)
        self.assertEqual(target.read_bytes(), original)

    def test_ledger_row_cap_fails_before_publishing(self):
        campaign = self.example()
        target = self.root / "ledger.csv"
        status, _, error = self.call("ledger", campaign, "--output", target, "--max-rows", 1)
        self.assertEqual(status, 1)
        self.assertIn("exceeding", error)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob(".ngen-reforecast-*")))

    def test_report_exposes_missing_assets_and_unknown_measurements(self):
        campaign = self.example()
        output = self.root / "report.md"
        status, _, error = self.call("report", campaign, "--output", output)
        self.assertEqual(status, 2, error)
        text = output.read_text()
        self.assertIn("No forecast has been generated", text)
        self.assertIn("## Blockers", text)
        self.assertIn("remain unknown", text)

    def test_invalid_campaign_returns_structured_error(self):
        campaign = self.root / "bad.json"
        campaign.write_text('{"schema_version": "1.0", "schema_version": "2.0"}')
        status, output, error = self.call("plan", campaign)
        self.assertEqual(status, 1)
        self.assertEqual(output, "")
        self.assertIn("message", json.loads(error))

    def test_failed_publication_removes_partial_file(self):
        target = self.root / "partial.csv"
        def fail(handle):
            handle.write("uncommitted partial content")
            raise ValueError("injected output failure")
        with self.assertRaises(ValueError):
            _publish_new(target, fail)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.iterdir()))

    def test_destination_symlink_is_never_followed_or_replaced(self):
        existing = self.root / "protected"
        existing.write_text("original")
        link = self.root / "output"
        link.symlink_to(existing)
        with self.assertRaises(FileExistsError):
            _publish_new(link, lambda handle: handle.write("changed"))
        self.assertEqual(existing.read_text(), "original")
        self.assertTrue(link.is_symlink())

    def test_physical_execution_is_explicitly_unavailable(self):
        for command in ("run", "resume"):
            status, output, error = self.call(command)
            self.assertEqual(status, 2)
            self.assertEqual(output, "")
            self.assertEqual(json.loads(error)["error"], "PHYSICAL_EXECUTION_NOT_IMPLEMENTED")


if __name__ == "__main__":
    unittest.main()
