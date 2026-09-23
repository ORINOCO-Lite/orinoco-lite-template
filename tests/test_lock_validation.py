from pathlib import Path
import shutil
import tempfile
import unittest

import importlib.util

spec = importlib.util.spec_from_file_location("render_template", Path(__file__).resolve().parents[1] / "tools/render_template.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
verify_frozen_lock = module.verify_frozen_lock


ROOT = Path(__file__).resolve().parents[1]


class LockValidationTests(unittest.TestCase):
    def test_checks_dependencies_without_rewriting_or_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            module.render(ROOT, destination / "rendered")
            destination = destination / "rendered"
            lock = destination / "pixi.lock"
            # Comments are valid YAML and must not make a dependency lock stale.
            lock.write_text("# Preserve source formatting.\n" + lock.read_text())
            before = lock.read_bytes()
            verify_frozen_lock(destination)
            self.assertEqual(lock.read_bytes(), before)
            self.assertFalse((destination / ".pixi/envs").exists())
            manifest = destination / "pixi.toml"
            manifest.write_text(manifest.read_text().replace('python = ">=3.12,<3.13"', 'python = "==3.11.0"'))
            self.assertIn('python = "==3.11.0"', manifest.read_text())
            with self.assertRaises(RuntimeError):
                verify_frozen_lock(destination)
            self.assertEqual(lock.read_bytes(), before)
