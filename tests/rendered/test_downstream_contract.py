from __future__ import annotations

import importlib.util
import importlib
import io
import json
import tempfile
import sys
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[2] / "github-template"
TOOLS = ROOT / ".orinoco-lite" / "tools"
sys.path.insert(0, TOOLS.as_posix())


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_template_ownership", TOOLS / "verify_template_ownership.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DownstreamContractTests(unittest.TestCase):
    def test_repository_has_no_submodule_contract(self) -> None:
        self.assertFalse((ROOT / ".gitmodules").exists())

    def test_every_checked_path_has_unambiguous_ownership(self) -> None:
        failures = load_verifier().verify(ROOT)
        self.assertEqual([], failures, "\n".join(failures))

    def test_site_owned_paths_are_present(self) -> None:
        for path in (
            ".orinoco-lite/provenance",
            "custom/editorial",
            "custom/assets",
            "site",
            "source-adapters",
            "extensions",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_dir())

        self.assertFalse((ROOT / "metadata").exists())
        self.assertFalse((ROOT / "metadata/records/.gitkeep").exists())

    def test_offline_acceptance_is_site_owned(self) -> None:
        verifier = load_verifier()
        ownership = verifier.load_yaml(ROOT / ".orinoco-lite/template-ownership.yml")
        classes = verifier.ownership_classes(ownership)
        self.assertEqual(
            ["consumer_tests"],
            verifier.classify(
                ".orinoco-lite/tests/offline/test_no_network.py", classes
            ),
        )
        self.assertEqual(
            ["initialized_site_owned"],
            verifier.classify(".orinoco-lite/provenance/external.json", classes),
        )
        self.assertEqual(
            ["initialized_site_owned"],
            verifier.classify("source-adapters/zotero/config.toml", classes),
        )

    def test_engine_configuration_uses_the_supported_path_contract(self) -> None:
        configuration = yaml.safe_load(
            (ROOT / "orinoco.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(2, configuration["contract_version"])
        self.assertEqual(
            {
                "name": "Orinoco Lite Site",
                "description": "A site built with Orinoco Lite.",
                "base_url": "https://example.invalid/orinoco-site/",
                "repository": "example/orinoco-site",
                "curation_service": "https://orinoco-curation-review.pages.dev",
            },
            configuration["site"],
        )
        self.assertEqual(
            {
                "records": "metadata/records",
                "provenance": ".orinoco-lite/provenance",
                "editorial": "custom/editorial",
                "assets": "custom/assets",
                "site": "site",
                "source_adapters": "source-adapters",
                "generated": "generated",
                "extensions": "extensions",
                "build": "build",
            },
            configuration["paths"],
        )

        # Run the actual engine loader when this downstream suite is executing
        # in the locked Orinoco environment. The structural assertions above
        # remain active in content-neutral template-source tests, where the
        # unpublished fail-closed wheel is intentionally unavailable.
        try:
            config_module = importlib.import_module("orinoco_lite.config")
        except ModuleNotFoundError:
            return
        loader = next(
            (
                getattr(config_module, name)
                for name in (
                    "load_config_path",
                    "load_config",
                    "load_site_config",
                    "load_configuration",
                )
                if hasattr(config_module, name)
            ),
            None,
        )
        if loader is None:
            self.fail("orinoco_lite.config exposes no supported configuration loader")
        loaded = loader(ROOT / "orinoco.yaml")
        self.assertIsNotNone(loaded)

    def test_complete_gate_includes_browser_and_deterministic_acceptance(self) -> None:
        pixi = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        self.assertEqual("==0.161.1", pixi["dependencies"]["hugo"])
        tasks = pixi["tasks"]
        self.assertEqual(
            "mkdir -p generated && orinoco projection update",
            tasks["projection-update"],
        )
        self.assertEqual(
            {"depends-on": ["projection-update"], "cmd": "orinoco projection verify"},
            tasks["projection-verify"],
        )
        self.assertEqual(
            {"depends-on": ["projection-update"], "cmd": "orinoco validate"},
            tasks["validate"],
        )
        self.assertEqual("orinoco assets hydrate", tasks["assets-hydrate"])
        self.assertEqual("orinoco assets verify", tasks["assets-verify"])
        self.assertEqual(
            ["assets-hydrate"],
            tasks["assets-prepare-online"]["depends-on"],
        )
        self.assertEqual(
            "orinoco assets verify",
            tasks["assets-prepare-online"]["cmd"],
        )
        self.assertIn("projection-verify", tasks["test-all"]["depends-on"])
        self.assertIn("assets-prepare-online", tasks["test-all"]["depends-on"])
        self.assertNotIn("assets-verify", tasks["test-all"]["depends-on"])
        self.assertIn("test-browser", tasks["test-all"]["depends-on"])
        self.assertIn("verify-build", tasks["test-all"]["depends-on"])
        self.assertIn("verify-hugo", tasks["test-all"]["depends-on"])
        self.assertEqual(
            "python .orinoco-lite/tools/run_consumer_tests.py",
            tasks["test-consumer"],
        )
        self.assertEqual(["build"], tasks["verify-local-preview"]["depends-on"])
        self.assertEqual(
            "python .orinoco-lite/tools/verify_local_preview.py build/site",
            tasks["verify-local-preview"]["cmd"],
        )
        self.assertEqual(
            ["verify-deterministic", "verify-local-preview"],
            tasks["verify-build"]["depends-on"],
        )
        self.assertEqual(
            "python .orinoco-lite/tools/install_browser_tests.py",
            tasks["install-browser-tests"],
        )
        self.assertEqual(
            ["install-browser-tests"],
            tasks["prepare-browser-binaries"]["depends-on"],
        )
        self.assertEqual(
            "python .orinoco-lite/tools/prepare_browser_runtime.py browsers",
            tasks["prepare-browser-binaries"]["cmd"],
        )
        self.assertEqual(
            {"PLAYWRIGHT_BROWSERS_PATH": "build/playwright-browsers"},
            tasks["prepare-browser-binaries"]["env"],
        )
        self.assertNotIn("install-browser-chromium", tasks)
        self.assertNotIn("install-browser-webkit", tasks)
        self.assertEqual(
            ["build-browser-pages", "prepare-browser-binaries"],
            tasks["test-browser-chromium"]["depends-on"],
        )
        self.assertEqual(
            "npm --prefix .orinoco-lite/tests/browser test -- --project=chromium",
            tasks["test-browser-chromium"]["cmd"],
        )
        self.assertEqual(
            ["test-browser-chromium"],
            tasks["prepare-browser-webkit-host"]["depends-on"],
        )
        self.assertEqual(
            "python .orinoco-lite/tools/prepare_browser_runtime.py "
            "linux-host-dependencies",
            tasks["prepare-browser-webkit-host"]["cmd"],
        )
        self.assertNotIn("env", tasks["prepare-browser-webkit-host"])
        self.assertEqual(
            ["prepare-browser-webkit-host"],
            tasks["test-browser-webkit"]["depends-on"],
        )
        self.assertEqual(
            "npm --prefix .orinoco-lite/tests/browser test -- --project=webkit",
            tasks["test-browser-webkit"]["cmd"],
        )
        self.assertEqual(
            {"depends-on": ["test-browser-webkit"]},
            tasks["test-browser"],
        )

    def test_browser_installer_respects_the_ownership_boundary(self) -> None:
        verifier = load_verifier()
        ownership = verifier.load_yaml(ROOT / ".orinoco-lite/template-ownership.yml")
        classes = verifier.ownership_classes(ownership)
        self.assertEqual(
            ["template_owned"],
            verifier.classify(".orinoco-lite/tools/install_browser_tests.py", classes),
        )
        self.assertEqual(
            ["template_owned"],
            verifier.classify(
                ".orinoco-lite/tools/prepare_browser_runtime.py", classes
            ),
        )
        for relative in (
            ".orinoco-lite/tests/browser/package.json",
            ".orinoco-lite/tests/browser/package-lock.json",
        ):
            with self.subTest(path=relative):
                self.assertEqual(
                    ["consumer_tests"],
                    verifier.classify(relative, classes),
                )
        package = json.loads(
            (ROOT / ".orinoco-lite/tests/browser/package.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("1.62.1", package["devDependencies"]["@playwright/test"])

    def test_local_build_is_host_neutral_and_pages_paths_stay_explicit(self) -> None:
        pixi = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        tasks = pixi["tasks"]
        self.assertEqual(
            "orinoco build --destination build/site --base-url /",
            tasks["build"]["cmd"],
        )
        self.assertEqual(["projection-update"], tasks["build"]["depends-on"])
        self.assertEqual(
            "orinoco build --destination build/site-repeat --base-url /",
            tasks["build-repeat"]["cmd"],
        )
        self.assertEqual(["projection-update"], tasks["build-repeat"]["depends-on"])
        self.assertIn("--port 8765", tasks["serve"])
        self.assertEqual(
            "python .orinoco-lite/tools/build_pages.py build/pages",
            tasks["build-pages"]["cmd"],
        )
        self.assertEqual(["projection-update"], tasks["build-pages"]["depends-on"])
        self.assertRegex(
            tasks["build-browser-pages"]["cmd"],
            r"--base-url http://127\.0\.0\.1:8766/[^/]+/$",
        )
        self.assertEqual(
            ["projection-update"], tasks["build-browser-pages"]["depends-on"]
        )

        verifier = load_verifier()
        ownership = verifier.load_yaml(ROOT / ".orinoco-lite/template-ownership.yml")
        classes = verifier.ownership_classes(ownership)
        self.assertEqual(
            ["template_owned"],
            verifier.classify(".orinoco-lite/tools/verify_local_preview.py", classes),
        )
        self.assertEqual(
            ["template_owned"],
            verifier.classify(".orinoco-lite/tools/build_pages.py", classes),
        )

    def test_pages_builder_expands_and_validates_the_environment_url(self) -> None:
        builder = load_tool("build_pages")
        with (
            patch.dict(
                builder.os.environ,
                {"ORINOCO_BASE_URL": "https://con.github.io/example"},
                clear=False,
            ),
            patch.object(builder.subprocess, "run") as run,
        ):
            self.assertEqual(0, builder.main(["build/pages"]))
        run.assert_called_once_with(
            [
                "orinoco",
                "build",
                "--destination",
                "build/pages",
                "--base-url",
                "https://con.github.io/example/",
            ],
            check=True,
        )

        with patch.dict(builder.os.environ, {"ORINOCO_BASE_URL": ""}, clear=False):
            with self.assertRaisesRegex(SystemExit, r"absolute HTTP\(S\) URL"):
                builder.main(["build/pages"])

    def test_hugo_verifier_accepts_distribution_revisions_strictly(self) -> None:
        verifier = load_tool("verify_hugo")

        def invoke(output: str) -> tuple[int, str, str]:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(
                    verifier.shutil,
                    "which",
                    return_value="/usr/bin/hugo",
                ),
                patch.object(
                    verifier.subprocess,
                    "run",
                    return_value=SimpleNamespace(returncode=0, stdout=output),
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                status = verifier.main(["--version", "0.161.1", "--extended"])
            return status, stdout.getvalue(), stderr.getvalue()

        accepted = (
            "hugo v0.161.1-conda-forge+extended linux/amd64 "
            "BuildDate=unknown VendorInfo=conda-forge",
            "hugo v0.161.1+extended darwin/arm64 BuildDate=unknown VendorInfo=brew",
        )
        for output in accepted:
            with self.subTest(output=output):
                status, stdout, stderr = invoke(output)
                self.assertEqual(0, status, stderr)
                self.assertEqual(output + "\n", stdout)

        rejected = (
            (
                "wrong version",
                "hugo v0.161.0-conda-forge+extended linux/amd64",
                1,
                "expected Hugo 0.161.1, found 0.161.0",
            ),
            (
                "standard edition",
                "hugo v0.161.1-conda-forge linux/amd64",
                1,
                "Hugo Extended is required",
            ),
            (
                "empty revision",
                "hugo v0.161.1-+extended linux/amd64",
                2,
                "cannot parse Hugo version",
            ),
            (
                "invalid revision",
                "hugo v0.161.1-conda_forge+extended linux/amd64",
                2,
                "cannot parse Hugo version",
            ),
            (
                "dangling variant",
                "hugo v0.161.1-conda-forge+extended+ linux/amd64",
                2,
                "cannot parse Hugo version",
            ),
        )
        for label, output, expected_status, message in rejected:
            with self.subTest(label=label):
                status, stdout, stderr = invoke(output)
                self.assertEqual(expected_status, status)
                self.assertEqual("", stdout)
                self.assertIn(message, stderr)

    def test_runtime_state_is_wholly_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".orinoco/", ignore)
        self.assertNotIn("!.orinoco/downloads/", ignore)

    def test_engine_digest_uses_pixi_direct_url_schema(self) -> None:
        pixi = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
        engine = yaml.safe_load((ROOT / "orinoco.lock").read_text(encoding="utf-8"))[
            "engine"
        ]
        requirement = pixi["pypi-dependencies"]["orinoco-lite"]["url"]
        self.assertEqual(f"{engine['url']}#sha256={engine['sha256']}", requirement)
        lock = yaml.safe_load((ROOT / "pixi.lock").read_text(encoding="utf-8"))
        matches = [
            package
            for package in lock["packages"]
            if package.get("name") == "orinoco-lite"
        ]
        self.assertEqual(1, len(matches))
        self.assertEqual(engine["version"], matches[0]["version"])
        self.assertEqual("direct+" + requirement, matches[0]["pypi"])

    def test_workflows_use_the_lock_generator_pixi_version(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        for name in ("pages.yml", "update-orinoco.yml", "validate.yml"):
            text = (workflows / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertIn("pixi-version: v0.73.0", text)

    def test_consumer_workflow_jobs_are_inert_in_template_repository(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        for name in ("pages.yml", "update-orinoco.yml", "validate.yml"):
            document = yaml.safe_load((workflows / name).read_text(encoding="utf-8"))
            for job_name, job in document["jobs"].items():
                with self.subTest(workflow=name, job=job_name):
                    self.assertIn(
                        "github.repository != 'ORINOCO-Lite/orinoco-lite-template'",
                        str(job.get("if", "")),
                    )

    def test_pages_deploys_and_records_the_destination_default_branch(self) -> None:
        workflow_text = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("\n  workflow_dispatch:\n", workflow_text)
        self.assertIn(
            "github.event_name == 'workflow_dispatch' ||",
            workflow_text,
        )
        self.assertEqual(
            workflow_text.count(
                "github.ref == format('refs/heads/{0}', "
                "github.event.repository.default_branch)"
            ),
            1,
        )
        lock = yaml.safe_load((ROOT / "orinoco.lock").read_text(encoding="utf-8"))
        pages_ref = (
            f"{lock['workflow']['repository']}/.github/workflows/"
            f"orinoco-pages.yml@{lock['workflow']['sha']}"
        )
        self.assertIn(f"uses: {pages_ref}", workflow_text)
        self.assertIn("contents: write", workflow_text)
        self.assertIn("pages: write", workflow_text)
        self.assertIn(
            f"workflow-repository: {lock['workflow']['repository']}", workflow_text
        )
        self.assertIn(f"workflow-sha: {lock['workflow']['sha']}", workflow_text)

    def test_update_workflow_commit_has_required_agent_attribution(self) -> None:
        workflow_path = ROOT / ".github" / "workflows" / "update-orinoco.yml"
        workflow_text = workflow_path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        self.assertIn("\n  workflow_dispatch:\n", workflow_text)
        self.assertNotIn("\n  schedule:\n", workflow_text)
        self.assertNotIn("cron:", workflow_text)
        pull_request = workflow["jobs"]["update"]["steps"][-1]
        self.assertEqual(
            "chore(deps): update Orinoco framework\n\n"
            "Co-Authored-By: Codex CLI 0.143.0 / GPT 5.6-sol "
            "<codex@openai.com>\n",
            pull_request["with"]["commit-message"],
        )
        self.assertTrue(
            pull_request["with"]["body"].startswith(
                "**AI-generated draft — not reviewed by John**\n"
            )
        )

    def test_deterministic_comparator_uses_exact_inventory_and_digests(self) -> None:
        comparator = load_tool("verify_deterministic_build")
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            first = workspace / "first"
            second = workspace / "second"
            first.mkdir()
            second.mkdir()
            (first / "index.html").write_bytes(b"same\n")
            (second / "index.html").write_bytes(b"same\n")
            manifest, differences = comparator.compare(first, second)
            self.assertEqual([], differences)
            self.assertEqual(1, manifest["file_count"])
            self.assertEqual(64, len(manifest["tree_sha256"]))
            (second / "index.html").write_bytes(b"different\n")
            _, differences = comparator.compare(first, second)
            self.assertEqual(["index.html"], differences)


if __name__ == "__main__":
    unittest.main()
