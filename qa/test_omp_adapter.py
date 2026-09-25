"""Ownership and safety behavior for native OMP package builds."""
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("omp_build", ROOT / "adapters" / "omp" / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class OmpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.package = Path(self.tmp.name) / "dev-workflows"
        BUILD.build_package(ROOT, self.package)

    def test_refuses_to_replace_unowned_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "third-party"
            dest.mkdir()
            sentinel = dest / "keep"
            sentinel.write_text("untouched")
            with self.assertRaises(FileExistsError):
                BUILD.build_package(ROOT, dest)
            self.assertEqual(sentinel.read_text(), "untouched")

    def test_preserves_manual_edits_in_managed_package(self):
        prompt = self.package / "agents" / "planner.md"
        prompt.write_text(prompt.read_text() + "\nMudança do usuário.\n")
        with self.assertRaisesRegex(FileExistsError, "alterações manuais"):
            BUILD.build_package(ROOT, self.package)
        self.assertIn("Mudança do usuário.", prompt.read_text())

    def test_rejects_invalid_model_selectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                BUILD.build_package(ROOT, Path(tmp) / "package", {"planner": "gpt-6-luna"})


if __name__ == "__main__":
    unittest.main()
