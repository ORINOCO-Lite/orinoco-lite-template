from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


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
        self.previous_runtime = os.environ.pop("ORINOCO_RUNTIME_ROOT", None)
        sys.dont_write_bytecode = False

    def tearDown(self) -> None:
        sys.dont_write_bytecode = self.previous_dont_write_bytecode
        if self.previous_environment is None:
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            os.environ["PYTHONDONTWRITEBYTECODE"] = self.previous_environment
        if self.previous_runtime is None:
            os.environ.pop("ORINOCO_RUNTIME_ROOT", None)
        else:
            os.environ["ORINOCO_RUNTIME_ROOT"] = self.previous_runtime
        for module in (
            "bytecode_child",
            "bytecode_helper",
            "test_bytecode_suppression",
            "test_runtime_binding",
        ):
            sys.modules.pop(module, None)

    def run_with_verified_runtime(self, directory: str) -> int:
        runner = load_runner()
        runtime = Path(directory) / "verified-runtime"
        runtime.mkdir()
        (runtime / "runtime-manifest.json").write_text("{}\n", encoding="utf-8")
        with (
            patch.object(
                runner,
                "find_consumer_root",
                return_value=Path(directory),
            ),
            patch.object(
                runner,
                "verified_runtime_root",
                return_value=runtime,
            ),
        ):
            return runner.main([directory])

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
                result = self.run_with_verified_runtime(directory)

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
                result = self.run_with_verified_runtime(directory)
        self.assertEqual(1, result)

    def test_runtime_is_verified_and_exported_before_test_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "consumer"
            tests = root / "tests"
            runtime = root / "released-runtime"
            executable = root / "bin/orinoco"
            tests.mkdir(parents=True)
            runtime.mkdir()
            executable.parent.mkdir()
            (root / "orinoco.yaml").write_text(
                "contract_version: 2\n",
                encoding="utf-8",
            )
            (root / "orinoco.lock").write_text(
                "lock_version: 1\n",
                encoding="utf-8",
            )
            (runtime / "runtime-manifest.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (runtime / "schema-marker").write_text(
                "released runtime\n",
                encoding="utf-8",
            )
            (tests / "test_runtime_binding.py").write_text(
                "import os\n"
                "from pathlib import Path\n"
                "import unittest\n"
                "runtime = Path(os.environ['ORINOCO_RUNTIME_ROOT'])\n"
                "assert (runtime / 'schema-marker').read_text() == "
                "'released runtime\\n'\n"
                "class RuntimeBinding(unittest.TestCase):\n"
                "    def test_exact_runtime(self):\n"
                "        self.assertTrue(runtime.is_absolute())\n",
                encoding="utf-8",
            )
            invocation = root / "runtime-invocation"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import os\n"
                "from pathlib import Path\n"
                "import sys\n"
                "assert 'ORINOCO_RUNTIME_ROOT' not in os.environ\n"
                f"Path({str(invocation)!r}).write_text("
                "json.dumps(sys.argv[1:]) + '\\n')\n"
                f"print(json.dumps({{'root': {str(runtime)!r}}}))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            environment = {
                "PATH": os.fspath(executable.parent)
                + os.pathsep
                + os.environ.get("PATH", ""),
                "ORINOCO_RUNTIME_ROOT": os.fspath(root / "stale-runtime"),
            }

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.dict(os.environ, environment),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = load_runner().main(
                    [os.fspath(tests), "--root", os.fspath(root)]
                )
                exported_runtime = os.environ.get("ORINOCO_RUNTIME_ROOT")

            self.assertEqual(0, result, stdout.getvalue() + stderr.getvalue())
            self.assertEqual(
                [
                    "--root",
                    os.fspath(root.resolve()),
                    "runtime",
                    "verify",
                    "--json",
                ],
                json.loads(invocation.read_text(encoding="utf-8")),
            )
            self.assertEqual(
                runtime.resolve(),
                Path(exported_runtime or ""),
            )

    def test_runner_contains_no_sibling_engineering_fallback(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("orinoco-lite-dev", source)
        self.assertNotIn("ROOT.parent", source)
        self.assertIn('"runtime", "verify", "--json"', source)

    def test_missing_site_test_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(
            io.StringIO()
        ) as stderr:
            result = load_runner().main([str(Path(directory, "missing"))])
        self.assertEqual(2, result)
        self.assertIn("Consumer test directory is missing", stderr.getvalue())
