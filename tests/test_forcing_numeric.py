"""Source values cannot silently change through Python-specific number syntax."""
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from ngen_reforecast.forcing import validate_history

ROOT = Path(__file__).parents[1]


class ForcingNumericTests(unittest.TestCase):
    def test_underflow_and_nonportable_literals_fail_with_matching_hash(self):
        manifest = json.loads((ROOT / 'examples/validation/history.manifest.json').read_text())
        rows = list(csv.DictReader(io.StringIO((ROOT / 'examples/validation/history.csv').read_text())))
        scratch = ROOT / '.local/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            base = Path(name)
            for literal in ('-1e-999', '1e-999', '1e-323', '1_000', ' 1', '１.０'):
                with self.subTest(literal=literal):
                    changed = deepcopy(rows)
                    changed[0]['APCP'] = literal
                    stream = io.StringIO(newline='')
                    writer = csv.DictWriter(stream, fieldnames=list(changed[0]))
                    writer.writeheader(); writer.writerows(changed)
                    raw = stream.getvalue().encode()
                    (base / manifest['payload']['path']).write_bytes(raw)
                    manifest['payload'].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
                    report = validate_history(manifest, base, expected_catchment_ids=manifest['catchment_ids'],
                                              start_time_utc=manifest['start_time_utc'],
                                              stop_time_utc_exclusive=manifest['stop_time_utc_exclusive'])
                    self.assertFalse(report['content_valid'])
                    self.assertIsNone(report['normalized_payload_sha256'])
                    self.assertFalse(report['execution_ready'])
                    if literal.startswith('-'):
                        self.assertIn('negative_precipitation', {b['code'] for b in report['blockers']})
