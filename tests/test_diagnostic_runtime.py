"""Diagnostic admission must refuse invalid exports before starting containers."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "diagnostic_runtime_qualifier", Path(__file__).parents[1] / "scripts/runtime/qualify_export.py"
)
qualifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualifier)


class DiagnosticRuntimeAdmissionTests(unittest.TestCase):
    def test_corrupt_export_is_refused_before_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "exports").mkdir()
            (root / "exports/ngen-shared").write_bytes(b"incorrect native bytes")
            with patch.object(qualifier.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "export hash mismatch"):
                    qualifier.qualify("unix:///explicit/socket", root / "exports", root / "locks",
                                      root / "build", root / "probe")
                run.assert_not_called()

    def test_nonlocal_endpoint_is_refused(self):
        with patch.object(qualifier.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Unix endpoint"):
                qualifier.qualify("tcp://remote:2375", Path("unused"), Path("unused"),
                                  Path("unused"), Path("unused"))
            run.assert_not_called()

    def test_leaf_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "resident").write_bytes(b"data")
            (root / "alias").symlink_to(root / "resident")
            with self.assertRaisesRegex(ValueError, "symlink"):
                qualifier.resident_bytes(root / "alias")

    def test_parent_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / "resident").mkdir()
            (root / "resident/data").write_bytes(b"data")
            (root / "alias").symlink_to(root / "resident", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                qualifier.resident_bytes(root / "alias/data")

    def test_oversized_leaf_is_refused_before_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "oversized"
            path.write_bytes(b"12345")
            with patch.object(qualifier.os, "open") as opened:
                with self.assertRaisesRegex(ValueError, "bounded regular"):
                    qualifier.resident_bytes(path, 4)
                opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
