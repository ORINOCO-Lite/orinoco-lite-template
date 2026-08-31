from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
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
    def test_maintenance_skill_uses_the_downstream_ownership_contract(self) -> None:
        relative = Path(".agents/skills/maintain-orinoco-site/SKILL.md")
        source = ROOT / "copier-template" / relative
        rendered = ROOT / "github-template" / relative
        text = source.read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])

        self.assertEqual("maintain-orinoco-site", frontmatter["name"])
        self.assertIn("preserving site-owned data", frontmatter["description"])
        for required in (
            ".orinoco-lite/template-ownership.yml",
            ".copier-answers.yml",
            "orinoco.lock",
            "pixi run update-check",
            "pixi run update-orinoco -- ...",
            "pixi run test-all",
            "$manage-orinoco-content",
            "$operate-orinoco-metadata-adapters",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertEqual(source.read_bytes(), rendered.read_bytes())

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

    def test_default_tree_has_generic_framework_and_no_site_content(self) -> None:
        destination = ROOT / "github-template"
        self.assertFalse((destination / ".gitmodules").exists())
        self.assertTrue((destination / ".orinoco-lite/site/themes/congo").is_dir())
        self.assertTrue((destination / ".orinoco-lite/source-adapters").is_dir())
        self.assertTrue((destination / "site-specific/site.yaml").is_file())
        self.assertTrue((destination / "site-specific/projection.yaml").is_file())
        self.assertTrue(
            (destination / "site-specific/static/manifest.yaml").is_file()
        )
        for obsolete in ("metadata", "custom", "site", "source-adapters"):
            self.assertFalse((destination / obsolete).exists(), obsolete)
        self.assertFalse((destination / "site-specific/metadata/records").exists())
        self.assertFalse((destination / "site-specific/metadata/records/.gitkeep").exists())

        site = yaml.safe_load(
            (destination / "site-specific/site.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            {
                "version",
                "record_prefix",
                "identity",
                "language",
                "author",
                "theme",
                "navigation",
                "people",
                "projects",
                "webmanifest",
            },
            set(site),
        )
        self.assertEqual("people", site["navigation"]["main"][1]["page_ref"])
        content_templates = destination / ".orinoco-lite/site/content-templates"
        self.assertTrue((content_templates / "people.md.j2").is_file())
        self.assertFalse((content_templates / "people-groups.md.j2").exists())

    def test_vendored_framework_retains_licenses_and_excludes_pro_assets(self) -> None:
        destination = ROOT / "github-template"
        congo = destination / ".orinoco-lite/site/themes/congo"
        self.assertTrue((congo / "LICENSE").is_file())
        self.assertFalse((congo / "assets/icons/line.svg").exists())
        sharing = (congo / "data/sharing.json").read_text(encoding="utf-8")
        self.assertNotIn('"line"', sharing)
        notices_path = destination / ".orinoco-lite/THIRD_PARTY_NOTICES.md"
        notices = notices_path.read_text(encoding="utf-8")
        self.assertIn("site/themes/congo/LICENSE", notices)
        self.assertIn("Font Awesome Pro `line.svg`", notices)
        ownership = yaml.safe_load(
            (destination / ".orinoco-lite/template-ownership.yml").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(
            ".orinoco-lite/site/**",
            ownership["classes"]["template_owned"]["paths"],
        )
        self.assertIn(
            "LICENSE*",
            ownership["classes"]["site_policy"]["paths"],
        )
        source_notices = (ROOT / "LICENSES.md").read_text(encoding="utf-8")
        self.assertIn(
            "copier-template/.orinoco-lite/site/themes/congo/LICENSE",
            source_notices,
        )
        self.assertIn("Font Awesome Pro", source_notices)

    def test_structured_list_and_term_presentation_is_implemented(self) -> None:
        framework = ROOT / "github-template/.orinoco-lite/site"
        taxonomy = (framework / "layouts/taxonomy.html").read_text(
            encoding="utf-8"
        )
        term = (framework / "layouts/term.html").read_text(encoding="utf-8")
        self.assertEqual(
            taxonomy,
            (framework / "layouts/_default/orinoco-taxonomy.html").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            term,
            (framework / "layouts/_default/orinoco-term.html").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn(".Params.list_variant", taxonomy)
        self.assertIn(".Params.filter_fields", taxonomy)
        self.assertIn(".Params.search_fields", taxonomy)
        self.assertIn("taxonomy-list-grid.html", taxonomy)
        self.assertIn("taxonomy-list-vertical.html", taxonomy)
        self.assertIn(".depiction_type", term)
        self.assertIn(".person_display", term)
        self.assertIn(".show_relations", term)
        self.assertIn("limitGraphRootNodeId", term)
        self.assertIn(
            "layout: orinoco-term",
            (framework / "projection-templates/page.md.j2").read_text(
                encoding="utf-8"
            ),
        )
        self.assertTrue((framework / "static/orinoco-list.js").is_file())
        self.assertTrue((framework / "static/orinoco-list.css").is_file())

    def test_source_adapter_canary_is_offline_and_part_of_full_validation(self) -> None:
        destination = ROOT / "github-template"
        canary = (
            destination
            / ".orinoco-lite/source-adapters/tests/test_metadata_review_canary.py"
        )
        self.assertTrue(canary.is_file())
        text = canary.read_text(encoding="utf-8")
        self.assertNotIn("urlopen", text)
        self.assertNotIn("requests", text)
        pixi = tomllib.loads((destination / "pixi.toml").read_text(encoding="utf-8"))
        self.assertIn(
            "source-adapter-canary",
            pixi["tasks"]["test-all"]["depends-on"],
        )
        adapter_pixi = tomllib.loads(
            (
                destination
                / ".orinoco-lite/source-adapters/metadata/pixi.toml"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn("test", adapter_pixi["tasks"])

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
        self.assertEqual(
            "gh:ORINOCO-Lite/orinoco-lite-template", answers["_src_path"]
        )
        self.assertEqual("v0.2.0rc17", answers["_commit"])
        self.assertEqual("v0.2.0rc17", answers["template_version"])

    def test_rendered_readme_preserves_markdown_structure(self) -> None:
        readme = (ROOT / "github-template" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("```console\npixi run validate\n", readme)
        self.assertIn("\npixi run update-check\n```", readme)
        self.assertEqual(2, len(re.findall(r"^- .*Orinoco Lite", readme, re.M)))
        self.assertGreaterEqual(len(re.findall(r"^- `", readme, re.M)), 9)

    def test_rendered_configuration_loads_with_the_actual_engine(self) -> None:
        script = """
from pathlib import Path
from orinoco_lite.config import load_config_path
root = Path(__import__('sys').argv[1])
workspace = load_config_path(root / 'orinoco.yaml')
assert workspace.path('records').resolve() == (root / 'site-specific' / 'metadata' / 'records').resolve()
assert workspace.path('framework').resolve() == (root / '.orinoco-lite' / 'site').resolve()
assert workspace.path('source_adapters').resolve() == (root / '.orinoco-lite' / 'source-adapters').resolve()
"""
        environment = dict(os.environ, PIXI_FROZEN="true", PIXI_NO_CONFIG="true")
        configured_source = environment.get("ORINOCO_ENGINE_SOURCE")
        pixi = shutil.which("pixi")
        self.assertIsNotNone(
            pixi,
            "Pixi is required for the engine configuration smoke test",
        )
        if configured_source:
            engine_source = Path(configured_source).resolve()
            self.assertTrue(engine_source.is_dir(), engine_source)
            environment["PYTHONPATH"] = engine_source.as_posix()
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

    def test_static_editor_submission_coordinates_are_build_derived(self) -> None:
        source = (ROOT / "copier-template" / "orinoco.yaml.jinja").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("repository:", source)
        self.assertNotIn("curation_service:", source)
        copier = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
        self.assertNotIn("repository_slug", copier)
        configuration = yaml.safe_load(
            (ROOT / "github-template" / "orinoco.yaml").read_text(encoding="utf-8")
        )
        self.assertNotIn("repository", configuration["site"])
        self.assertNotIn("curation_service", configuration["site"])
        builder = (
            ROOT
            / "copier-template"
            / ".orinoco-lite"
            / "tools"
            / "build_pages.py"
        ).read_text(encoding="utf-8")
        self.assertIn('os.environ.get("GITHUB_REPOSITORY"', builder)
        self.assertIn('"--github-repository"', builder)
        ownership = (
            ROOT / "copier-template" / "docs" / "ownership.md"
        ).read_text(encoding="utf-8")
        self.assertIn("site's own static `/review/` route", ownership)
        self.assertIn("not another review page", ownership)

    def test_custom_domain_and_curation_defaults_are_documented(self) -> None:
        guidance = (
            ROOT / "github-template" / "docs" / "custom-domain.md"
        ).read_text(encoding="utf-8")
        self.assertIn("dedicated custom domain is the normal", guidance)
        self.assertIn("Browsers isolate origins, not URL paths", guidance)
        self.assertIn("shows a clear warning", guidance)
        self.assertIn("does not require a checkbox or acknowledgment", guidance)
        self.assertIn("**Download bundle** always remains available", guidance)
        self.assertIn("central Orinoco Lite service at", guidance)
        self.assertIn("https://orinoco-curation-review.pages.dev", guidance)
        self.assertIn("site.curation_service", guidance)
        self.assertNotIn("site.repository", guidance)
        self.assertIn("keep the verification TXT record", guidance)
        self.assertIn("neither needs nor tracks a `CNAME` file", guidance)
        self.assertIn("**Enforce HTTPS**", guidance)

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

    def test_exact_hugo_pin_satisfies_the_runtime_manifest(self) -> None:
        pixi = shutil.which("pixi")
        self.assertIsNotNone(pixi, "Pixi is required for the runtime contract test")
        rendered = ROOT / "github-template"
        manifest = rendered / "pixi.toml"
        environment = dict(os.environ, PIXI_FROZEN="true", PIXI_NO_CONFIG="true")
        environment.pop("PYTHONPATH", None)
        preflight = """
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tomllib
from orinoco_lite.cli import main
from orinoco_lite.site import _preflight_hugo
from packaging.specifiers import Specifier
from packaging.version import Version

workspace = Path(sys.argv[1])
manifest = Path(sys.argv[2])
stdout = StringIO()
with redirect_stdout(stdout):
    assert main(["--root", str(workspace), "runtime", "verify", "--json"]) == 0
runtime = json.loads(stdout.getvalue())
declared = tomllib.loads(manifest.read_text(encoding="utf-8"))["dependencies"]["hugo"]
specifier = Specifier(declared)
assert specifier.operator == "==" and "*" not in specifier.version
expected = Version(specifier.version)
actual = _preflight_hugo(Path(runtime["root"]), cwd=workspace)
assert actual == expected, (actual, expected, runtime["manifest_sha256"])
print(json.dumps({"declared": declared, "resolved": str(actual)}))
"""
        with tempfile.TemporaryDirectory(prefix="orinoco-runtime-contract-") as name:
            workspace = Path(name)
            configuration = yaml.safe_load(
                (rendered / "orinoco.yaml").read_text(encoding="utf-8")
            )
            # This test proves only the currently released runtime's Hugo pin.
            # Candidate-only path keys have their own configuration smoke test.
            configuration["paths"].pop("framework", None)
            (workspace / "orinoco.yaml").write_text(
                yaml.safe_dump(configuration, sort_keys=False),
                encoding="utf-8",
            )
            shutil.copy2(rendered / "orinoco.lock", workspace / "orinoco.lock")
            compatible = subprocess.run(
                [
                    str(pixi),
                    "run",
                    "--manifest-path",
                    manifest.as_posix(),
                    "python",
                    "-c",
                    preflight,
                    workspace.as_posix(),
                    manifest.as_posix(),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(
            0,
            compatible.returncode,
            compatible.stdout + compatible.stderr,
        )
        proof = json.loads(compatible.stdout)
        self.assertEqual(f"=={proof['resolved']}", proof["declared"])

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

    def test_manual_validation_selects_full_or_joined_scope(self) -> None:
        workflow = (
            ROOT / "github-template" / ".github" / "workflows" / "validate.yml"
        ).read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)
        validation = document["on"]["workflow_dispatch"]["inputs"]["validation"]
        self.assertEqual(
            {
                "description": "Validation scope",
                "required": "true",
                "default": "full",
                "type": "choice",
                "options": ["full", "joined"],
            },
            validation,
        )

        jobs = document["jobs"]
        for name in ("macos", "linux"):
            with self.subTest(job=name):
                self.assertEqual("test-all", jobs[name]["with"]["command"])
                self.assertIn("github.event_name == 'pull_request'", jobs[name]["if"])
                self.assertIn(
                    "!startsWith(github.event.pull_request.head.ref, "
                    "'automation/curation/')",
                    jobs[name]["if"],
                )
                self.assertIn("github.event_name == 'push'", jobs[name]["if"])
                self.assertIn("inputs.validation == 'full'", jobs[name]["if"])
        joined = jobs["linux-joined"]
        self.assertEqual("Validate joined graph (Linux x86-64)", joined["name"])
        self.assertEqual("validate", joined["with"]["command"])
        self.assertEqual("ubuntu-24.04", joined["with"]["runner"])
        self.assertIn("inputs.validation == 'joined'", joined["if"])
        self.assertNotIn("pull_request", joined["if"])
        self.assertNotIn("artifact-name", joined["with"])
        self.assertNotIn("concurrency:", workflow)
        self.assertNotIn("cancel-in-progress", workflow)

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
                "site-specific/metadata/overlays/annotations/XYZProject/example.yaml",
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
