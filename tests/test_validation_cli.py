"""Operator validation commands bind expected clocks and keep execution blocked."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ngen_reforecast.cli import main

ROOT = Path(__file__).parents[1]


class ValidationCLITests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.local/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('history.csv', 'history.manifest.json', 'forecast.csv', 'forecast.manifest.json'):
            shutil.copyfile(ROOT / 'examples/validation' / name, self.root / name)

    def call(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([str(arg) for arg in args])
        return code, out.getvalue(), err.getvalue()

    def arguments(self, role):
        m = json.loads((self.root / f'{role}.manifest.json').read_text())
        args = ['validate-forcing', self.root / f'{role}.manifest.json']
        for cid in m['catchment_ids']:
            args += ['--catchment', cid]
        if role == 'history':
            args += ['--history-start', m['start_time_utc'], '--history-stop', m['stop_time_utc_exclusive']]
        else:
            args += ['--issue-time', m['source']['issue_time_utc']]
        return args

    def test_both_roles_and_no_overwrite(self):
        for role in ('history', 'forecast'):
            code, out, err = self.call(*self.arguments(role))
            self.assertEqual(code, 0, err)
            result = json.loads(out)
            self.assertTrue(result['validation']['content_valid'])
            self.assertFalse(result['validation']['execution_ready'])
            self.assertEqual(result['gap_decision']['decision'], 'accept_content')
        target = self.root / 'report.json'
        args = self.arguments('history') + ['--output', target]
        self.assertEqual(self.call(*args)[0], 0)
        original = target.read_bytes()
        self.assertEqual(self.call(*args)[0], 1)
        self.assertEqual(target.read_bytes(), original)

    def test_independent_clock_is_required_and_manifest_cannot_supply_it(self):
        for role in ('history', 'forecast'):
            args = self.arguments(role)
            cutoff = args.index('--history-start' if role == 'history' else '--issue-time')
            code, out, err = self.call(*args[:cutoff])
            self.assertEqual(code, 1)
            self.assertIn('requires', err)
        args = self.arguments('history') + ['--issue-time', '2022-01-01T00:00:00Z']
        self.assertEqual(self.call(*args)[0], 1)

    def test_content_failure_and_recorded_exclusion_both_exit_two(self):
        path = self.root / 'forecast.csv'
        raw = path.read_bytes().splitlines(keepends=True)
        data = b''.join(raw[:-1])
        path.write_bytes(data)
        mpath = self.root / 'forecast.manifest.json'
        manifest = json.loads(mpath.read_text())
        manifest['payload'].update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
        mpath.write_text(json.dumps(manifest))
        for policy in ('fail', 'exclude_issue'):
            code, out, err = self.call(*self.arguments('forecast'), '--gap-policy', policy)
            self.assertEqual(code, 2, err)
            self.assertEqual(json.loads(out)['gap_decision']['decision'], policy)
            self.assertFalse(json.loads(out)['validation']['content_valid'])

    def test_cfe_manifest_missing_and_duplicate_json_are_errors(self):
        path = self.root / 'missing.json'
        self.assertEqual(self.call('validate-cfe', path, '--catchment', 'cat-1')[0], 1)
        path.write_text('{"schema_version": 1, "schema_version": 2}')
        self.assertEqual(self.call('validate-cfe', path, '--catchment', 'cat-1')[0], 1)
