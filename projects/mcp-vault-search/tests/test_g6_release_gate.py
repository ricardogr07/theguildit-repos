"""G6 release candidate checks are fail-closed; no tag or branch is created."""

import copy
import json
from pathlib import Path
from unittest import TestCase

from scripts.check_release_gate import release_blockers


PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT / "docs" / "gates" / "G6" / "RELEASE_MANIFEST.json"
QRELS = PROJECT / "evaluation" / "qrels.json"
COMMIT = "a" * 40
OTHER_SHA = "b" * 40


def load():
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        json.loads(QRELS.read_text(encoding="utf-8")),
    )


def synthetic_fully_approved_fixture():
    """A fictional test fixture, never a production approval."""
    manifest, qrels = load()
    manifest["status"] = "APPROVED_FOR_FREEZE"
    manifest["candidate_commit_sha"] = COMMIT
    for gate in manifest["gate_approvals"]:
        manifest["gate_approvals"][gate]["pass"] = True
    for pr in manifest["pr_merges"]:
        manifest["pr_merges"][pr] = OTHER_SHA
    manifest["owner_approval"]["reviewer"] = "test-owner"
    manifest["owner_approval"]["approved_at_utc"] = "2026-11-15T00:00:00Z"
    manifest["independent_review"].update({
        "reviewer": "test-reviewer",
        "reviewed_commit_sha": OTHER_SHA,
        "reviewed_at_utc": "2026-11-15T00:00:00Z",
        "report_path": "synthetic/mock-review.md",
    })
    for key in manifest["release_evidence"]:
        manifest["release_evidence"][key] = "mock://evidence"
    for label in qrels["judgments"]:
        label["review_status"] = "approved"
        label["reviewer"] = "test-reviewer"
        label["reviewed_at"] = "2026-11-15T00:00:00Z"
    return manifest, qrels


class ReleaseGateTests(TestCase):
    def test_committed_manifest_correctly_blocks_release(self):
        manifest, qrels = load()
        blockers = release_blockers(manifest, qrels, COMMIT)
        self.assertGreater(len(blockers), 4)
        self.assertTrue(any("G3" in reason for reason in blockers))
        self.assertTrue(any("judgments" in reason for reason in blockers))
        self.assertTrue(any("owner" in reason for reason in blockers))

    def test_synthetic_approved_fixture_is_eligible(self):
        manifest, qrels = synthetic_fully_approved_fixture()
        self.assertEqual(release_blockers(manifest, qrels, COMMIT), [])

    def test_candidate_must_match_actual_checkout_sha(self):
        manifest, qrels = synthetic_fully_approved_fixture()
        blockers = release_blockers(manifest, qrels, OTHER_SHA)
        self.assertTrue(any("checkout HEAD" in error for error in blockers))

    def test_any_open_high_or_critical_finding_blocks_freeze(self):
        for severity in ("open_high_defects", "open_critical_defects"):
            manifest, qrels = synthetic_fully_approved_fixture()
            manifest[severity] = [{"id": "failing-test", "severity": severity}]
            self.assertTrue(any("defects" in reason for reason in release_blockers(manifest, qrels, COMMIT)))

    def test_reviewer_identity_and_approval_are_mandatory(self):
        manifest, qrels = synthetic_fully_approved_fixture()
        manifest["independent_review"]["reviewer"] = None
        self.assertTrue(any("independent adversarial" in reason
                            for reason in release_blockers(manifest, qrels, COMMIT)))
        manifest, qrels = synthetic_fully_approved_fixture()
        qrels["judgments"][0]["reviewer"] = None
        self.assertTrue(any("relevance judgments" in reason
                            for reason in release_blockers(manifest, qrels, COMMIT)))

    def test_missing_pr_merge_blocks_even_with_all_other_approvals(self):
        manifest, qrels = synthetic_fully_approved_fixture()
        manifest["pr_merges"]["14"] = None
        self.assertTrue(any("PR #14" in reason for reason in release_blockers(manifest, qrels, COMMIT)))

    def test_missing_evidence_or_model_change_blocks_freeze(self):
        manifest, qrels = synthetic_fully_approved_fixture()
        manifest["release_evidence"]["g4_performance"] = None
        self.assertTrue(any("g4_performance" in reason for reason in release_blockers(manifest, qrels, COMMIT)))
        manifest, qrels = synthetic_fully_approved_fixture()
        manifest["model"]["revision"] = "unreviewed-revision"
        self.assertTrue(any("model revision" in reason.lower()
                            for reason in release_blockers(manifest, qrels, COMMIT)))
