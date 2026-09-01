#!/usr/bin/env python3
"""Publish an ephemeral Copier rendering on a dedicated Git branch."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterator

import yaml

import render_github_template as rendering


FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")
ZERO_COMMIT = "0" * 40


class PublicationError(RuntimeError):
    """Report an unsafe or inexact publication."""


def git(
    repository: Path,
    *arguments: str,
    environment: dict[str, str] | None = None,
    input_text: str | None = None,
) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=environment,
        input=input_text,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise PublicationError(
            f"git {' '.join(arguments)} failed with status {result.returncode}"
            + (f": {detail}" if detail else "")
        )
    return result.stdout.strip()


def optional_git(repository: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def require_clean(repository: Path) -> None:
    if git(repository, "status", "--porcelain", "--untracked-files=normal"):
        raise PublicationError("publishing requires a clean source worktree")


def resolve_exact_source(repository: Path, source_ref: str) -> str:
    """Accept an immutable tag or a full commit, never a moving branch name."""

    if FULL_COMMIT.fullmatch(source_ref):
        commit = git(repository, "rev-parse", f"{source_ref}^{{commit}}")
        if commit != source_ref:
            raise PublicationError(f"source commit is not canonical: {source_ref}")
        return commit
    tag = f"refs/tags/{source_ref}"
    if optional_git(repository, "show-ref", "--verify", tag) is None:
        raise PublicationError(
            "source ref must be an existing tag or full 40-character commit"
        )
    return git(repository, "rev-parse", f"{tag}^{{commit}}")


def template_version_commit(repository: Path, rendered: Path) -> str:
    answers = yaml.safe_load(
        (rendered / ".copier-answers.yml").read_text(encoding="utf-8")
    )
    version = answers.get("_commit") if isinstance(answers, dict) else None
    if not isinstance(version, str):
        raise PublicationError("rendered answers do not select a template version")
    tag = f"refs/tags/{version}"
    if optional_git(repository, "show-ref", "--verify", tag) is None:
        raise PublicationError(f"rendered template version is not tagged: {version}")
    return git(repository, "rev-parse", f"{tag}^{{commit}}")


def forbidden_rendered_paths(rendered: Path) -> list[str]:
    forbidden = []
    for path in sorted(rendered.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(rendered).as_posix()
        if (
            relative == ".gitmodules"
            or relative == "copier.yml"
            or relative.startswith("copier-template/")
            or relative.startswith("github-template/")
        ):
            forbidden.append(relative)
    return forbidden


def tree_from_directory(repository: Path, rendered: Path) -> str:
    """Write a Git tree without adding generated files to the source branch."""

    forbidden = forbidden_rendered_paths(rendered)
    if forbidden:
        raise PublicationError(
            "render exposes template source topology: " + ", ".join(forbidden)
        )
    with tempfile.TemporaryDirectory(prefix="orinoco-publication-index-") as temporary:
        index = Path(temporary) / "index"
        environment = dict(
            os.environ,
            GIT_INDEX_FILE=index.as_posix(),
            GIT_WORK_TREE=rendered.resolve().as_posix(),
        )
        git(repository, "read-tree", "--empty", environment=environment)
        git(repository, "add", "--all", "--force", environment=environment)
        return git(repository, "write-tree", environment=environment)


@contextmanager
def render_source(repository: Path, source_ref: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="orinoco-publication-render-") as temporary:
        destination = Path(temporary) / "consumer"
        try:
            rendering.render(
                repository,
                destination,
                source_ref=source_ref,
                verify_lock=True,
            )
        except rendering.RenderError as error:
            raise PublicationError(str(error)) from error
        yield destination


def published_tree(repository: Path, branch: str) -> str:
    return git(repository, "rev-parse", f"refs/heads/{branch}^{{tree}}")


def verify(repository: Path, source_ref: str, branch: str) -> str:
    source_commit = resolve_exact_source(repository, source_ref)
    with render_source(repository, source_ref) as rendered:
        if template_version_commit(repository, rendered) != source_commit:
            raise PublicationError(
                "rendered template version does not resolve to the source commit"
            )
        expected = tree_from_directory(repository, rendered)
    actual = published_tree(repository, branch)
    if actual != expected:
        raise PublicationError(
            f"{branch} tree {actual} differs from the {source_ref} rendering {expected}"
        )
    return actual


def publish(repository: Path, source_ref: str, branch: str) -> str:
    require_clean(repository)
    source_commit = resolve_exact_source(repository, source_ref)
    branch_ref = f"refs/heads/{branch}"
    with render_source(repository, source_ref) as rendered:
        if template_version_commit(repository, rendered) != source_commit:
            raise PublicationError(
                "rendered template version does not resolve to the source commit"
            )
        tree = tree_from_directory(repository, rendered)
    parent = optional_git(repository, "rev-parse", branch_ref)
    if parent is not None and published_tree(repository, branch) == tree:
        return parent
    arguments = ["commit-tree", tree]
    if parent is not None:
        arguments.extend(["-p", parent])
    message = (
        f"chore(publication): render {source_ref}\n\n"
        f"Source-Commit: {source_commit}\n"
    )
    commit = git(repository, *arguments, input_text=message)
    git(repository, "update-ref", branch_ref, commit, parent or ZERO_COMMIT)
    return commit


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--check", action="store_true")
    result.add_argument("--repository", type=Path, default=Path.cwd())
    result.add_argument("--source-ref", required=True)
    result.add_argument("--branch", default="github-template")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = args.repository.resolve()
    try:
        if args.publish:
            commit = publish(repository, args.source_ref, args.branch)
            tree = published_tree(repository, args.branch)
            print(f"published {args.source_ref} as {args.branch} ({commit}, tree {tree})")
        else:
            tree = verify(repository, args.source_ref, args.branch)
            print(f"{args.branch} exactly renders {args.source_ref} (tree {tree})")
    except (OSError, PublicationError, yaml.YAMLError) as error:
        print(f"GitHub-template publication failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
