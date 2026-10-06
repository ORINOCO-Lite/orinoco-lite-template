from __future__ import annotations

from html.parser import HTMLParser
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

import pytest


ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = set()
        self.ids = set()
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == "a":
            self.links.add(values.get("href"))
        self.ids.add(values.get("id"))


@pytest.mark.integration
class DefaultRenderTests(unittest.TestCase):
    def test_default_render_builds_and_serves_every_navigation_route(self) -> None:
        """An ordinary starter site uses the bundled tools and selected upstream directly."""

        with tempfile.TemporaryDirectory(prefix="orinoco-template-default-") as temp:
            trap_dir = Path(temp) / "no-annex"
            trap_dir.mkdir()
            self.annex_invoked = trap_dir / "invoked"
            executable = trap_dir / "git-annex"
            executable.write_text(
                "#!/bin/sh\n"
                f"touch {shlex.quote(str(self.annex_invoked))}\n"
                'echo "Unexpected git-annex invocation in an ordinary downstream" >&2\n'
                "exit 99\n"
            )
            executable.chmod(0o755)
            self.command_env = {
                **os.environ,
                "PATH": f"{trap_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            }
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
            # Images are ordinary site inputs; generated metadata supplies the pages.
            portrait = rendered / "site-specific/content/persons/starter-person/portrait.svg"
            portrait.parent.mkdir(parents=True)
            portrait.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="12" fill="teal"/></svg>')
            self.assertFalse(list((rendered / "site-specific/content").rglob("_index.md")))
            self.run_command(["git", "init"], rendered)
            self.run_command(
                ["git", "config", "user.email", "template@example.invalid"],
                rendered,
            )
            self.run_command(
                ["git", "config", "user.name", "Template Test"], rendered
            )
            self.run_command(["git", "add", "."], rendered)
            self.run_command(["git", "commit", "-m", "initial render"], rendered)
            if revision := os.environ.get("ORINOCO_TEST_PACKAGE_REVISION"):
                self.run_command(["pixi", "run", "orinoco-lite", "package", "update", "--revision", revision], rendered)
                self.run_command(["git", "add", "pixi.toml", "pixi.lock"], rendered)
                self.run_command(["git", "commit", "-m", "test: select package candidate"], rendered)
            self.run_command(["pixi", "run", "--locked", "orinoco-lite", "validate"], rendered)
            self.run_command(["pixi", "run", "--locked", "build"], rendered)
            self.run_command(
                ["pixi", "run", "--locked", "orinoco-lite", "verify-site", "build/site"], rendered
            )
            # Installed builds need the selected upstream, not another package checkout.
            source = rendered / ".orinoco-lite/www-from-model"
            self.assertFalse((rendered / ".orinoco").exists())
            self.run_command(["git", "check-ignore", str(source)], rendered)
            self.assertTrue((source / "themes/congo/theme.toml").is_file())
            self.assertFalse((source / "src/orinoco_lite").exists())
            self.assertFalse((source / "submodules/www-from-model").exists())
            site = rendered / "build/site"
            home = (site / "index.html").read_text()
            main = re.search(r"<main\b[^>]*>(.*?)</main>", home, re.S).group(1)
            self.assertEqual(main.count("A site built with Orinoco Lite."), 1)
            self.assertNotIn("Not your ordinary theme!", home)
            for section, record, title in (
                ("persons", "starter-person", "Starter Person"),
                ("projects", "starter-project", "Starter Project"),
                ("publications", "starter-publication", "Starter Publication"),
            ):
                self.assertIn(f"/{section}/", Page(home).links)
                listing = (site / section / "index.html").read_text()
                self.assertIn(f'/{section}/{record}/', listing)
                page = (site / section / record / "index.html").read_text()
                self.assertIn(title, page)
            self.assertIn('/persons/starter-person/', (site / 'projects/starter-project/index.html').read_text())
            self.assertIn('/projects/starter-project/', (site / 'persons/starter-person/index.html').read_text())
            self.assertIn('/publications/starter-publication/', (site / 'persons/starter-person/index.html').read_text())
            self.assertIn('/persons/starter-person/portrait.svg', (site / 'persons/index.html').read_text())
            self.assertEqual((site / 'persons/starter-person/portrait.svg').read_bytes(), portrait.read_bytes())
            graph = json.loads((site / "graph.json").read_text())
            self.assertTrue(any(edge["source"] == "xyzrins:." and edge["target"] == "xyzrins:persons/starter-person" for edge in graph["edges"]))

            # Whole-file overrides replace the default body, while metadata pages remain.
            content = rendered / "site-specific/content"
            (content / "_index.md").write_text("---\ntitle: Authored home\nparams:\n  hideGraph: true\n---\nUnique authored introduction.\n")
            (content / "persons/_index.md").write_text("---\ntitle: Our people\n---\nUnique authored section.\n")
            self.run_command(["git", "add", "site-specific/content"], rendered)
            self.run_command(["git", "commit", "-m", "test: author homepage and section overrides"], rendered)
            self.run_command(["pixi", "run", "--locked", "build"], rendered)
            home = (site / "index.html").read_text()
            self.assertIn("Unique authored introduction.", home)
            self.assertNotIn("sigma-container", Page(home).ids)
            self.assertIn("Unique authored section.", (site / "persons/index.html").read_text())
            self.assertIn("Starter Person", (site / "persons/starter-person/index.html").read_text())


    def run_command(self, command: list[str], cwd: Path) -> None:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=self.command_env,
            text=True,
            capture_output=True,
            check=False,
        )
        # Detect calls even when application code ignores the trap's exit status.
        self.assertFalse(self.annex_invoked.exists(), "Ordinary downstream invoked git-annex")
        if result.returncode:
            self.fail(
                f"{' '.join(command)} failed with status {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
