#!/usr/bin/env python3
"""Render the Copier source into an untracked destination."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = ROOT / "build" / "github-template"


class RenderError(RuntimeError):
    """Report an unsafe or stale template rendering."""


def executable(name: str) -> str:
    value = shutil.which(name)
    if value is None:
        raise RenderError(f"{name} is unavailable; run this command through Pixi")
    return value


def run(arguments: list[str], *, cwd: Path) -> None:
    result = subprocess.run(arguments, cwd=cwd, check=False)
    if result.returncode:
        raise RenderError(
            f"{' '.join(arguments)} failed with status {result.returncode}"
        )


def safe_destination(repository: Path, destination: Path) -> Path:
    repository = repository.resolve()
    if destination.is_symlink():
        raise RenderError(f"render destination cannot be a symlink: {destination}")
    destination = destination.resolve(strict=False)
    if destination == repository or destination in repository.parents:
        raise RenderError("render destination must not contain the source repository")
    if repository in destination.parents:
        build_root = (repository / "build").resolve(strict=False)
        if destination != build_root and build_root not in destination.parents:
            raise RenderError(
                "render destinations inside the source repository must be under build/"
            )
    return destination


def normalize_answers(destination: Path) -> dict[str, object]:
    """Make Copier bookkeeping stable without a second defaults file."""

    path = destination / ".copier-answers.yml"
    try:
        answers = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise RenderError(f"Copier did not produce valid answers: {path}") from error
    if not isinstance(answers, dict):
        raise RenderError(f"Copier answers are not a mapping: {path}")
    source = answers.get("template_source")
    version = answers.get("template_version")
    if not isinstance(source, str) or not isinstance(version, str):
        raise RenderError("rendered answers lack template_source or template_version")
    answers.pop("_src_path", None)
    answers.pop("_commit", None)
    answers = {"_src_path": source, **answers, "_commit": version}
    path.write_text(
        yaml.safe_dump(answers, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return answers


def verify_frozen_lock(destination: Path) -> None:
    """Require the source lock to already match the rendered manifest."""

    lock = destination / "pixi.lock"
    if not lock.is_file():
        raise RenderError("copier-template/pixi.lock was not rendered")
    before = lock.read_bytes()
    run(
        [
            executable("pixi"),
            "lock",
            "--no-config",
            "--no-install",
            "--manifest-path",
            (destination / "pixi.toml").as_posix(),
        ],
        cwd=destination,
    )
    if lock.read_bytes() != before:
        raise RenderError(
            "copier-template/pixi.lock is stale; refresh and review the source lock"
        )


def render(
    repository: Path,
    destination: Path,
    *,
    source_ref: str | None = None,
    data_file: Path | None = None,
    replace: bool = False,
    verify_lock: bool = True,
) -> dict[str, object]:
    """Render current source bytes or one selected Git ref."""

    repository = repository.resolve()
    destination = safe_destination(repository, destination)
    if destination.exists():
        if not destination.is_dir():
            raise RenderError(f"render destination is not a directory: {destination}")
        if not replace:
            raise RenderError(f"render destination already exists: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable("copier"),
        "copy",
        "--quiet",
        "--defaults",
        "--overwrite",
    ]
    # Copier otherwise selects the latest template tag for a local Git source.
    # Development renders must exercise the current checkout, including its
    # deliberate uncommitted changes; publication passes an immutable tag or
    # commit explicitly.
    command.extend(["--vcs-ref", source_ref or "HEAD"])
    if data_file is not None:
        command.extend(["--data-file", data_file.resolve().as_posix()])
    command.extend([repository.as_posix(), destination.as_posix()])
    run(command, cwd=repository)
    answers = normalize_answers(destination)
    if verify_lock:
        verify_frozen_lock(destination)
    return answers


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository", type=Path, default=ROOT)
    result.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    result.add_argument("--source-ref")
    result.add_argument("--data-file", type=Path)
    result.add_argument("--replace", action="store_true")
    result.add_argument(
        "--skip-lock-check",
        action="store_true",
        help="render without resolving the downstream Pixi lock",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        render(
            args.repository,
            args.destination,
            source_ref=args.source_ref,
            data_file=args.data_file,
            replace=args.replace,
            verify_lock=not args.skip_lock_check,
        )
    except RenderError as error:
        print(f"template render failed: {error}", file=sys.stderr)
        return 2
    print(f"rendered template into {args.destination.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
