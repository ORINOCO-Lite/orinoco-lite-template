from pathlib import Path
import subprocess
import tempfile
import unittest

import importlib.util

spec = importlib.util.spec_from_file_location("render_template", Path(__file__).resolve().parents[1] / "tools/render_template.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


ROOT = Path(__file__).resolve().parents[1]


class LockValidationTests(unittest.TestCase):
    def test_resolves_an_ignored_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            module.render(ROOT, destination / "rendered")
            destination = destination / "rendered"
            lock = destination / "pixi.lock"
            self.assertTrue(lock.is_file())
            subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
            subprocess.run(["git", "add", "."], cwd=destination, check=True)
            tracked = subprocess.check_output(
                ["git", "ls-files", "pixi.lock"], cwd=destination, text=True
            )
            self.assertEqual(tracked, "")
