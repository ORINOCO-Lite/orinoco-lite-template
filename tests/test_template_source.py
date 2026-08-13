from __future__ import annotations

import hashlib
import inspect
import json
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


class TemplateSourceTests(unittest.TestCase):
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
            "metadata/records",
            "metadata/reference",
            "metadata/provenance",
            "editorial",
            "assets",
            "site/config",
            "site/layouts",
            "site/static",
            "integrations",
            "extensions",
        ):
            files = [
                path
                for path in (destination / root).rglob("*")
                if path.is_file() and path.name != ".gitkeep"
            ]
            self.assertEqual([], files, root)

        browser_files = [
            path
            for path in (destination / "tests" / "browser").rglob("*")
            if path.is_file()
        ] if (destination / "tests" / "browser").is_dir() else []
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
        self.assertEqual("v0.1.7", answers["_commit"])
        self.assertEqual("v0.1.7", answers["template_version"])

    def test_rendered_configuration_loads_with_the_actual_engine(self) -> None:
        script = """
from pathlib import Path
from orinoco_lite.config import load_config_path
root = Path(__import__('sys').argv[1])
workspace = load_config_path(root / 'orinoco.yaml')
assert workspace.path('canonical').resolve() == (root / 'metadata' / 'records').resolve()
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
        self.assertNotIn(
            "github.event_name == 'workflow_dispatch' ||",
            pages,
        )
        self.assertEqual(
            pages.count(
                "github.ref == format('refs/heads/{0}', "
                "github.event.repository.default_branch)"
            ),
            2,
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

    def test_bundle_import_preserves_full_scope_and_rejects_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            consumer = workspace / "consumer"
            shutil.copytree(ROOT / "github-template", consumer)
            bundle = workspace / "bundle"
            (bundle / "metadata" / "records").mkdir(parents=True)
            (bundle / "editorial").mkdir()
            (bundle / "generated" / "projection").mkdir(parents=True)
            (bundle / "tests" / "parity").mkdir(parents=True)
            (bundle / "tests" / "offline").mkdir(parents=True)
            (bundle / "site" / "framework" / "themes" / "congo" / ".github" / "workflows").mkdir(
                parents=True
            )
            (bundle / "metadata" / "records" / "all.yml").write_text(
                "pid: example:all\n", encoding="utf-8"
            )
            (bundle / "editorial" / "index.md").write_text(
                "# Complete site\n", encoding="utf-8"
            )
            (bundle / "generated" / "projection" / "records.jsonl").write_text(
                '{"pid":"example:all"}\n', encoding="utf-8"
            )
            (bundle / "tests" / "parity" / "test_full_site.py").write_text(
                "# Site-owned parity proof.\n", encoding="utf-8"
            )
            (bundle / "tests" / "offline" / "test_no_network.py").write_text(
                "# Site-owned offline proof.\n", encoding="utf-8"
            )
            (
                bundle
                / "site"
                / "framework"
                / "themes"
                / "congo"
                / ".github"
                / "workflows"
                / "theme.yml"
            ).write_text("name: inert theme metadata\n", encoding="utf-8")
            declared_paths = [
                "metadata/records/all.yml",
                "editorial/index.md",
                "generated/projection/records.jsonl",
                "tests/parity/test_full_site.py",
                "tests/offline/test_no_network.py",
                "site/framework/themes/congo/.github/workflows/theme.yml",
            ]
            classifications = {
                path: (
                    "generated"
                    if path.startswith("generated/")
                    else "consumer_tests"
                    if path.startswith("tests/")
                    else "initialized_site_owned"
                )
                for path in declared_paths
            }
            digests = {
                path: hashlib.sha256((bundle / path).read_bytes()).hexdigest()
                for path in declared_paths
            }
            sizes = {path: (bundle / path).stat().st_size for path in declared_paths}
            bundle_manifest = {
                "format": "orinoco-site-bundle-v1",
                "source": {
                    "repository": "https://example.invalid/full-site",
                    "commit": "a" * 40,
                    "scope": "full",
                },
                "files": digests,
                "classifications": classifications,
                "sizes": sizes,
                "summary": {
                    "bytes": sum(sizes.values()),
                    "classes": {
                        "consumer_tests": 2,
                        "generated": 1,
                        "initialized_site_owned": 3,
                    },
                    "files": 6,
                },
            }
            manifest_text = json.dumps(bundle_manifest, indent=2, sort_keys=True) + "\n"
            (bundle / "orinoco-site-bundle.json").write_text(
                manifest_text, encoding="utf-8"
            )
            command = [
                "python",
                "tools/import_site_bundle.py",
                bundle.as_posix(),
                "--source-repository",
                "https://example.invalid/full-site",
                "--source-commit",
                "a" * 40,
                "--scope",
                "full",
            ]
            env = dict(os.environ, SOURCE_DATE_EPOCH="0")
            result = subprocess.run(
                command,
                cwd=consumer,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(
                "pid: example:all\n",
                (consumer / "metadata" / "records" / "all.yml").read_text(),
            )
            self.assertEqual(
                '{"pid":"example:all"}\n',
                (
                    consumer / "generated" / "projection" / "records.jsonl"
                ).read_text(),
            )
            self.assertTrue(
                (consumer / "tests" / "parity" / "test_full_site.py").is_file()
            )
            self.assertTrue(
                (consumer / "tests" / "offline" / "test_no_network.py").is_file()
            )
            self.assertEqual(
                "name: inert theme metadata\n",
                (
                    consumer
                    / "site"
                    / "framework"
                    / "themes"
                    / "congo"
                    / ".github"
                    / "workflows"
                    / "theme.yml"
                ).read_text(encoding="utf-8"),
            )
            self.assertEqual(
                manifest_text,
                (consumer / "orinoco-site-bundle.json").read_text(encoding="utf-8"),
            )
            ledgers = list((consumer / "metadata" / "provenance").glob("site-import-*.json"))
            self.assertEqual(1, len(ledgers))
            ledger = json.loads(ledgers[0].read_text())
            self.assertEqual("full", ledger["source"]["scope"])
            self.assertEqual(6, ledger["source"]["declared_files"])
            self.assertEqual(6, len(ledger["files"]))
            preserved = json.loads(
                (consumer / "orinoco-site-bundle.json").read_text(encoding="utf-8")
            )
            self.assertEqual(6, preserved["summary"]["files"])
            self.assertEqual(
                set(preserved["files"]),
                {entry["path"] for entry in ledger["files"]},
            )
            self.assertNotIn(
                ledgers[0].relative_to(consumer).as_posix(), preserved["files"]
            )
            self.assertNotIn("pixi.toml", preserved["files"])

            stale = workspace / "stale-summary"
            shutil.copytree(bundle, stale)
            stale_manifest = json.loads(
                (stale / "orinoco-site-bundle.json").read_text(encoding="utf-8")
            )
            stale_manifest["summary"]["files"] = 7
            (stale / "orinoco-site-bundle.json").write_text(
                json.dumps(stale_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            rejected_summary = subprocess.run(
                command[:2]
                + [stale.as_posix()]
                + command[3:]
                + ["--replace"],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(0, rejected_summary.returncode)
            self.assertIn("summary.files must be 6", rejected_summary.stderr)

            forbidden = workspace / "forbidden"
            forbidden.mkdir()
            (forbidden / ".gitmodules").write_text("forbidden\n")
            rejected = subprocess.run(
                command[:2] + [forbidden.as_posix()] + command[3:] + ["--replace"],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("forbidden", rejected.stderr)

            root_workflow = workspace / "root-workflow"
            (root_workflow / ".github" / "workflows").mkdir(parents=True)
            (root_workflow / ".github" / "workflows" / "attack.yml").write_text(
                "name: forbidden root workflow\n", encoding="utf-8"
            )
            rejected_workflow = subprocess.run(
                command[:2]
                + [root_workflow.as_posix()]
                + command[3:]
                + ["--replace"],
                cwd=consumer,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(0, rejected_workflow.returncode)
            self.assertIn("forbidden root workflow", rejected_workflow.stderr)


if __name__ == "__main__":
    unittest.main()
