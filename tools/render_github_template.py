#!/usr/bin/env python3
"""Render or verify the checked GitHub-template tree from the Copier source."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "github-template"
ANSWERS = ROOT / ".github-template-answers.yml"
SOURCE_LOCK = ROOT / "copier-template" / "pixi.lock"


def copier_executable() -> str:
    executable = shutil.which("copier")
    if executable is None:
        raise RuntimeError("Copier is unavailable; run through `pixi run render`")
    return executable


def pixi_executable() -> str:
    executable = shutil.which("pixi")
    if executable is None:
        raise RuntimeError("Pixi is unavailable; rendering must create pixi.lock")
    return executable


def render(destination: Path) -> bool:
    command = [
        copier_executable(),
        "copy",
        "--quiet",
        "--defaults",
        "--overwrite",
        "--data-file",
        ANSWERS.as_posix(),
        ROOT.as_posix(),
        destination.as_posix(),
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(f"Copier render failed with status {result.returncode}")

    defaults = yaml.safe_load(ANSWERS.read_text(encoding="utf-8"))
    rendered_answers_path = destination / ".copier-answers.yml"
    rendered_answers = yaml.safe_load(rendered_answers_path.read_text(encoding="utf-8"))
    rendered_answers["_src_path"] = defaults["template_source"]
    rendered_answers["_commit"] = defaults["template_version"]
    rendered_answers_path.write_text(
        yaml.safe_dump(rendered_answers, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    copied_lock = destination / "pixi.lock"
    if not copied_lock.is_file():
        raise RuntimeError(
            "copier-template/pixi.lock is required so Copier-first consumers "
            "receive the reviewed frozen environment"
        )
    lock_before = copied_lock.read_bytes()
    lock = subprocess.run(
        [
            pixi_executable(),
            "lock",
            "--no-config",
            "--no-install",
            "--manifest-path",
            (destination / "pixi.toml").as_posix(),
        ],
        cwd=destination,
        check=False,
    )
    if lock.returncode:
        raise RuntimeError(f"Pixi lock generation failed with status {lock.returncode}")
    return lock_before != copied_lock.read_bytes()


def differences(left: Path, right: Path) -> list[str]:
    comparison = filecmp.dircmp(left, right, ignore=[".pixi", "__pycache__"])
    result = [f"only rendered: {path}" for path in comparison.left_only]
    result.extend(f"only checked: {path}" for path in comparison.right_only)
    result.extend(f"different: {path}" for path in comparison.diff_files)
    for name, child in comparison.subdirs.items():
        result.extend(f"{name}/{item}" for item in differences(child.left, child.right))
    return sorted(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="orinoco-template-render-") as temporary:
        candidate = Path(temporary) / "github-template"
        source_lock_was_stale = render(candidate)
        if args.check:
            if source_lock_was_stale:
                print(
                    "copier-template/pixi.lock differs from the lock generated "
                    "for .github-template-answers.yml; run `pixi run render`",
                    file=sys.stderr,
                )
                return 1
            if not DESTINATION.is_dir():
                print("github-template/ has not been rendered", file=sys.stderr)
                return 1
            changed = differences(candidate, DESTINATION)
            if changed:
                print("github-template/ differs from the Copier rendering:", file=sys.stderr)
                for path in changed:
                    print(f"- {path}", file=sys.stderr)
                return 1
            print("GitHub-template rendering is current")
            return 0

        if source_lock_was_stale:
            shutil.copy2(candidate / "pixi.lock", SOURCE_LOCK)
            shutil.rmtree(candidate)
            source_lock_was_stale = render(candidate)
            if source_lock_was_stale:
                raise RuntimeError(
                    "generated Copier source lock is not stable across rendering"
                )

        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        shutil.copytree(candidate, DESTINATION)
    print(f"rendered {DESTINATION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
