from __future__ import annotations

import subprocess
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class TemplateArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            ["python", "tools/render_github_template.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def test_complete_website_is_template_owned(self) -> None:
        root = ROOT / "github-template/.orinoco-lite/site"
        for relative in (
            "config-templates/hugo.toml.j2",
            "layouts/term.html",
            "projection-templates/project.md.j2",
            "projection-tools/pool2graph.py",
            "themes/congo/theme.toml",
        ):
            self.assertTrue((root / relative).is_file(), relative)

    def test_only_forward_looking_downstream_surfaces_are_materialized(self) -> None:
        root = ROOT / "github-template"
        for relative in ("site-specific", "extensions"):
            self.assertTrue((root / relative).is_dir(), relative)
        for retired in ("custom", "metadata", "site", "source-adapters"):
            self.assertFalse((root / retired).exists(), retired)
        self.assertFalse((root / ".github/workflows/update-orinoco.yml").exists())
        self.assertFalse((root / ".orinoco-lite/tools/update_orinoco.py").exists())

    def test_site_specific_contract_has_no_website_implementation(self) -> None:
        root = ROOT / "github-template/site-specific"
        forbidden = {"archetypes", "layouts", "themes"}
        self.assertFalse(forbidden & {path.name for path in root.iterdir()})
        self.assertTrue((root / "overrides/layouts/.gitkeep").is_file())
        projection = yaml.safe_load((root / "projection.yaml").read_text())
        templates = [projection["homepage"]["template"]]
        templates.extend(entry["template"] for entry in projection["pages"].values())
        self.assertTrue(
            all(value.startswith(".orinoco-lite/site/projection-templates/") for value in templates)
        )

    def test_default_is_generic_and_contains_no_german_site_material(self) -> None:
        root = ROOT / "github-template"
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for base in (root / ".orinoco-lite/site", root / "site-specific")
            for path in base.rglob("*")
            if path.is_file() and path.stat().st_size < 2_000_000
        )
        for marker in (
            "Psychoinformatics",
            "Forschungszentrum Jülich",
            "psychoinformatics.de",
            "www-draft.psychoinformatics.de",
        ):
            self.assertNotIn(marker, text)

    def test_checked_default_tree_matches_copier_source(self) -> None:
        result = subprocess.run(
            ["python", "tools/render_github_template.py", "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
