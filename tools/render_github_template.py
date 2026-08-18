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
COPIER_CONFIGURATION = ROOT / "copier.yml"
RELEASE_COORDINATES = (
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
IGNORED_RUNTIME_ROOTS = {
    ".orinoco",
    ".pixi",
    "build",
    "generated",
    "node_modules",
    "playwright-report",
    "test-results",
}
IGNORED_RUNTIME_PATHS = {Path(".orinoco-lite/state")}
IGNORED_NAMES = {".DS_Store", "__pycache__"}


def verify_coordinate_defaults() -> None:
    """Require Copier-first creation and the checked render to share pins."""

    answers = yaml.safe_load(ANSWERS.read_text(encoding="utf-8"))
    configuration = yaml.safe_load(
        COPIER_CONFIGURATION.read_text(encoding="utf-8")
    )
    mismatches = []
    for coordinate in RELEASE_COORDINATES:
        prompt = configuration.get(coordinate)
        default = prompt.get("default") if isinstance(prompt, dict) else None
        if default != answers.get(coordinate):
            mismatches.append(coordinate)
    if mismatches:
        raise RuntimeError(
            "Copier release-coordinate defaults differ from "
            ".github-template-answers.yml: " + ", ".join(mismatches)
        )


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
    verify_coordinate_defaults()
    command = [
        copier_executable(),
        "copy",
        "--quiet",
        "--defaults",
        "--overwrite",
        "--vcs-ref",
        "HEAD",
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
    # Copier orders these bookkeeping keys according to the VCS checkout. A
    # shallow CI clone can therefore produce a different byte order than a
    # full local clone even when the values are identical. Normalize both
    # keys so the checked publication tree is reproducible everywhere.
    rendered_answers.pop("_src_path", None)
    rendered_answers.pop("_commit", None)
    rendered_answers = {
        "_src_path": defaults["template_source"],
        **rendered_answers,
        "_commit": defaults["template_version"],
    }
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


def ignored_runtime_path(relative: Path) -> bool:
    if not relative.parts:
        return False
    if relative.parts[0] in IGNORED_RUNTIME_ROOTS:
        return True
    if relative.name in IGNORED_NAMES:
        return True
    if relative.suffix in {".pyc", ".pyo", ".rej"}:
        return True
    return any(
        relative == ignored or ignored in relative.parents
        for ignored in IGNORED_RUNTIME_PATHS
    )


def differences(
    left: Path,
    right: Path,
    relative: Path = Path(),
) -> list[str]:
    comparison = filecmp.dircmp(left, right)
    result = [
        f"only rendered: {path}"
        for path in comparison.left_only
        if not ignored_runtime_path(relative / path)
    ]
    result.extend(
        f"only checked: {path}"
        for path in comparison.right_only
        if not ignored_runtime_path(relative / path)
    )
    result.extend(
        f"different: {path}"
        for path in comparison.diff_files
        if not ignored_runtime_path(relative / path)
    )
    for name, child in comparison.subdirs.items():
        child_relative = relative / name
        if ignored_runtime_path(child_relative):
            continue
        result.extend(
            f"{name}/{item}"
            for item in differences(child.left, child.right, child_relative)
        )
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
