"""Optional checks for downstreams that do not use Git Annex."""

import os
import shlex

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--no-annex",
        action="store_true",
        help="Fail if a test invokes git-annex, even if the caller ignores failure.",
    )


@pytest.fixture(autouse=True)
def no_annex(request, tmp_path, monkeypatch):
    if not request.config.getoption("--no-annex"):
        yield
        return

    invoked = tmp_path / "annex-invoked"
    executable = tmp_path / "git-annex"
    executable.write_text(
        "#!/bin/sh\n"
        f"touch {shlex.quote(str(invoked))}\n"
        'echo "Unexpected git-annex invocation under --no-annex" >&2\n'
        "exit 99\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    yield
    if invoked.exists():
        pytest.fail("git-annex was invoked under --no-annex")
