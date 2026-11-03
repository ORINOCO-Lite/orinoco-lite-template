"""Exercise the downstream event router without calling GitHub."""
from pathlib import Path
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from jinja2 import Environment
import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(repository='git@github.com:example/package.git'):
    environment = Environment(variable_start_string='[[', variable_end_string=']]',
                              block_start_string='<%', block_end_string='%>')
    source = (ROOT / 'copier-template/.github/workflows/orinoco.yml.jinja').read_text()
    rendered = environment.from_string(source).render(
        package_repository=repository, package_revision='a' * 40)
    return yaml.load(rendered, Loader=yaml.BaseLoader)


class SubmissionRoutingTests(unittest.TestCase):
    def run_route(self, event_name, event, responses=None):
        sent = []
        responses = responses or {}

        def respond(request, **kwargs):
            if request.data:
                sent.append(json.loads(request.data))
                return io.BytesIO(b'')
            for path, value in responses.items():
                if path in request.full_url:
                    return io.BytesIO(json.dumps(value).encode())
            raise AssertionError(request.full_url)

        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / 'event.json'
            event_path.write_text(json.dumps(event))
            with patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/metadata',
                                         'GITHUB_EVENT_NAME': event_name,
                                         'GITHUB_EVENT_PATH': str(event_path),
                                         'GH_TOKEN': 'fixture-token'}):
                with patch('urllib.request.urlopen', side_effect=respond):
                    exec(workflow()['jobs']['route']['steps'][0]['run'], {})
        return sent

    def test_dispatch_runs_at_the_retained_submission_branch(self):
        branch = 'orinoco/submissions/' + 'b' * 64
        self.assertEqual(self.run_route('repository_dispatch', {'client_payload': {'submission': branch}}),
                         [{'ref': branch, 'inputs': {'phase': 'process', 'pull_request': '0'}}])

    def test_merge_of_an_existing_proposal_routes_its_authorized_submissions(self):
        event = {'pull_request': {'number': 17, 'head': {'ref': 'existing-proposal'}}}
        sent = self.run_route('pull_request_target', event, {
            '/issues/17/comments': [{'body': '<!-- orinoco-submission:' + 'c' * 64 + ' -->'}],
            '/contents/': {'input_repository': 'example/metadata'},
        })
        self.assertEqual(sent, [{'ref': 'orinoco/submissions/' + 'c' * 64,
                                 'inputs': {'phase': 'complete', 'pull_request': '17'}}])

    def test_website_merge_does_not_process_private_metadata(self):
        event = {'pull_request': {'number': 18, 'head': {'ref': 'orinoco/proposals/' + 'd' * 64}}}
        self.assertEqual(self.run_route('pull_request_target', event, {
            '/issues/18/comments': [], '/contents/': {'input_repository': 'example/private-input'},
        }), [])

    def test_invalid_dispatch_branch_is_not_run(self):
        with self.assertRaisesRegex(SystemExit, 'Invalid submission'):
            self.run_route('repository_dispatch', {'client_payload': {'submission': 'main'}})

    def test_ssh_and_https_package_selections_call_the_same_worker(self):
        expected = 'example/package/.github/workflows/repository-submission.yml@' + 'a' * 40
        for repository in ['git@github.com:example/package.git', 'https://github.com/example/package.git']:
            self.assertEqual(workflow(repository)['jobs']['process']['uses'], expected)


if __name__ == '__main__':
    unittest.main()
