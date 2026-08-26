from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_renderer():
    path = ROOT / "tools" / "render_github_template.py"
    spec = importlib.util.spec_from_file_location("render_github_template", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateSourceTests(unittest.TestCase):
    def test_downstream_skills_separate_content_from_adapter_curation(self) -> None:
        skills = ROOT / "copier-template" / ".agents" / "skills"
        content = (skills / "manage-orinoco-content" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        adapters = (
            skills / "operate-orinoco-metadata-adapters" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("$operate-orinoco-metadata-adapters", content)
        self.assertIn("decision-only", adapters)
        self.assertIn("pull request", adapters)
        self.assertIn("orinoco.lock", adapters)
        self.assertIn("Remote latest is advisory", adapters)

    def test_render_comparison_ignores_only_declared_runtime_state(self) -> None:
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rendered = root / "rendered"
            checked = root / "checked"
            rendered.mkdir()
            checked.mkdir()
            (rendered / ".orinoco-lite").mkdir()
            (checked / ".orinoco-lite").mkdir()
            for relative in (
                ".orinoco/runtime/cache",
                ".pixi/envs/default",
                ".orinoco-lite/state/update",
                "build/site",
                "generated/projection",
                "node_modules/package",
                "playwright-report/results",
                "test-results/browser",
            ):
                path = checked / relative
                path.mkdir(parents=True)
                (path / "ignored.txt").write_text("runtime\n", encoding="utf-8")

            self.assertEqual([], renderer.differences(rendered, checked))
            (checked / "visible.txt").write_text("checked\n", encoding="utf-8")
            self.assertEqual(
                ["only checked: visible.txt"],
                renderer.differences(rendered, checked),
            )

    def test_checked_default_tree_matches_copier_source(self) -> None:
        renderer = (ROOT / "tools" / "render_github_template.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"--vcs-ref",\n        "HEAD",', renderer)
        result = subprocess.run(
            ["python", "tools/render_github_template.py", "--check"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_default_tree_is_content_neutral_and_submodule_free(self) -> None:
        destination = ROOT / "github-template"
        self.assertFalse((destination / ".gitmodules").exists())
        for root in (
            ".orinoco-lite/provenance",
            "custom/editorial",
            "custom/assets",
            "site/config",
            "site/layouts",
            "site/static",
            "source-adapters",
            "extensions",
        ):
            files = [
                path
                for path in (destination / root).rglob("*")
                if path.is_file() and path.name != ".gitkeep"
            ]
            self.assertEqual([], files, root)

        self.assertFalse((destination / "metadata").exists())
        self.assertFalse((destination / "metadata/records/.gitkeep").exists())

        browser_files = [
            path
            for path in (destination / ".orinoco-lite" / "tests" / "browser").rglob("*")
            if path.is_file()
        ] if (destination / ".orinoco-lite" / "tests" / "browser").is_dir() else []
        self.assertTrue(browser_files)
        browser_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in browser_files
            if path.suffix in {".json", ".md", ".mjs"}
        )
        self.assertNotIn("Center for Open Neuroscience", browser_text)
        self.assertNotIn("xyzrins:", browser_text)

    def test_default_answers_point_to_a_versioned_remote_source(self) -> None:
        answers = yaml.safe_load(
            (ROOT / "github-template" / ".copier-answers.yml").read_text()
        )
        self.assertEqual("gh:con/orinoco-lite-template", answers["_src_path"])
        self.assertEqual("v0.2.0rc7", answers["_commit"])
        self.assertEqual("v0.2.0rc7", answers["template_version"])

    def test_rendered_configuration_loads_with_the_actual_engine(self) -> None:
        script = """
from pathlib import Path
from orinoco_lite.config import load_config_path
root = Path(__import__('sys').argv[1])
workspace = load_config_path(root / 'orinoco.yaml')
assert workspace.path('records').resolve() == (root / 'metadata' / 'records').resolve()
assert workspace.path('source_adapters').resolve() == (root / 'source-adapters').resolve()
"""
        environment = dict(os.environ, PIXI_FROZEN="true", PIXI_NO_CONFIG="true")
        configured_source = environment.get("ORINOCO_ENGINE_SOURCE")
        if configured_source:
            engine_source = Path(configured_source).resolve()
            self.assertTrue(engine_source.is_dir(), engine_source)
            environment["PYTHONPATH"] = engine_source.as_posix()
            command = [
                sys.executable,
                "-c",
                script,
                (ROOT / "github-template").as_posix(),
            ]
        else:
            pixi = shutil.which("pixi")
            self.assertIsNotNone(
                pixi,
                "Pixi is required for the released-engine smoke test",
            )
            command = [
                str(pixi),
                "run",
                "--manifest-path",
                (ROOT / "github-template" / "pixi.toml").as_posix(),
                "python",
                "-c",
                script,
                (ROOT / "github-template").as_posix(),
            ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_hosted_engine_smoke_does_not_require_a_sibling_checkout(self) -> None:
        source = inspect.getsource(
            self.test_rendered_configuration_loads_with_the_actual_engine
        )
        self.assertNotIn("ROOT.parent", source)
        self.assertNotIn("LOCAL_ENGINE_SOURCE", source)
        self.assertIn('"--manifest-path",', source)
        self.assertIn('PIXI_FROZEN="true"', source)

    def test_default_coordinates_are_concrete_published_release_pins(self) -> None:
        lock = yaml.safe_load((ROOT / "github-template" / "orinoco.lock").read_text())
        self.assertNotEqual({"0"}, set(lock["engine"]["sha256"]))
        self.assertNotEqual({"0"}, set(lock["runtime"]["sha256"]))
        self.assertNotEqual({"0"}, set(lock["runtime"]["manifest_sha256"]))
        self.assertNotEqual({"0"}, set(lock["workflow"]["sha"]))
        self.assertTrue((ROOT / "github-template" / "pixi.lock").is_file())

    def test_copier_first_defaults_match_the_checked_render_coordinates(self) -> None:
        answers = yaml.safe_load(
            (ROOT / ".github-template-answers.yml").read_text(encoding="utf-8")
        )
        configuration = yaml.safe_load(
            (ROOT / "copier.yml").read_text(encoding="utf-8")
        )
        coordinates = (
            "engine_version",
            "engine_url",
            "engine_sha256",
            "runtime_version",
            "runtime_url",
            "runtime_sha256",
            "runtime_manifest_sha256",
            "template_source",
            "template_version",
            "workflow_repository",
            "workflow_sha",
            "workflow_ref",
        )
        for coordinate in coordinates:
            with self.subTest(coordinate=coordinate):
                self.assertEqual(
                    answers[coordinate], configuration[coordinate]["default"]
                )

    def test_copier_first_creation_ships_the_reviewed_frozen_lock(self) -> None:
        source_lock = ROOT / "copier-template" / "pixi.lock"
        rendered_lock = ROOT / "github-template" / "pixi.lock"
        self.assertTrue(source_lock.is_file())
        self.assertEqual(source_lock.read_bytes(), rendered_lock.read_bytes())

    def test_consumer_workflows_follow_the_destination_default_branch(self) -> None:
        for name in ("validate.yml", "pages.yml"):
            workflow = (
                ROOT / "github-template" / ".github" / "workflows" / name
            ).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertIn("github.event.repository.default_branch", workflow)
                self.assertNotIn("branches: [main]", workflow)

        pages = (
            ROOT / "github-template" / ".github" / "workflows" / "pages.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "github.event_name == 'workflow_dispatch' ||",
            pages,
        )
        self.assertEqual(
            pages.count(
                "github.ref == format('refs/heads/{0}', "
                "github.event.repository.default_branch)"
            ),
            1,
        )

    def test_milestone_five_ownership_boundaries_are_explicit(self) -> None:
        from importlib.util import module_from_spec, spec_from_file_location

        path = ROOT / "github-template/.orinoco-lite/tools/template_contract.py"
        spec = spec_from_file_location("curation_template_contract", path)
        assert spec and spec.loader
        contract = module_from_spec(spec)
        spec.loader.exec_module(contract)
        ownership = contract.load_yaml(
            ROOT / "github-template/.orinoco-lite/template-ownership.yml"
        )
        classes = contract.ownership_classes(ownership)
        self.assertEqual(
            ["initialized_site_owned"],
            contract.classify(
                "metadata/overlays/annotations/XYZProject/example.yaml",
                classes,
            ),
        )
        self.assertEqual(
            ["initialized_site_owned"],
            contract.classify(".github/workflows/curation-review.yml", classes),
        )
        self.assertEqual(
            ["template_owned"],
            contract.classify(".github/workflows/shacl-vue-proposal.yml", classes),
        )

    def test_source_ci_covers_both_platforms_with_full_action_pins(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "source-ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("runner: macos-14", workflow)
        self.assertIn("runner: ubuntu-24.04", workflow)
        self.assertIn("pixi-version: v0.73.0", workflow)
        self.assertIn("run: pixi run check", workflow)
        references = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
        self.assertEqual(
            [
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "prefix-dev/setup-pixi@f00437f565399d418b0acc85936d12c1fb668347",
            ],
            references,
        )
        for reference in references:
            self.assertRegex(reference, r"@[0-9a-f]{40}$")

    def test_all_engine_runtime_state_is_untrackable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="orinoco-ignore-proof-") as temporary:
            consumer = Path(temporary)
            shutil.copy2(ROOT / "github-template" / ".gitignore", consumer / ".gitignore")
            run = subprocess.run
            initialized = run(
                ["git", "init", "-b", "main"],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            candidates = [
                ".orinoco/cache/cache.bin",
                ".orinoco/downloads/runtime.tar.gz",
                ".orinoco/runtime/runtime-manifest.json",
                ".orinoco-lite/state/framework-update.json",
                "generated/projection/records.jsonl",
            ]
            for relative in candidates:
                path = consumer / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"runtime state\n")
            ignored = run(
                ["git", "check-ignore", "--no-index", *candidates],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, ignored.returncode, ignored.stderr)
            self.assertEqual(candidates, ignored.stdout.splitlines())
            trackable = run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, trackable.returncode, trackable.stderr)
            self.assertNotIn(".orinoco/", trackable.stdout)



if __name__ == "__main__":
    unittest.main()
