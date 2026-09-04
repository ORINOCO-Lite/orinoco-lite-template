from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class TemplateArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="orinoco-template-architecture-"
        )
        temporary = Path(cls.temporary.name)
        cls.rendered = temporary / "consumer"
        data_file = temporary / "answers.yml"
        data_file.write_text(
            yaml.safe_dump(
                {
                    "project_slug": "delta-atlas",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                "tools/render_github_template.py",
                "--destination",
                cls.rendered.as_posix(),
                "--data-file",
                data_file.as_posix(),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_site_yaml_is_the_only_persisted_identity(self) -> None:
        config = yaml.safe_load(
            (self.rendered / "orinoco.yaml").read_text(encoding="utf-8")
        )
        site = yaml.safe_load(
            (self.rendered / "site-specific/site.yaml").read_text(
                encoding="utf-8"
            )
        )
        answers = yaml.safe_load(
            (self.rendered / ".copier-answers.yml").read_text(encoding="utf-8")
        )

        self.assertNotIn("site", config)
        self.assertEqual("Orinoco Lite Site", site["identity"]["title"])
        self.assertEqual(
            "A site built with Orinoco Lite.",
            site["identity"]["description"],
        )
        self.assertEqual(
            "https://example.invalid/delta-atlas/",
            site["identity"]["base_url"],
        )
        self.assertEqual("delta-atlas", answers["project_slug"])
        self.assertIsInstance(answers["_src_path"], str)
        self.assertIsInstance(answers["_commit"], str)

    def test_consumer_surfaces_are_forward_looking_and_small(self) -> None:
        for relative in ("site-specific", "extensions"):
            self.assertTrue((self.rendered / relative).is_dir(), relative)
        for retired in ("custom", "metadata", "site", "source-adapters"):
            self.assertFalse((self.rendered / retired).exists(), retired)
        self.assertFalse(
            (self.rendered / ".github/workflows/update-orinoco.yml").exists()
        )
        self.assertFalse(
            (self.rendered / ".orinoco-lite/tools/update_orinoco.py").exists()
        )

    def test_presentation_is_an_adapter_not_a_copied_website(self) -> None:
        presentation = self.rendered / ".orinoco-lite/presentation"
        self.assertLessEqual(
            {"config-templates", "layouts", "static-templates"},
            {path.name for path in presentation.iterdir()},
        )
        for relative in (
            "config-templates/hugo.toml.j2",
            "static-templates/site.webmanifest.j2",
        ):
            self.assertTrue((presentation / relative).is_file(), relative)
        forbidden_names = {
            "archetypes",
            "assets",
            "projection-templates",
            "projection-tools",
            "themes",
        }
        self.assertFalse(
            forbidden_names
            & {path.name for path in presentation.rglob("*") if path.is_dir()}
        )
        self.assertLessEqual(
            len([path for path in presentation.rglob("*") if path.is_file()]),
            20,
        )

        private_root = self.rendered / ".orinoco-lite"
        for copied_tree in ("site", "themes", "framework", "upstream"):
            self.assertFalse((private_root / copied_tree).exists(), copied_tree)
        self.assertFalse(
            any(path.name == "themes" for path in private_root.rglob("*"))
        )

    def test_materialized_presentation_is_a_bounded_licensed_overlay(self) -> None:
        private_root = self.rendered / ".orinoco-lite"
        overlay = private_root / "materialized-presentation"
        upstream = overlay / "upstream"

        self.assertTrue(upstream.is_dir())
        self.assertTrue((overlay / "LICENSE").read_text(encoding="utf-8").strip())
        self.assertFalse(any(path.is_symlink() for path in overlay.rglob("*")))

        ownership = yaml.safe_load(
            (private_root / "template-ownership.yml").read_text(encoding="utf-8")
        )
        self.assertIn(
            ".orinoco-lite/**",
            ownership["classes"]["template_owned"]["paths"],
        )

    def test_private_namespace_is_exclusively_template_owned(self) -> None:
        ownership = yaml.safe_load(
            (
                self.rendered / ".orinoco-lite/template-ownership.yml"
            ).read_text(encoding="utf-8")
        )
        classes = ownership["classes"]

        self.assertIn(".orinoco-lite/**", classes["template_owned"]["paths"])
        for name, entry in classes.items():
            if name == "template_owned":
                continue
            self.assertFalse(
                any(path.startswith(".orinoco-lite/") for path in entry["paths"]),
                name,
            )

        copier = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
        self.assertFalse(
            any(path.startswith(".orinoco-lite/") for path in copier["_skip_if_exists"])
        )

    def test_package_is_the_only_presentation_pin_authority(self) -> None:
        config = yaml.safe_load(
            (self.rendered / "orinoco.yaml").read_text(encoding="utf-8")
        )
        lock = yaml.safe_load(
            (self.rendered / "orinoco.lock").read_text(encoding="utf-8")
        )

        self.assertNotIn("framework", config["paths"])
        self.assertNotIn("website", lock)
        self.assertNotIn("presentation", lock)
        self.assertEqual(
            {"package", "lock_version", "template", "workflow"},
            set(lock),
        )
        for configuration in (
            "orinoco.yaml",
            "orinoco.lock",
            "pixi.toml",
            ".copier-answers.yml",
        ):
            text = (self.rendered / configuration).read_text(encoding="utf-8")
            self.assertNotIn("www-from-model", text)
            self.assertNotIn("congo", text.lower())

    def test_package_coordinates_match_the_frozen_environment(self) -> None:
        helper = self.rendered / ".orinoco-lite/tools/template_contract.py"
        spec = importlib.util.spec_from_file_location("template_contract", helper)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(contract)
        package = yaml.safe_load(
            (self.rendered / "orinoco.lock").read_text(encoding="utf-8")
        )["package"]

        self.assertEqual(
            [], contract.pixi_package_pin_failures(self.rendered, package)
        )
        wrong_version = {**package, "version": "0.0.0"}
        self.assertTrue(
            contract.pixi_package_pin_failures(self.rendered, wrong_version)
        )
        wrong_digest = {**package, "sha256": "0" * 64}
        self.assertTrue(
            contract.pixi_package_pin_failures(self.rendered, wrong_digest)
        )

    def test_no_generic_projection_or_record_is_materialized(self) -> None:
        site_specific = self.rendered / "site-specific"
        self.assertFalse((site_specific / "projection.yaml").exists())
        records = site_specific / "metadata/records"
        self.assertEqual(
            [".gitkeep"],
            sorted(path.name for path in records.iterdir() if path.is_file()),
        )

    def test_rendered_output_is_build_state_not_source_state(self) -> None:
        tracked = subprocess.run(
            [
                "git",
                "ls-files",
                "--",
                "github-template",
                ".github-template-answers.yml",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        self.assertEqual([], tracked)
        self.assertIn("build/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_renderer_cannot_replace_template_source(self) -> None:
        destination = ROOT / "copier-template/rendered-output"
        result = subprocess.run(
            [
                sys.executable,
                "tools/render_github_template.py",
                "--destination",
                destination.as_posix(),
                "--replace",
                "--skip-lock-check",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("must be under build/", result.stderr)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
