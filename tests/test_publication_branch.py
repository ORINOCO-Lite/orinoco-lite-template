from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "publish_github_template_branch.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Template Publication Test",
    "GIT_AUTHOR_EMAIL": "publication-test@example.invalid",
    "GIT_COMMITTER_NAME": "Template Publication Test",
    "GIT_COMMITTER_EMAIL": "publication-test@example.invalid",
}


def load_publisher():
    sys.path.insert(0, SCRIPT.parent.as_posix())
    spec = importlib.util.spec_from_file_location(
        "publish_github_template_branch",
        SCRIPT,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command: list[str], cwd: Path, *, check: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=dict(os.environ, **GIT_ENV),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise AssertionError(
            f"command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


class PublicationBranchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.publisher = load_publisher()

    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(prefix="orinoco-template-branch-") as temporary:
            temporary_root = Path(temporary)
            repository = temporary_root / "source"
            repository.mkdir()
            run(["git", "init", "-b", "main"], repository)
            (repository / "copier.yml").write_text(
                "_subdirectory: copier-template\n",
                encoding="utf-8",
            )
            (repository / "copier-template").mkdir()
            (repository / "copier-template/README.md.jinja").write_text(
                "# Consumer\n",
                encoding="utf-8",
            )
            run(["git", "add", "--all"], repository)
            run(["git", "commit", "-m", "feat: add template source"], repository)
            run(["git", "tag", "v1.0.0"], repository)

            rendered = temporary_root / "rendered-consumer"
            rendered.mkdir()
            (rendered / ".copier-answers.yml").write_text(
                yaml.safe_dump({"_commit": "v1.0.0"}),
                encoding="utf-8",
            )
            (rendered / "README.md").write_text("# Consumer\n", encoding="utf-8")
            (rendered / "orinoco.yaml").write_text(
                "contract_version: 1\n", encoding="utf-8"
            )
            yield repository, rendered

    def test_publication_is_an_exact_ephemeral_render_from_a_tag(self) -> None:
        with self.fixture() as (repository, rendered):

            @contextmanager
            def use_rendered(_repository: Path, _source_ref: str):
                yield rendered

            with (
                patch.object(self.publisher, "render_source", use_rendered),
                patch.dict(os.environ, GIT_ENV),
            ):
                commit = self.publisher.publish(
                    repository,
                    "v1.0.0",
                    "github-template",
                )
                branch_tree = self.publisher.verify(
                    repository,
                    "v1.0.0",
                    "github-template",
                )

            self.assertEqual(
                commit,
                run(["git", "rev-parse", "github-template"], repository),
            )
            self.assertEqual(
                branch_tree,
                run(
                    ["git", "rev-parse", "github-template^{tree}"],
                    repository,
                ),
            )
            paths = run(
                ["git", "ls-tree", "-r", "--name-only", "github-template"],
                repository,
            ).splitlines()
            self.assertEqual(
                [".copier-answers.yml", "README.md", "orinoco.yaml"],
                paths,
            )
            self.assertNotIn("copier.yml", paths)
            self.assertFalse((repository / "github-template").exists())

            (rendered / "README.md").write_text("# Drifted\n", encoding="utf-8")
            with (
                patch.object(self.publisher, "render_source", use_rendered),
                self.assertRaisesRegex(
                    self.publisher.PublicationError,
                    "differs from the v1.0.0 rendering",
                ),
            ):
                self.publisher.verify(
                    repository,
                    "v1.0.0",
                    "github-template",
                )

    def test_only_immutable_source_refs_are_accepted(self) -> None:
        with self.fixture() as (repository, _rendered):
            commit = run(["git", "rev-parse", "HEAD"], repository)
            self.assertEqual(
                commit,
                self.publisher.resolve_exact_source(repository, "v1.0.0"),
            )
            self.assertEqual(
                commit,
                self.publisher.resolve_exact_source(repository, commit),
            )
            with self.assertRaisesRegex(
                self.publisher.PublicationError,
                "existing tag or full 40-character commit",
            ):
                self.publisher.resolve_exact_source(repository, "main")

    def test_source_topology_cannot_leak_into_publication(self) -> None:
        with self.fixture() as (repository, rendered):
            (rendered / "copier.yml").write_text(
                "question: value\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                self.publisher.PublicationError,
                "render exposes template source topology: copier.yml",
            ):
                self.publisher.tree_from_directory(repository, rendered)


if __name__ == "__main__":
    unittest.main()
