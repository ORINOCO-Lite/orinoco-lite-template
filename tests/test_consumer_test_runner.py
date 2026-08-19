from __future__ import annotations

import importlib.util
import io
import os
import sys
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
    def setUp(self) -> None:
        self.previous_dont_write_bytecode = sys.dont_write_bytecode
        self.previous_environment = os.environ.pop(
            "PYTHONDONTWRITEBYTECODE",
            None,
        )
        sys.dont_write_bytecode = False

    def tearDown(self) -> None:
        sys.dont_write_bytecode = self.previous_dont_write_bytecode
        if self.previous_environment is None:
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            os.environ["PYTHONDONTWRITEBYTECODE"] = self.previous_environment
        for module in (
            "bytecode_child",
            "bytecode_helper",
            "test_bytecode_suppression",
        ):
            sys.modules.pop(module, None)

    def test_bytecode_is_suppressed_in_process_and_in_children(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tests = Path(directory)
            Path(tests, "__init__.py").touch()
            Path(tests, "bytecode_helper.py").write_text(
                "VALUE = 'in-process'\n",
                encoding="utf-8",
            )
            Path(tests, "bytecode_child.py").write_text(
                "VALUE = 'child'\n",
                encoding="utf-8",
            )
            Path(tests, "test_bytecode_suppression.py").write_text(
                "import os\n"
                "from pathlib import Path\n"
                "import subprocess\n"
                "import sys\n"
                "import unittest\n"
                "import bytecode_helper\n\n"
                "class BytecodeSuppression(unittest.TestCase):\n"
                "    def test_runner_and_child(self):\n"
                "        self.assertTrue(sys.dont_write_bytecode)\n"
                "        self.assertEqual(\n"
                "            '1', os.environ.get('PYTHONDONTWRITEBYTECODE')\n"
                "        )\n"
                "        subprocess.run(\n"
                "            [\n"
                "                sys.executable,\n"
                "                '-c',\n"
                "                (\n"
                "                    'import os, bytecode_child; '\n"
                "                    \"assert os.environ.get(\"\n"
                "                    \"'PYTHONDONTWRITEBYTECODE') == '1'\"\n"
                "                ),\n"
                "            ],\n"
                "            cwd=Path(__file__).parent,\n"
                "            check=True,\n"
                "        )\n",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = load_runner().main([directory])

            self.assertEqual(0, result)
            self.assertTrue(sys.dont_write_bytecode)
            self.assertEqual("1", os.environ.get("PYTHONDONTWRITEBYTECODE"))
            self.assertEqual([], list(tests.rglob("*.pyc")))
            self.assertEqual([], list(tests.rglob("__pycache__")))

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
