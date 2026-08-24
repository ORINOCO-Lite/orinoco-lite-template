from __future__ import annotations

import json
import unittest

import test_update_cycle as update_cycle


DECISION_BYTES = b"""adapter: zotero
decisions:
  xyzrins:publications/example:
    claim_sha256: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    disposition: reject
    review: github-comment:123456
    source_record_id: item:ABCD1234
format: orinoco-lite-curation-decisions-v1
reviews:
  github-comment:123456:
    review_url: https://github.com/example/site/pull/42#issuecomment-123456
    reviewed_at: '2026-08-20T18:42:00Z'
    reviewer: https://github.com/example-reviewer
    source_coordinate:
      library_version: 451
"""
ANNOTATION_BYTES = b"""assertions:
  - assertion_sha256: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    path: /identifiers/0
    pav:importedBy: xyzrins:source-adapters/zotero/v1
    pav:importedFrom: https://api.zotero.org/groups/6197458/items/ABCD1234
record: xyzrins:publications/example
"""
CURATION_WORKFLOW_BYTES = b"""name: Site curation review
on:
  workflow_dispatch:
jobs:
  site-owned-example:
    runs-on: ubuntu-24.04
    steps:
      - run: echo retained
"""


class SourceAdapterUpdatePreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.update_fixture = update_cycle.UpdateCycleTests(
            "test_update_records_coordinates_preserves_site_and_reverts_cleanly"
        )
        self.update_fixture.setUp()
        self.addCleanup(self.update_fixture.tearDown)

    def test_normal_update_preserves_site_curation_bytes(self) -> None:
        consumer = self.update_fixture.make_consumer("source-adapter-policy")
        artifacts = {
            "source-adapters/zotero/policy/curation-decisions.yaml": DECISION_BYTES,
            "metadata/overlays/annotations/XYZPublication/example.yaml": ANNOTATION_BYTES,
            ".github/workflows/curation-review.yml": CURATION_WORKFLOW_BYTES,
        }
        for relative, content in artifacts.items():
            path = consumer / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        update_cycle.commit_all(
            consumer,
            "test: add site-owned source-adapter policy",
        )
        before = {
            relative: (consumer / relative).read_bytes() for relative in artifacts
        }

        result = update_cycle.run(
            self.update_fixture.update_command(),
            consumer,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        after = {
            relative: (consumer / relative).read_bytes() for relative in artifacts
        }
        self.assertEqual(before, after)
        ledger = json.loads(
            (
                consumer / ".orinoco-lite/state/framework-update.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual([], ledger["site_owned"]["changed"])


if __name__ == "__main__":
    unittest.main()
