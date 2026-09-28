"""Publication configuration survives ordinary Copier updates."""

from pathlib import Path
import shutil
import subprocess

import copier
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True,
                          text=True, capture_output=True).stdout.strip()


@pytest.mark.parametrize("supplied, expected", [(None, 3), (1, 1), (5, 5)])
def test_pages_history_limit_survives_update(tmp_path, monkeypatch, supplied, expected):
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Template Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "template@example.invalid")
    template = tmp_path / "template"
    template.mkdir()
    shutil.copy2(ROOT / "copier.yml", template)
    shutil.copytree(ROOT / "copier-template", template / "copier-template")
    git(template, "init", "-b", "main")
    git(template, "add", ".")
    git(template, "commit", "-m", "feat: add template")
    git(template, "tag", "v1.0.0")
    downstream = tmp_path / "downstream"
    data = {} if supplied is None else {"pages_history_limit": supplied}
    copier.run_copy(str(template), downstream, defaults=True, data=data, quiet=True)
    git(downstream, "init", "-b", "main")
    git(downstream, "add", ".")
    git(downstream, "commit", "-m", "feat: create website")

    def check():
        answers = yaml.safe_load((downstream / ".copier-answers.yml").read_text())
        assert answers["pages_history_limit"] == expected
        workflow = (downstream / ".github/workflows/pages.yml").read_text()
        assert f"publication record --history-limit {expected}" in workflow

    check()
    (template / "copier-template/README.md.jinja").write_text("An updated template.\n")
    git(template, "add", ".")
    git(template, "commit", "-m", "docs: update template")
    git(template, "tag", "v1.0.1")
    copier.run_update(downstream, defaults=True, overwrite=True, quiet=True)
    check()


def test_invalid_history_limit_is_rejected(tmp_path):
    # A non-Git source makes Copier use the candidate files being tested.
    template = tmp_path / "template"
    template.mkdir()
    shutil.copy2(ROOT / "copier.yml", template)
    shutil.copytree(ROOT / "copier-template", template / "copier-template")
    with pytest.raises(ValueError, match="Retain at least one publication"):
        copier.run_copy(str(template), tmp_path / "site", defaults=True,
                        data={"pages_history_limit": 0}, quiet=True)
