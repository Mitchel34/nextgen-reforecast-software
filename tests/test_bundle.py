"""Bundle identity, hydration refusal and private staging contract tests."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast.bundle import BundleError, bind_fixture_contract, inventory_bundle, stage_bundle
from ngen_reforecast.runtime import _InspectionFailure

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.local').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.raw = b'original forcing bytes\n'
        (self.source / 'forcing.csv').write_bytes(self.raw)
        self.assets = [{'path': 'forcing.csv', 'sha256': hashlib.sha256(self.raw).hexdigest(), 'bytes': len(self.raw)}]
        self.sources = {'original': self.source}

    def inspect(self, **kwargs):
        return inventory_bundle(self.assets, self.sources, **kwargs)

    def test_verified_bytes_are_not_physical_admission(self):
        report = self.inspect()
        self.assertTrue(report['input_bytes_verified'])
        self.assertFalse(report['execution_ready'])
        self.assertFalse(report['scientific_semantics_verified'])
        self.assertNotIn(str(self.source), json.dumps(report))

    def test_unknown_identity_is_not_promoted_from_observation(self):
        self.assets[0]['sha256'] = None
        report = self.inspect()
        self.assertEqual(report['assets'][0]['status'], 'unbound')
        self.assertFalse(report['input_bytes_verified'])
        self.assertEqual(report['summary']['unresolved_expected_hashes'], 1)

    def test_missing_does_not_make_partial_bundle_complete(self):
        self.assets.append({'path': 'missing.csv', 'sha256': 'a' * 64, 'bytes': 1})
        report = stage_bundle(self.assets, self.sources, self.root / 'bundle')
        self.assertFalse(report['input_bytes_verified'])
        self.assertEqual(report['summary']['staged_assets'], 1)
        self.assertEqual(report['assets'][1]['status'], 'missing')

    def test_same_size_hash_mismatch_never_staged(self):
        (self.source / 'forcing.csv').write_bytes(b'x' * len(self.raw))
        report = stage_bundle(self.assets, self.sources, self.root / 'bundle')
        self.assertEqual(report['assets'][0]['status'], 'hash_mismatch')
        self.assertFalse((self.root / 'bundle' / 'forcing.csv').exists())

    def test_size_mismatch_is_not_read(self):
        self.assets[0]['bytes'] += 1
        report = self.inspect()
        self.assertEqual(report['assets'][0]['status'], 'size_mismatch')
        self.assertEqual(report['summary']['source_bytes_read_or_reserved'], 0)

    def test_dataless_rejected_before_content_read(self):
        with patch('ngen_reforecast.bundle._open_asset', side_effect=_InspectionFailure('DATALESS_REJECTED', 'offline')):
            report = self.inspect()
        self.assertEqual(report['assets'][0]['status'], 'dataless')
        self.assertEqual(report['summary']['source_bytes_read_or_reserved'], 0)

    def test_file_and_total_bounds(self):
        for kwargs, code in [({'max_file_bytes': 1}, 'FILE_HASH_BOUND_EXCEEDED'),
                             ({'max_total_bytes': 1}, 'TOTAL_HASH_BOUND_EXCEEDED')]:
            with self.subTest(code=code):
                report = self.inspect(**kwargs)
                self.assertEqual(report['assets'][0]['code'], code)
                self.assertEqual(report['summary']['source_bytes_read_or_reserved'], 0)

    def test_raced_read_reserved_against_budget(self):
        with patch('ngen_reforecast.bundle._read_bounded', side_effect=_InspectionFailure('FILE_CHANGED', 'race')):
            report = self.inspect()
        self.assertEqual(report['assets'][0]['code'], 'FILE_CHANGED')
        self.assertEqual(report['summary']['source_bytes_read_or_reserved'], len(self.raw))

    def test_symlink_sources_rejected(self):
        (self.source / 'link').symlink_to(self.source / 'forcing.csv')
        report = self.inspect(candidates={'forcing.csv': [{'root': 'original', 'path': 'link'}]})
        self.assertEqual(report['assets'][0]['code'], 'SYMLINK_REJECTED')
        link = self.root / 'root-link'
        link.symlink_to(self.source, target_is_directory=True)
        report = inventory_bundle(self.assets, {'linked': link})
        self.assertEqual(report['assets'][0]['code'], 'SYMLINK_REJECTED')

    def test_explicit_equivalent_copy_keeps_failed_attempt(self):
        copy = self.root / 'copy'
        copy.mkdir()
        (copy / 'preserved').write_bytes(self.raw)
        (self.source / 'forcing.csv').unlink()
        report = inventory_bundle(self.assets, {**self.sources, 'preserved': copy}, {
            'forcing.csv': [{'root': 'original', 'path': 'forcing.csv'}, {'root': 'preserved', 'path': 'preserved'}]})
        self.assertEqual(report['assets'][0]['source_alias'], 'preserved')
        self.assertEqual(len(report['assets'][0]['attempts']), 2)
        self.assertTrue(report['input_bytes_verified'])

    def test_private_copy_is_new_bytes_not_hardlink(self):
        source_stat = (self.source / 'forcing.csv').stat()
        report = stage_bundle(self.assets, self.sources, self.root / 'bundle')
        staged = self.root / 'bundle' / 'forcing.csv'
        self.assertEqual(staged.read_bytes(), self.raw)
        self.assertNotEqual(staged.stat().st_ino, source_stat.st_ino)
        self.assertEqual(staged.stat().st_mode & 0o777, 0o400)
        self.assertEqual(source_stat.st_mtime_ns, (self.source / 'forcing.csv').stat().st_mtime_ns)
        self.assertEqual(report['summary']['staged_assets'], 1)

    def test_existing_or_source_destination_refused(self):
        for destination in [self.source, self.source / 'new', self.root]:
            with self.subTest(destination=destination), self.assertRaises(BundleError):
                stage_bundle(self.assets, self.sources, destination)
        self.assertFalse((self.source / 'new').exists())

    def test_nested_staging_and_symlink_destination_parent(self):
        self.assets[0]['path'] = 'fixture/nested/data.csv'
        candidates = {self.assets[0]['path']: [{'root': 'original', 'path': 'forcing.csv'}]}
        report = stage_bundle(self.assets, self.sources, self.root / 'bundle', candidates)
        self.assertTrue(report['input_bytes_verified'])
        link = self.root / 'link'
        link.symlink_to(self.root / 'bundle', target_is_directory=True)
        with self.assertRaises(BundleError):
            stage_bundle(self.assets, self.sources, link / 'child', candidates)

    def test_unsafe_declarations_refused(self):
        for path in ['../escape', '/absolute', '.', 'double//slash', 'a/../b']:
            with self.subTest(path=path), self.assertRaises(BundleError):
                inventory_bundle([{**self.assets[0], 'path': path}], self.sources)
        with self.assertRaises(BundleError):
            inventory_bundle(self.assets * 2, self.sources)
        with self.assertRaises(BundleError):
            self.inspect(max_file_bytes=17 * 1024 * 1024)

    def fixture(self, *, conflict=False):
        contract = {'schema': 'nextgen-real-day-custody-qualification/v3', 'files': {
            'forcing.csv': {'bytes': len(self.raw), 'sha256': self.assets[0]['sha256']}}}
        raw = json.dumps(contract).encode()
        assets = [{'path': 'fixture/CONTRACT.json', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)},
                  {**self.assets[0], 'path': 'fixture/forcing.csv', 'sha256': 'b' * 64 if conflict else None}]
        return raw, assets

    def test_contract_resolves_only_prebound_manifest(self):
        raw, assets = self.fixture()
        report = bind_fixture_contract(raw, assets)
        self.assertEqual(report['resolved_unknown_hashes'], 1)
        self.assertEqual(report['unresolved_hashes'], 0)
        self.assertFalse(report['input_bytes_verified'])
        self.assertIsNone(assets[1]['sha256'])
        self.assertEqual(report, bind_fixture_contract(raw, assets))

    def test_changed_or_unbound_contract_refused(self):
        raw, assets = self.fixture()
        with self.assertRaises(BundleError):
            bind_fixture_contract(raw + b' ', assets)
        assets[0]['sha256'] = None
        with self.assertRaises(BundleError):
            bind_fixture_contract(raw, assets)

    def test_contract_conflicting_existing_identity_refused(self):
        raw, assets = self.fixture(conflict=True)
        with self.assertRaises(BundleError):
            bind_fixture_contract(raw, assets)

    def test_stage_failure_not_reported_verified(self):
        with patch('ngen_reforecast.bundle._write_member', side_effect=OSError('failed')):
            report = stage_bundle(self.assets, self.sources, self.root / 'bundle')
        self.assertEqual(report['summary']['verified_assets'], 0)
        self.assertFalse(report['input_bytes_verified'])


if __name__ == '__main__':
    unittest.main()
