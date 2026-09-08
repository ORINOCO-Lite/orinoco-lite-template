from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DefaultRenderTests(unittest.TestCase):
    def test_default_render_builds_and_serves_every_navigation_route(self) -> None:
        """A default Copier render is a deployable starter site."""

        with tempfile.TemporaryDirectory(prefix="orinoco-template-default-") as temp:
            rendered = Path(temp) / "consumer"
            self.run_command(
                [
                    sys.executable,
                    "tools/render_template.py",
                    "--destination",
                    rendered.as_posix(),
                ],
                ROOT,
            )
            self.assertTrue(
                (rendered / "site-specific/content/explore.md").is_file()
            )
            self.run_command(["pixi", "run", "--frozen", "validate"], rendered)
            self.run_command(["pixi", "run", "--frozen", "build"], rendered)
            self.run_command(
                ["pixi", "run", "--frozen", "verify-local-preview"], rendered
            )

    def run_command(self, command: list[str], cwd: Path) -> None:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            self.fail(
                f"{' '.join(command)} failed with status {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
