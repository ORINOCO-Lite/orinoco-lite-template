from __future__ import annotations

import json
import unittest

import test_update_cycle as update_cycle


DECISION_BYTES = b"""format: orinoco-lite-curation-decisions-prototype-v1
decisions:
  - decision_id: curation-decision-event-v1:683fd53cf1e9fb333f31db5fd596f97f52c5ff8c188829a7dd5c1960612ed531
    claim_revision_id: curation-claim-revision-v1:bcd7bac6c802e4715116f8f960f127b0dee9897ab7ef50c28419cca504f52b4e
    supersedes_decision_id: null
    candidate_id: curation-candidate-v1:9c5be03b07f32697ff8434d90545463ace26a87c37e0388ee9ac4fa81f7a06c0
    adapter_id: zotero
    source_namespace: zotero:group:6197458
    source_record_id: item:ABCD1234
    claim_kind: record-import
    material_fingerprint: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    relevant_policy_fingerprint: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    disposition: reject
    reviewer: example-reviewer
    decided_on: "2026-08-18"
    rationale: The reviewed source claim does not identify the canonical record.
    evidence:
      - https://example.invalid/review/example
transactions:
  - inventory_id: curation-inventory-v1:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
    decision_ids:
      - curation-decision-event-v1:683fd53cf1e9fb333f31db5fd596f97f52c5ff8c188829a7dd5c1960612ed531
"""
CROSSWALK_BYTES = (
    b"subject_id\tpredicate_id\tobject_id\tmapping_justification\n"
    b"zotero:creator:ABCD1234\tskos:exactMatch\t"
    b"xyzrins:persons/example\tsemapv:ManualMappingCuration\n"
)
DATALAD_RUNINFO_BYTES = b"synthetic retained curation run evidence\n"
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
            "source-adapters/zotero/policy/curation-decisions-prototype-v1.yaml": DECISION_BYTES,
            "source-adapters/zotero/policy/creator-crosswalk.tsv": CROSSWALK_BYTES,
            ".datalad/runinfo/0123456789abcdef0123456789abcdef": DATALAD_RUNINFO_BYTES,
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
