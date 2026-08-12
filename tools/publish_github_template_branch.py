#!/usr/bin/env python3
"""Publish or verify the exact rendered tree on a dedicated Git branch."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


class PublicationError(RuntimeError):
    """Raised when the publication branch is not an exact rendered tree."""


def git(repository: Path, *arguments: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode:
        detail = result.stderr.strip() if result.stderr else ""
        raise PublicationError(
            f"git {' '.join(arguments)} failed with status {result.returncode}"
            + (f": {detail}" if detail else "")
        )
    return result.stdout.strip() if result.stdout else ""


def require_clean(repository: Path) -> None:
    status = git(repository, "status", "--porcelain", "--untracked-files=normal")
    if status:
        raise PublicationError(
            "publishing requires a clean source worktree; commit the reviewed "
            "Copier source and rendered tree first"
        )


def expected_tree(repository: Path, source_ref: str, prefix: str) -> str:
    return git(repository, "rev-parse", f"{source_ref}:{prefix}")


def published_tree(repository: Path, branch: str) -> str:
    return git(repository, "rev-parse", f"refs/heads/{branch}^{{tree}}")


def verify(repository: Path, source_ref: str, prefix: str, branch: str) -> None:
    expected = expected_tree(repository, source_ref, prefix)
    actual = published_tree(repository, branch)
    if actual != expected:
        raise PublicationError(
            f"{branch} tree {actual} differs from {source_ref}:{prefix} tree {expected}"
        )
    paths = git(repository, "ls-tree", "-r", "--name-only", branch).splitlines()
    forbidden = [
        path
        for path in paths
        if path == ".gitmodules"
        or path == "copier.yml"
        or path.startswith("copier-template/")
        or path.startswith(f"{prefix}/")
    ]
    if forbidden:
        raise PublicationError(
            "publication branch exposes source topology: " + ", ".join(forbidden)
        )


def publish(repository: Path, source_ref: str, prefix: str, branch: str) -> None:
    require_clean(repository)
    if branch == source_ref:
        raise PublicationError("source and publication branches must be distinct")
    # `git subtree split` preserves the source commits' authorship and messages
    # while rewriting their tree roots to the rendered prefix. Re-running it is
    # stable and advances the publication history from the same reviewed source.
    git(
        repository,
        "subtree",
        "split",
        f"--prefix={prefix}",
        f"--branch={branch}",
        source_ref,
        capture=False,
    )
    verify(repository, source_ref, prefix, branch)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--check", action="store_true")
    result.add_argument("--repository", type=Path, default=Path.cwd())
    result.add_argument("--source-ref", default="main")
    result.add_argument("--prefix", default="github-template")
    result.add_argument("--branch", default="github-template")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repository = args.repository.resolve()
    try:
        if args.publish:
            publish(repository, args.source_ref, args.prefix, args.branch)
        else:
            verify(repository, args.source_ref, args.prefix, args.branch)
    except PublicationError as error:
        print(f"GitHub-template publication failed: {error}", file=sys.stderr)
        return 2
    tree = published_tree(repository, args.branch)
    print(
        f"{args.branch} exactly publishes {args.source_ref}:{args.prefix} "
        f"(tree {tree})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
