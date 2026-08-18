from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "github-template"


def load_runtime_preparer():
    path = ROOT / ".orinoco-lite" / "tools" / "prepare_browser_runtime.py"
    spec = importlib.util.spec_from_file_location("prepare_browser_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BrowserRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preparer = load_runtime_preparer()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="orinoco-browser-runtime-test-"
        )
        self.browser = Path(self.temporary.name) / "browser"
        self.browser.mkdir()
        self.calls: list[tuple[list[str], Path, float, str]] = []

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def successful_runner(self, command, cwd, timeout_seconds, label) -> int:
        self.calls.append((list(command), cwd, timeout_seconds, label))
        return 0

    def test_browser_download_prepares_both_binaries_from_project_root(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.preparer.prepare_browser_binaries(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                timeout_seconds=73,
                runner=self.successful_runner,
            )

        self.assertEqual(
            [
                (
                    [
                        "npx",
                        "--prefix",
                        "browser",
                        "playwright",
                        "install",
                        "--only-shell",
                        "chromium",
                        "webkit",
                    ],
                    Path(self.temporary.name).resolve(),
                    73,
                    "Chromium headless-shell and WebKit download",
                ),
            ],
            self.calls,
        )
        logs = output.getvalue()
        self.assertIn("starting Chromium headless-shell and WebKit download", logs)
        self.assertIn("completed Chromium headless-shell and WebKit download", logs)

    def test_linux_host_phase_is_separate_and_webkit_only(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.preparer.prepare_linux_host_dependencies(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                system="Linux",
                timeout_seconds=41,
                runner=self.successful_runner,
            )

        self.assertEqual(
            [
                (
                    [
                        "npx",
                        "--prefix",
                        "browser",
                        "playwright",
                        "install-deps",
                        "webkit",
                    ],
                    Path(self.temporary.name).resolve(),
                    41,
                    "Linux WebKit host dependencies",
                )
            ],
            self.calls,
        )
        self.assertIn("starting Linux WebKit host dependencies", output.getvalue())
        self.assertIn("completed Linux WebKit host dependencies", output.getvalue())

    def test_darwin_host_phase_is_an_explicit_noop(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.preparer.prepare_linux_host_dependencies(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                system="Darwin",
                runner=self.successful_runner,
            )

        self.assertEqual([], self.calls)
        self.assertIn("skipped on Darwin", output.getvalue())

    def test_linux_dependency_failure_is_visible(self) -> None:
        with self.assertRaisesRegex(
            self.preparer.BrowserRuntimeError,
            "Linux WebKit host dependencies failed with status 23",
        ):
            self.preparer.prepare_linux_host_dependencies(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                system="Linux",
                runner=lambda command, cwd, timeout, label: 23,
            )

    def test_unsupported_platform_fails_without_running_a_command(self) -> None:
        with self.assertRaisesRegex(
            self.preparer.BrowserRuntimeError,
            "unsupported browser test platform: Windows",
        ):
            self.preparer.prepare_linux_host_dependencies(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                system="Windows",
                runner=self.successful_runner,
            )
        self.assertEqual([], self.calls)

    def test_non_finite_timeout_fails_without_running_a_command(self) -> None:
        with self.assertRaisesRegex(
            self.preparer.BrowserRuntimeError,
            "phase timeout must be a finite number greater than zero",
        ):
            self.preparer.prepare_browser_binaries(
                Path("browser"),
                project_directory=Path(self.temporary.name),
                timeout_seconds=float("nan"),
                runner=self.successful_runner,
            )
        self.assertEqual([], self.calls)

    def test_subprocess_timeout_is_bounded_and_visible(self) -> None:
        started = time.monotonic()
        with self.assertRaisesRegex(
            self.preparer.BrowserRuntimeError,
            "timeout probe exceeded its 0.05-second timeout",
        ):
            self.preparer.bounded_subprocess_runner(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                self.browser,
                0.05,
                "timeout probe",
                termination_grace_seconds=0.05,
            )
        self.assertLess(time.monotonic() - started, 2)


if __name__ == "__main__":
    unittest.main()
