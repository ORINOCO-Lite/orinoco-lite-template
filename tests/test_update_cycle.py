from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
INITIAL_ENGINE_URL = (
    "https://example.invalid/orinoco_lite-0.1.0-py3-none-any.whl"
)
TARGET_ENGINE_URL = (
    "https://example.invalid/orinoco_lite-0.1.1-py3-none-any.whl"
)
TARGET_RUNTIME_URL = "https://example.invalid/runtime-0.1.1.tar.gz"
TARGET_RUNTIME_SHA256 = "4" * 64
TARGET_RUNTIME_MANIFEST_SHA256 = "5" * 64
TARGET_WORKFLOW_SHA = "6" * 40
TARGET_WORKFLOW_REF = (
    "example/orinoco/.github/workflows/orinoco-consumer-ci.yml@"
    f"{TARGET_WORKFLOW_SHA}"
)
BOOTSTRAP_SOURCE_PATHS = (
    "copier-template/.github/workflows/pages.yml",
    "copier-template/.github/workflows/update-orinoco.yml",
    "copier-template/.github/workflows/validate.yml.jinja",
)
BOOTSTRAP_RENDERED_PATHS = (
    ".github/workflows/pages.yml",
    ".github/workflows/update-orinoco.yml",
    ".github/workflows/validate.yml",
)
BOOTSTRAP_EQUIVALENT_PATHS = (
    *BOOTSTRAP_RENDERED_PATHS,
    ".orinoco-lite/tools/update_orinoco.py",
)
TARGET_ADDED_SOURCE_PATHS = (
    "copier-template/.github/workflows/shacl-vue-proposal.yml",
    "copier-template/.orinoco-lite/tools/shacl_vue_handoff.py",
)
TARGET_ADDED_RENDERED_PATHS = tuple(
    path.removeprefix("copier-template/") for path in TARGET_ADDED_SOURCE_PATHS
)
TARGET_ADDED_WORKFLOW = ".github/workflows/shacl-vue-proposal.yml"
OLD_UPDATER_MARKER = "v0.1.0 updater requires reviewed bootstrap"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Orinoco Template Test",
    "GIT_AUTHOR_EMAIL": "template-test@example.invalid",
    "GIT_COMMITTER_NAME": "Orinoco Template Test",
    "GIT_COMMITTER_EMAIL": "template-test@example.invalid",
}


def run(
    command: list[str],
    cwd: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, **GIT_ENV, SOURCE_DATE_EPOCH="0")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def commit_all(repository: Path, message: str) -> str:
    run(["git", "add", "--all"], repository)
    run(["git", "commit", "-m", message], repository)
    return run(["git", "rev-parse", "HEAD"], repository).stdout.strip()


def replace_pixi_pin(path: Path, current: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated = text.replace(current, replacement)
    if updated == text:
        raise AssertionError(f"expected a Pixi version pin in {path}")
    path.write_text(updated, encoding="utf-8")


def protected_bytes(repository: Path) -> dict[str, bytes]:
    protected_roots = (
        "metadata",
        "custom",
        "site",
        "source-adapters",
        "extensions",
    )
    return {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for root in protected_roots
        for path in (repository / root).rglob("*")
        if path.is_file()
    }


def fake_pixi_executable(directory: Path) -> Path:
    executable = directory / "pixi"
    executable.write_text(
        """#!/usr/bin/env python3
import hashlib
import re
from pathlib import Path

import yaml

if __import__('sys').argv[1:] != ['lock']:
    raise SystemExit('fake pixi accepts only `pixi lock`')
root = Path.cwd()
manifest = (root / 'pixi.toml').read_text(encoding='utf-8')
match = re.search(r'^orinoco-lite = \\{ url = "([^"]+)" \\}$', manifest, re.MULTILINE)
if match is None:
    raise SystemExit('orinoco-lite URL is missing from pixi.toml')
requirement = match.group(1)
url, separator, declared_digest = requirement.partition('#sha256=')
if not separator or not re.fullmatch(r'[0-9a-f]{64}', declared_digest):
    raise SystemExit('orinoco-lite URL lacks an exact #sha256 fragment')
version = re.search(r'orinoco_lite-([0-9]+\\.[0-9]+\\.[0-9]+)-', url)
if version is None:
    raise SystemExit('cannot infer exact orinoco-lite version')
fixture = Path(__import__('os').environ['ORINOCO_TEST_ENGINE_WHEEL'])
observed_digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
if declared_digest != observed_digest:
    raise SystemExit('orinoco-lite wheel digest differs from URL fragment')
(root / 'pixi.lock').write_text(
    yaml.safe_dump(
        {
            'version': 7,
            'packages': [
                {
                    'pypi': 'direct+' + requirement,
                    'name': 'orinoco-lite',
                    'version': version.group(1),
                }
            ],
        },
        sort_keys=False,
    ),
    encoding='utf-8',
)
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


class UpdateCycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orinoco-update-test-")
        self.workspace = Path(self.temporary.name)
        self.template = self.workspace / "template"
        self.template.mkdir()
        shutil.copy2(ROOT / "copier.yml", self.template / "copier.yml")
        shutil.copytree(ROOT / "copier-template", self.template / "copier-template")
        self.target_added_files = {
            relative: (
                (self.template / relative).read_bytes(),
                (self.template / relative).stat().st_mode & 0o777,
            )
            for relative in TARGET_ADDED_SOURCE_PATHS
        }
        for relative in TARGET_ADDED_SOURCE_PATHS:
            (self.template / relative).unlink()
        updater = self.template / "copier-template/.orinoco-lite/tools/update_orinoco.py"
        self.target_updater = updater.read_bytes()
        updater.write_text(
            "#!/usr/bin/env python3\n"
            f"raise SystemExit({OLD_UPDATER_MARKER!r})\n",
            encoding="utf-8",
        )
        for relative in BOOTSTRAP_SOURCE_PATHS:
            replace_pixi_pin(
                self.template / relative,
                "pixi-version: v0.73.0",
                "pixi-version: 0.73.0",
            )
        run(["git", "init", "-b", "main"], self.template)
        self.template_v010_commit = commit_all(
            self.template, "feat: release template 0.1.0"
        )
        run(["git", "tag", "v0.1.0"], self.template)

        for relative, (content, mode) in self.target_added_files.items():
            path = self.template / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(mode)
        updater.write_bytes(self.target_updater)
        for relative in BOOTSTRAP_SOURCE_PATHS:
            path = self.template / relative
            text = path.read_text(encoding="utf-8")
            updated = text.replace(
                "pixi-version: 0.73.0",
                "pixi-version: v0.73.0",
            )
            self.assertNotEqual(text, updated, relative)
            path.write_text(updated, encoding="utf-8")

        readme = self.template / "copier-template" / "README.md.jinja"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "# [[ project_name ]]", "# [[ project_name ]] — updated"
            ),
            encoding="utf-8",
        )
        ownership_doc = self.template / "copier-template" / "docs" / "ownership.md"
        ownership_doc.write_text(
            ownership_doc.read_text(encoding="utf-8")
            + "\nTemplate release 0.1.1 clarifies conflict behavior.\n",
            encoding="utf-8",
        )
        self.template_v011_commit = commit_all(
            self.template, "docs: clarify update conflicts"
        )
        run(["git", "tag", "-a", "v0.1.1", "-m", "v0.1.1"], self.template)
        self.template_v011_tag_object = run(
            ["git", "rev-parse", "v0.1.1"], self.template
        ).stdout.strip()

        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\nExact intervening release state.\n",
            encoding="utf-8",
        )
        commit_all(self.template, "docs: release template 0.1.2")
        run(["git", "tag", "v0.1.2"], self.template)
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "Exact intervening release state.",
                "Exact target release state.",
            ),
            encoding="utf-8",
        )
        commit_all(self.template, "docs: release template 0.1.3")
        run(["git", "tag", "v0.1.3"], self.template)

        self.engine_wheel = self.workspace / "orinoco_lite-0.1.1-py3-none-any.whl"
        with zipfile.ZipFile(self.engine_wheel, "w") as archive:
            archive.writestr(
                "orinoco_lite-0.1.1.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: orinoco-lite\nVersion: 0.1.1\n",
            )
        self.engine_sha256 = hashlib.sha256(self.engine_wheel.read_bytes()).hexdigest()
        self.fake_bin = self.workspace / "fake-bin"
        self.fake_bin.mkdir()
        fake_pixi_executable(self.fake_bin)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_consumer(
        self,
        name: str,
        *,
        bootstrap_updater: bool = True,
    ) -> Path:
        consumer = self.workspace / name
        initial_sha = "3" * 40
        command = [
            "copier",
            "copy",
            "--quiet",
            "--defaults",
            "--overwrite",
            "--vcs-ref",
            "v0.1.0",
            "--data",
            "template_version=v0.1.0",
            "--data",
            "engine_version=0.1.0",
            "--data",
            f"engine_url={INITIAL_ENGINE_URL}",
            "--data",
            f"engine_sha256={'0' * 63}1",
            "--data",
            "runtime_version=0.1.0",
            "--data",
            "runtime_url=https://example.invalid/runtime-0.1.0.tar.gz",
            "--data",
            f"runtime_sha256={'1' * 64}",
            "--data",
            f"runtime_manifest_sha256={'2' * 64}",
            "--data",
            f"workflow_sha={initial_sha}",
            "--data",
            "workflow_ref=example/orinoco/.github/workflows/"
            f"orinoco-consumer-ci.yml@{initial_sha}",
            self.template.as_posix(),
            consumer.as_posix(),
        ]
        run(command, self.workspace)
        run(["git", "init", "-b", "main"], consumer)
        records = consumer / "metadata" / "records"
        extensions = consumer / "extensions"
        records.mkdir(parents=True)
        (records / "complete.yml").write_text(
            "pid: example:complete\ntitle: Site-owned content\n", encoding="utf-8"
        )
        (extensions / "custom.css").write_text(
            ":root { --site-accent: #123456; }\n", encoding="utf-8"
        )
        commit_all(consumer, "feat: add complete site and customization")
        if bootstrap_updater:
            self.bootstrap_target_updater(consumer)
        return consumer

    def bootstrap_target_updater(self, consumer: Path) -> None:
        updater = consumer / ".orinoco-lite/tools/update_orinoco.py"
        self.assertIn(OLD_UPDATER_MARKER, updater.read_text(encoding="utf-8"))
        updater.write_bytes(self.target_updater)
        self.assertEqual(self.target_updater, updater.read_bytes())
        commit_all(consumer, "chore: bootstrap reviewed framework updater")

    def preapply_bootstrap_edits(
        self,
        consumer: Path,
        *,
        pages_replacement: str = "pixi-version: v0.73.0",
    ) -> None:
        for relative in BOOTSTRAP_RENDERED_PATHS:
            path = consumer / relative
            replacement = (
                pages_replacement
                if relative == ".github/workflows/pages.yml"
                else "pixi-version: v0.73.0"
            )
            replace_pixi_pin(
                path,
                "pixi-version: 0.73.0",
                replacement,
            )
        commit_all(consumer, "chore: apply reviewed Pixi bootstrap")

    def update_command(self, *, skip_pixi_lock: bool = True) -> list[str]:
        command = [
            "python",
            ".orinoco-lite/tools/update_orinoco.py",
            "--to-template",
            "v0.1.1",
            "--to-engine",
            "0.1.1",
            "--engine-url",
            TARGET_ENGINE_URL,
            "--engine-sha256",
            self.engine_sha256,
            "--to-runtime",
            "0.1.1",
            "--runtime-url",
            TARGET_RUNTIME_URL,
            "--runtime-sha256",
            TARGET_RUNTIME_SHA256,
            "--runtime-manifest-sha256",
            TARGET_RUNTIME_MANIFEST_SHA256,
            "--workflow-sha",
            TARGET_WORKFLOW_SHA,
            "--workflow-ref",
            TARGET_WORKFLOW_REF,
        ]
        if skip_pixi_lock:
            command.append("--skip-pixi-lock")
        return command

    def test_update_records_coordinates_preserves_site_and_reverts_cleanly(self) -> None:
        consumer = self.make_consumer("success")
        baseline = run(["git", "rev-parse", "HEAD"], consumer).stdout.strip()
        record = (consumer / "metadata" / "records" / "complete.yml").read_bytes()
        extension = (consumer / "extensions" / "custom.css").read_bytes()

        result = run(self.update_command(), consumer, check=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        ledger = json.loads(
            (consumer / ".orinoco-lite" / "state" / "framework-update.json").read_text()
        )
        self.assertEqual("ready-for-review", ledger["status"])
        self.assertEqual("v0.1.0", ledger["previous"]["template"]["version"])
        self.assertEqual(
            self.template_v010_commit,
            ledger["previous"]["template"]["commit"],
        )
        self.assertEqual(
            "v0.1.0", ledger["previous"]["template"]["copier_ref"]
        )
        self.assertEqual("v0.1.1", ledger["target"]["template"]["version"])
        self.assertEqual(
            self.template_v011_commit,
            ledger["target"]["template"]["commit"],
        )
        self.assertNotEqual(
            self.template_v011_tag_object,
            ledger["target"]["template"]["commit"],
            "the ledger must record the peeled commit, not an annotated tag object",
        )
        self.assertEqual("v0.1.1", ledger["target"]["template"]["copier_ref"])
        self.assertEqual("0.1.0", ledger["previous"]["engine"]["version"])
        self.assertEqual("0.1.1", ledger["target"]["engine"]["version"])
        self.assertEqual("0.1.0", ledger["previous"]["runtime"]["version"])
        self.assertEqual("0.1.1", ledger["target"]["runtime"]["version"])
        self.assertEqual([], ledger["site_owned"]["changed"])
        self.assertEqual(record, (consumer / "metadata" / "records" / "complete.yml").read_bytes())
        self.assertEqual(extension, (consumer / "extensions" / "custom.css").read_bytes())
        self.assertGreater(ledger["site_owned"]["checked_files"], 0)
        self.assertNotIn("before", ledger["site_owned"])
        self.assertNotIn("after", ledger["site_owned"])
        self.assertIn("— updated", (consumer / "README.md").read_text())

        commit_all(consumer, "chore(deps): update Orinoco framework")
        run(["git", "revert", "--no-edit", "HEAD"], consumer)
        comparison = run(["git", "diff", "--quiet", baseline, "--", "."], consumer, check=False)
        self.assertEqual(0, comparison.returncode, "revert did not restore the baseline tree")

    def test_exact_target_coordinates_render_and_lock_together(self) -> None:
        consumer = self.make_consumer("real-lock")
        environment = dict(
            os.environ,
            **GIT_ENV,
            SOURCE_DATE_EPOCH="0",
            ORINOCO_TEST_ENGINE_WHEEL=self.engine_wheel.as_posix(),
            PATH=f"{self.fake_bin}{os.pathsep}{os.environ['PATH']}",
        )
        result = subprocess.run(
            self.update_command(skip_pixi_lock=False),
            cwd=consumer,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        manifest = tomllib.loads((consumer / "pixi.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            f"{TARGET_ENGINE_URL}#sha256={self.engine_sha256}",
            manifest["pypi-dependencies"]["orinoco-lite"]["url"],
        )
        answers = yaml.safe_load(
            (consumer / ".copier-answers.yml").read_text(encoding="utf-8")
        )
        lock = yaml.safe_load(
            (consumer / "orinoco.lock").read_text(encoding="utf-8")
        )
        pixi_lock = yaml.safe_load(
            (consumer / "pixi.lock").read_text(encoding="utf-8")
        )
        self.assertEqual("0.1.1", answers["engine_version"])
        self.assertEqual(TARGET_ENGINE_URL, answers["engine_url"])
        self.assertEqual(self.engine_sha256, answers["engine_sha256"])
        self.assertEqual("v0.1.1", answers["template_version"])
        self.assertEqual("v0.1.1", answers["_commit"])
        self.assertNotIn("template_commit", answers)
        self.assertEqual("0.1.1", answers["runtime_version"])
        self.assertEqual(TARGET_RUNTIME_URL, answers["runtime_url"])
        self.assertEqual(TARGET_RUNTIME_SHA256, answers["runtime_sha256"])
        self.assertEqual(
            TARGET_RUNTIME_MANIFEST_SHA256,
            answers["runtime_manifest_sha256"],
        )
        self.assertEqual("example/orinoco", answers["workflow_repository"])
        self.assertEqual(TARGET_WORKFLOW_SHA, answers["workflow_sha"])
        self.assertEqual(TARGET_WORKFLOW_REF, answers["workflow_ref"])
        self.assertEqual("0.1.1", lock["engine"]["version"])
        self.assertEqual(TARGET_ENGINE_URL, lock["engine"]["url"])
        self.assertEqual(self.engine_sha256, lock["engine"]["sha256"])
        self.assertEqual("v0.1.1", lock["template"]["version"])
        self.assertNotIn("commit", lock["template"])
        self.assertEqual("0.1.1", lock["runtime"]["version"])
        self.assertEqual(TARGET_RUNTIME_URL, lock["runtime"]["url"])
        self.assertEqual(TARGET_RUNTIME_SHA256, lock["runtime"]["sha256"])
        self.assertEqual(
            TARGET_RUNTIME_MANIFEST_SHA256,
            lock["runtime"]["manifest_sha256"],
        )
        self.assertEqual("example/orinoco", lock["workflow"]["repository"])
        self.assertEqual(TARGET_WORKFLOW_SHA, lock["workflow"]["sha"])
        self.assertEqual(TARGET_WORKFLOW_REF, lock["workflow"]["ref"])
        self.assertIn(
            f"uses: {TARGET_WORKFLOW_REF}",
            (
                consumer / ".github" / "workflows" / "validate.yml"
            ).read_text(encoding="utf-8"),
        )
        self.assertEqual(
            {
                "pypi": (
                    "direct+"
                    f"{TARGET_ENGINE_URL}#sha256={self.engine_sha256}"
                ),
                "name": "orinoco-lite",
                "version": "0.1.1",
            },
            pixi_lock["packages"][0],
        )

    def test_target_equivalent_bootstrap_edits_are_reconciled_safely(self) -> None:
        consumer = self.make_consumer("equivalent-bootstrap")
        before = protected_bytes(consumer)
        self.preapply_bootstrap_edits(consumer)

        result = run(self.update_command(), consumer, check=False)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual([], list(consumer.rglob("*.rej")))
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertEqual(
            list(BOOTSTRAP_EQUIVALENT_PATHS),
            ledger["reconciled_target_equivalent"],
        )
        self.assertEqual(before, protected_bytes(consumer))
        self.assertIn(
            TARGET_WORKFLOW_REF,
            (consumer / ".github/workflows/validate.yml").read_text(
                encoding="utf-8"
            ),
        )

    def test_exact_target_added_files_are_reconciled_safely(self) -> None:
        consumer = self.make_consumer("target-added-equivalent")
        before = protected_bytes(consumer)
        for source_relative, rendered_relative in zip(
            TARGET_ADDED_SOURCE_PATHS,
            TARGET_ADDED_RENDERED_PATHS,
            strict=True,
        ):
            source = self.template / source_relative
            destination = consumer / rendered_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            destination.chmod(source.stat().st_mode & 0o777)
        commit_all(consumer, "feat: preapply target SHACL support")

        result = run(self.update_command(), consumer, check=False)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual([], list(consumer.rglob("*.rej")))
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertEqual(
            list(TARGET_ADDED_RENDERED_PATHS),
            [
                path
                for path in ledger["reconciled_target_equivalent"]
                if path in TARGET_ADDED_RENDERED_PATHS
            ],
        )
        for source_relative, rendered_relative in zip(
            TARGET_ADDED_SOURCE_PATHS,
            TARGET_ADDED_RENDERED_PATHS,
            strict=True,
        ):
            self.assertEqual(
                (self.template / source_relative).read_bytes(),
                (consumer / rendered_relative).read_bytes(),
            )
        self.assertEqual(before, protected_bytes(consumer))

    def test_divergent_target_added_workflow_remains_a_conflict(self) -> None:
        consumer = self.make_consumer("target-added-divergent")
        source = self.template / f"copier-template/{TARGET_ADDED_WORKFLOW}"
        destination = consumer / TARGET_ADDED_WORKFLOW
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            source.read_bytes().replace(
                b"name: Materialize SHACL Vue proposal",
                b"name: Site-specific SHACL Vue proposal",
                1,
            )
        )
        commit_all(consumer, "feat: add divergent target workflow")

        result = run(self.update_command(), consumer, check=False)

        self.assertNotEqual(0, result.returncode)
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertEqual("conflicts", ledger["status"])
        self.assertIn(TARGET_ADDED_WORKFLOW + ".rej", ledger["conflicts"])
        self.assertNotIn(
            TARGET_ADDED_WORKFLOW,
            ledger["reconciled_target_equivalent"],
        )

    def test_exact_intervening_release_state_advances_safely(self) -> None:
        consumer = self.make_consumer("intervening-release")
        before = protected_bytes(consumer)
        rendered = self.workspace / "rendered-v012"
        run(
            [
                "copier",
                "copy",
                "--quiet",
                "--defaults",
                "--overwrite",
                "--vcs-ref",
                "v0.1.2",
                self.template.as_posix(),
                rendered.as_posix(),
            ],
            self.workspace,
        )
        (consumer / "README.md").write_bytes((rendered / "README.md").read_bytes())
        commit_all(consumer, "docs: apply exact v0.1.2 framework state")
        command = self.update_command()
        command[command.index("v0.1.1")] = "v0.1.3"

        result = run(command, consumer, check=False)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual([], list(consumer.rglob("*.rej")))
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertIn("README.md", ledger["reconciled_target_equivalent"])
        self.assertEqual(before, protected_bytes(consumer))
        self.assertIn(
            "Exact target release state.",
            (consumer / "README.md").read_text(encoding="utf-8"),
        )

    def test_v010_updater_is_synced_exactly_before_framework_update(self) -> None:
        consumer = self.make_consumer(
            "updater-bootstrap",
            bootstrap_updater=False,
        )
        old_updater = consumer / ".orinoco-lite/tools/update_orinoco.py"
        self.assertIn(OLD_UPDATER_MARKER, old_updater.read_text(encoding="utf-8"))

        self.bootstrap_target_updater(consumer)
        result = run(self.update_command(), consumer, check=False)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(
            self.target_updater,
            (consumer / ".orinoco-lite/tools/update_orinoco.py").read_bytes(),
        )

    def test_non_equivalent_bootstrap_override_remains_a_conflict(self) -> None:
        consumer = self.make_consumer("non-equivalent-bootstrap")
        before = protected_bytes(consumer)
        self.preapply_bootstrap_edits(
            consumer,
            pages_replacement=(
                "pixi-version: v0.73.0 # downstream override"
            ),
        )

        result = run(self.update_command(), consumer, check=False)

        self.assertNotEqual(0, result.returncode)
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertEqual("conflicts", ledger["status"])
        self.assertIn(
            ".github/workflows/pages.yml.rej",
            ledger["conflicts"],
        )
        self.assertNotIn(
            ".github/workflows/pages.yml",
            ledger["reconciled_target_equivalent"],
        )
        self.assertTrue(
            (consumer / ".github/workflows/pages.yml.rej").is_file()
        )
        self.assertEqual(before, protected_bytes(consumer))

    def test_target_placeholders_are_removed_only_from_populated_paths(self) -> None:
        consumer = self.make_consumer("placeholder-reconciliation")
        populated = {
            "source-adapters/.gitkeep": "source-adapters/zotero/config.toml",
            "site/config/.gitkeep": "site/config/site.yaml",
        }
        for placeholder, real_file in populated.items():
            (consumer / placeholder).unlink()
            destination = consumer / real_file
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f"evidence: {real_file}\n", encoding="utf-8")
        empty_placeholder = consumer / "custom/assets/.gitkeep"
        self.assertTrue(empty_placeholder.is_file())
        commit_all(consumer, "feat: populate imported site paths")
        before = protected_bytes(consumer)

        result = run(self.update_command(), consumer, check=False)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        ledger = json.loads(
            (consumer / ".orinoco-lite/state/framework-update.json").read_text()
        )
        self.assertEqual(sorted(populated), ledger["removed_populated_placeholders"])
        for placeholder in populated:
            self.assertFalse((consumer / placeholder).exists(), placeholder)
        self.assertTrue(empty_placeholder.is_file())
        self.assertEqual(before, protected_bytes(consumer))

    def test_preexisting_protected_rejection_fails_before_mutation(self) -> None:
        consumer = self.make_consumer("preexisting-rejection")
        rejection = consumer / "metadata/records/manual.rej"
        rejection.write_text("review required\n", encoding="utf-8")
        run(["git", "add", "--force", rejection.as_posix()], consumer)
        commit_all(consumer, "test: preserve unresolved content rejection")
        baseline = run(["git", "rev-parse", "HEAD"], consumer).stdout.strip()

        result = run(self.update_command(), consumer, check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("pre-existing conflict artifacts", result.stderr)
        self.assertTrue(rejection.is_file())
        comparison = run(
            ["git", "diff", "--quiet", baseline, "--", "."],
            consumer,
            check=False,
        )
        self.assertEqual(0, comparison.returncode)

    def test_unresolvable_template_tag_fails_before_mutation(self) -> None:
        consumer = self.make_consumer("missing-tag")
        command = self.update_command()
        command[command.index("v0.1.1")] = "v9.9.9"

        result = run(command, consumer, check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("cannot resolve Copier template tag 'v9.9.9'", result.stderr)
        status = run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            consumer,
        )
        self.assertEqual("", status.stdout)


    def test_intentional_template_conflict_fails_visibly(self) -> None:
        consumer = self.make_consumer("conflict")
        readme = consumer / "README.md"
        original_content = (consumer / "metadata" / "records" / "complete.yml").read_bytes()
        lines = readme.read_text(encoding="utf-8").splitlines()
        lines[0] = "# Orinoco Lite Site — downstream customization"
        readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
        commit_all(consumer, "docs: customize framework-owned heading")

        result = run(self.update_command(), consumer, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("conflict", (result.stdout + result.stderr).lower())
        conflicts = list(consumer.rglob("*.rej"))
        self.assertTrue(conflicts, "expected Copier to leave a visible .rej conflict")
        ledger = json.loads(
            (consumer / ".orinoco-lite" / "state" / "framework-update.json").read_text()
        )
        self.assertEqual("conflicts", ledger["status"])
        self.assertTrue(ledger["conflicts"])
        self.assertEqual(
            original_content,
            (consumer / "metadata" / "records" / "complete.yml").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
