from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "publish_github_template_branch.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Template Publication Test",
    "GIT_AUTHOR_EMAIL": "publication-test@example.invalid",
    "GIT_COMMITTER_NAME": "Template Publication Test",
    "GIT_COMMITTER_EMAIL": "publication-test@example.invalid",
}


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
    def test_publication_branch_has_exact_consumer_tree_at_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="orinoco-template-branch-") as temporary:
            repository = Path(temporary)
            run(["git", "init", "-b", "main"], repository)
            rendered = repository / "github-template"
            rendered.mkdir()
            (rendered / "README.md").write_text("# Consumer\n", encoding="utf-8")
            (rendered / "orinoco.yaml").write_text(
                "contract_version: 1\n", encoding="utf-8"
            )
            (repository / "copier.yml").write_text("question: answer\n", encoding="utf-8")
            (repository / "copier-template").mkdir()
            (repository / "copier-template" / "README.md.jinja").write_text(
                "# [[ project_name ]]\n", encoding="utf-8"
            )
            run(["git", "add", "--all"], repository)
            run(["git", "commit", "-m", "feat: add template source"], repository)

            output = run(
                [
                    "python",
                    SCRIPT.as_posix(),
                    "--publish",
                    "--repository",
                    repository.as_posix(),
                ],
                repository,
            )
            self.assertIn("exactly publishes main:github-template", output)
            source_tree = run(
                ["git", "rev-parse", "main:github-template"], repository
            )
            branch_tree = run(
                ["git", "rev-parse", "github-template^{tree}"], repository
            )
            self.assertEqual(source_tree, branch_tree)
            paths = run(
                ["git", "ls-tree", "-r", "--name-only", "github-template"],
                repository,
            ).splitlines()
            self.assertEqual(["README.md", "orinoco.yaml"], paths)
            self.assertNotIn("copier.yml", paths)

            checked = run(
                [
                    "python",
                    SCRIPT.as_posix(),
                    "--check",
                    "--repository",
                    repository.as_posix(),
                ],
                repository,
            )
            self.assertIn(branch_tree, checked)


if __name__ == "__main__":
    unittest.main()
