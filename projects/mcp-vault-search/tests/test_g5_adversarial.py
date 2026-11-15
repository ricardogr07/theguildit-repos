"""G5 adversarial probes: actively corrupt evidence and demand rejection.

These tests are authored by the implementer and are NOT an independent review.
"""

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from evaluation.dataset import load_json, validate_dataset
from evaluation.metrics import score_query
from mcp_vault_search.retrieval_metrics import unique_note_ranking
from verify_g2_baseline import verify


PROJECT = Path(__file__).resolve().parents[1]
HISTORICAL = PROJECT / "evaluate_semantic_results_checkpoint_fixes.json"
EVAL = PROJECT / "evaluation"


def fixture():
    """Construct a consistent modern G2 report from already-versioned historical hits."""
    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    hmeta = historical[0]["evaluation_metadata"]
    code_paths = (
        "src/mcp_vault_search/semantic.py",
        "src/mcp_vault_search/server.py",
        "src/mcp_vault_search/retrieval_metrics.py",
        "evaluate_semantic.py", "run_g2_baseline.py", "uv.lock",
    )
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()
    rows = []
    for original in historical:
        hits = original["full_results"]
        note_order = unique_note_ranking(hits)
        first = {hit["path"]: hit for hit in reversed(hits)}
        # Keep the first, highest-ranked hit for every note.
        for hit in reversed(hits):
            first[hit["path"]] = hit
        target = original["expected_target"]
        rank = note_order.index(target) + 1 if target in note_order else None
        notes = [
            {"note": name, "rank": n, "score": first[name]["score"]}
            for n, name in enumerate(note_order, 1)
        ]
        rows.append({
            "query": original["query"],
            "expected_target": target,
            "designated_distractor": original["designated_distractor"],
            "target_position": original["target_position"],
            "distractor_position": original["distractor_position"],
            "pass": original["pass"],
            "full_results": hits,
            "note_rankings": notes,
            "top_10_notes": notes[:10],
            "single_target_recall_at_3": float(rank is not None and rank <= 3),
            "single_target_recall_at_5": float(rank is not None and rank <= 5),
            "single_target_reciprocal_rank_at_10": 1 / rank if rank and rank <= 10 else 0.0,
        })
    return {
        "metadata": {
            "git_commit": sha,
            "code_and_lock_sha256": {
                name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                for name in code_paths
            },
            "corpus_sha256": hmeta["corpus_sha256"],
            "model_name": hmeta["model_name"],
            "model_revision": hmeta["model_revision"],
        },
        "summary": {
            "current_legacy_pass_count": 2,
            "historical_original_pass_count": 2,
            "single_target_recall_at_3": 0.75,
            "single_target_recall_at_5": 1.0,
            "single_target_mrr_at_10": (1 / 5 + 1 + 1 + 1 / 3) / 4,
            "all_independent_checks_passed": True,
        },
        "results": rows,
    }


class EvidenceTamperingTests(TestCase):
    def assert_verifies(self, data, expected_error=None):
        with TemporaryDirectory() as directory:
            f = Path(directory) / "benchmark.json"
            f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            if expected_error is None:
                return verify(f, HISTORICAL, PROJECT)
            with self.assertRaises(AssertionError):
                verify(f, HISTORICAL, PROJECT)

    def test_original_historical_evidence_reconstructs_a_valid_report(self):
        result = self.assert_verifies(fixture())
        self.assertEqual(result["current_legacy_pass_count"], 2)
        self.assertEqual(result["single_target_recall_at_3"], .75)

    def test_mutated_top_ten_is_rejected(self):
        data = fixture()
        data["results"][0]["top_10_notes"][0]["note"] = "forged.md"
        self.assert_verifies(data, "top-ten")

    def test_fake_per_query_recall_is_rejected(self):
        data = fixture()
        data["results"][0]["single_target_recall_at_3"] = .99
        self.assert_verifies(data, "recall")

    def test_mutated_source_hash_is_rejected(self):
        data = fixture()
        data["metadata"]["code_and_lock_sha256"]["uv.lock"] = "0" * 64
        self.assert_verifies(data, "hash")

    def test_nonfinite_similarity_is_rejected(self):
        data = fixture()
        data["results"][0]["full_results"][0]["score"] = float("nan")
        self.assert_verifies(data, "nonfinite")

    def test_falsely_approved_qrel_without_reviewer_is_rejected(self):
        development = load_json(EVAL / "development_queries.json")
        holdout = load_json(EVAL / "holdout_queries.json")
        qrels = load_json(EVAL / "qrels.json")
        qrels["judgments"][0]["review_status"] = "approved"
        with self.assertRaisesRegex(ValueError, "revisor y fecha"):
            validate_dataset(
                development, holdout, qrels,
                {p.name for p in (PROJECT / "examples" / "vault").glob("*.md")},
            )

    def test_out_of_domain_not_counted_as_recall_zero(self):
        outcome = score_query(["mcp.md"], [])
        self.assertIsNone(outcome["recall_at_3"])
        self.assertTrue(outcome["forced_hit"])
