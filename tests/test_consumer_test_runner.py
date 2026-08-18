from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = (
    ROOT
    / "copier-template"
    / ".orinoco-lite"
    / "tools"
    / "run_consumer_tests.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_consumer_tests", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConsumerTestRunnerTests(unittest.TestCase):
    def test_empty_site_test_directory_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(
            io.StringIO()
        ) as stdout:
            Path(directory, "__init__.py").touch()
            result = load_runner().main([directory])
        self.assertEqual(0, result)
        self.assertIn("No site-owned Python tests", stdout.getvalue())

    def test_site_test_failures_propagate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "__init__.py").touch()
            Path(directory, "test_failure.py").write_text(
                "import unittest\n"
                "class Failure(unittest.TestCase):\n"
                "    def test_failure(self):\n"
                "        self.fail('expected')\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = load_runner().main([directory])
        self.assertEqual(1, result)

    def test_missing_site_test_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(
            io.StringIO()
        ) as stderr:
            result = load_runner().main([str(Path(directory, "missing"))])
        self.assertEqual(2, result)
        self.assertIn("Consumer test directory is missing", stderr.getvalue())
