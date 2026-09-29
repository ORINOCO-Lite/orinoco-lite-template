"""Exercise workflow bundle transport with real parent and child Git histories."""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / 'copier-template/.github/workflows/template-update.yml').read_text())


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def commit(root, message):
    git(root, 'add', '.')
    git(root, 'commit', '-qm', message)
    return git(root, 'rev-parse', 'HEAD')


def step(job, name, root, env):
    script = next(s['run'] for s in WORKFLOW['jobs'][job]['steps'] if s.get('name') == name)
    return subprocess.run(['bash', '-euo', 'pipefail', '-c', script], cwd=root, env=env,
                          text=True, capture_output=True)


@pytest.mark.parametrize(('changed', 'retarget'), [(False, False), (True, False), (True, True)])
def test_parent_and_child_commits_survive_bundle_transport(tmp_path, monkeypatch, changed, retarget):
    for role in ('AUTHOR', 'COMMITTER'):
        monkeypatch.setenv(f'GIT_{role}_NAME', 'Transport test')
        monkeypatch.setenv(f'GIT_{role}_EMAIL', 'test@example.invalid')
    child, parent = tmp_path / 'published-inputs', tmp_path / 'candidate'
    for repo in (child, parent):
        repo.mkdir()
        git(repo, 'init', '-qb', 'main')
    (child / 'record.yaml').write_text('title: Before\n')
    child_base = commit(child, 'test: initial site inputs')
    git(parent, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'site-specific')
    base = commit(parent, 'test: record original gitlink')
    if changed:
        for title in ('Intermediate', 'After'):
            (parent / 'site-specific/record.yaml').write_text(f'title: {title}\n')
            commit(parent / 'site-specific', f'test: record {title.lower()} inputs')
            commit(parent, f'test: select {title.lower()} inputs')
    if retarget:
        modules = parent / '.gitmodules'
        modules.write_text(modules.read_text().replace(str(child), 'https://github.com/other/inputs.git'))
        commit(parent, 'test: unauthorized input repository change')
    runner = tmp_path / 'runner'; runner.mkdir()
    env = dict(os.environ, GITHUB_SHA=base, GITHUB_REF_NAME='main', RUNNER_TEMP=str(runner),
               GITHUB_OUTPUT=str(tmp_path / 'outputs'), GITHUB_STEP_SUMMARY=str(tmp_path / 'summary'))
    result = step('update', 'Export recorded update', parent, env)
    assert result.returncode == 0, result.stderr
    outputs = (tmp_path / 'outputs').read_text()
    assert f'changed={str(changed).lower()}' in outputs
    assert f'site_changed={str(changed).lower()}' in outputs
    if not changed:
        assert not list(runner.glob('*.bundle'))
        return
    transport = runner / 'template-update'; transport.mkdir()
    for bundle in runner.glob('*.bundle'):
        bundle.rename(transport / bundle.name)
    published = tmp_path / 'publisher'
    subprocess.run(['git', 'clone', '--quiet', str(parent), str(published)], check=True)
    git(published, 'checkout', '--detach', base)
    env['SITE_CHANGED'] = 'true'
    result = step('publish', 'Import recorded commits without executing updated code', published, env)
    if retarget:
        assert result.returncode != 0
        assert git(published, 'rev-parse', 'HEAD') == base
        return
    assert result.returncode == 0, result.stderr
    assert git(published, 'rev-parse', 'HEAD') == git(parent, 'rev-parse', 'HEAD')
    subprocess.run(['git', 'clone', '--quiet', str(child), str(published / 'site-specific')], check=True)
    env.update(SITE_BASE=child_base, SITE_BRANCH='main')
    result = step('publish', 'Import the recorded site-specific commits', published, env)
    assert result.returncode == 0, result.stderr
    assert git(published / 'site-specific', 'rev-parse', 'HEAD') == git(parent, 'rev-parse', 'HEAD:site-specific')
    assert git(published / 'site-specific', 'rev-list', '--count', f'{child_base}..HEAD') == '2'
    # Every intermediate parent run still names a recoverable child commit.
    for revision in git(parent, 'rev-list', f'{base}..HEAD').splitlines():
        pinned = git(parent, 'rev-parse', f'{revision}:site-specific')
        git(published / 'site-specific', 'cat-file', '-e', f'{pinned}^{{commit}}')
    # create-pull-request restores its working base after publishing the child.
    child_head = git(published / 'site-specific', 'rev-parse', 'HEAD')
    git(published / 'site-specific', 'reset', '--hard', child_base)
    env.update(SITE_PULL_URL='https://github.com/example/inputs/pull/1', SITE_PULL_HEAD=child_head)
    result = step('publish', 'Require published site-specific commits', published, env)
    assert result.returncode == 0, result.stderr
    assert not git(published, 'status', '--porcelain')
