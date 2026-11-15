"""G3 evaluation: no model download; enforce metric and annotation safeguards."""

import copy
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from evaluation.dataset import load_json, validate_dataset
from evaluation.metrics import score_query, summarize
from evaluation.run_expanded import run, validate_legacy_queries


HERE = Path(__file__).resolve().parents[1]
EVAL = HERE / "evaluation"
AVAILABLE = {p.name for p in (HERE / "examples" / "vault").glob("*.md")}


class DatasetValidationTest(TestCase):
    def get_files(self):
        return (
            load_json(EVAL / "development_queries.json"),
            load_json(EVAL / "holdout_queries.json"),
            load_json(EVAL / "qrels.json"),
        )

    def test_complete_distinct_splits_and_provisional_labels(self):
        d, h, q = self.get_files()
        report = validate_dataset(d, h, q, AVAILABLE)
        self.assertEqual(report["new_queries_count"], 24)
        self.assertEqual((report["development_count"], report["holdout_count"]), (16, 8))
        self.assertGreaterEqual(report["multiple_relevant_count"], 2)
        self.assertGreaterEqual(report["out_of_domain_count"], 2)
        self.assertEqual(report["proposed_qrels_count"], 24)
        self.assertFalse(report["qrels_fully_reviewed"])

    def test_duplicate_id_across_splits_is_rejected(self):
        d, h, q = self.get_files()
        h["queries"][0]["id"] = d["queries"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicados"):
            validate_dataset(d, h, q, AVAILABLE)

    def test_unknown_note_is_rejected(self):
        d, h, q = self.get_files()
        q["judgments"][0]["relevant_notes"] = ["not-present.md"]
        with self.assertRaisesRegex(ValueError, "desconocidas"):
            validate_dataset(d, h, q, AVAILABLE)

    def test_missing_rationale_is_rejected(self):
        d, h, q = self.get_files()
        q["judgments"][0]["rationale"] = ""
        with self.assertRaisesRegex(ValueError, "justificación"):
            validate_dataset(d, h, q, AVAILABLE)

    def test_cannot_self_certify_an_annotation_without_a_reviewer(self):
        d, h, q = self.get_files()
        q["judgments"][0]["review_status"] = "approved"
        with self.assertRaisesRegex(ValueError, "revisor y fecha"):
            validate_dataset(d, h, q, AVAILABLE)

    def test_frozen_historical_four_are_unchanged(self):
        historical = load_json(EVAL / "historical_queries.json")
        validate_legacy_queries(historical)
        historical["queries"][0]["target"] = "another.md"
        with self.assertRaisesRegex(ValueError, "históricas"):
            validate_legacy_queries(historical)

    def test_holdout_guard_blocks_unreviewed_labels_before_model_load(self):
        with patch.object(sys, "argv", [
            "run_expanded.py", "--split", "holdout", "--allow-holdout",
        ]):
            with self.assertRaisesRegex(ValueError, "revisión humana"):
                run()

    def test_provisional_development_requires_explicit_permission(self):
        with patch.object(sys, "argv", ["run_expanded.py", "--split", "development"]):
            with self.assertRaisesRegex(ValueError, "allow-provisional"):
                run()


class G3MetricsTest(TestCase):
    def test_multi_relevant_recall_precision_and_rr(self):
        result = score_query(
            ["irrelevant.md", "a.md", "irrelevant2.md", "b.md"],
            ["a.md", "b.md"],
        )
        self.assertAlmostEqual(result["recall_at_3"], 0.5)
        self.assertAlmostEqual(result["recall_at_5"], 1.0)
        self.assertAlmostEqual(result["precision_at_3"], 1 / 3)
        self.assertAlmostEqual(result["mrr_at_10"], 0.5)
        self.assertFalse(result["is_out_of_domain"])

    def test_duplicate_chunks_must_not_be_counted_as_multiple_notes(self):
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            score_query(["a.md", "a.md", "b.md"], ["a.md"])

    def test_zero_relevant_notes_do_not_get_invented_recall(self):
        row = score_query(["a.md"], [])
        self.assertIsNone(row["recall_at_3"])
        self.assertIsNone(row["precision_at_3"])
        self.assertTrue(row["forced_hit"])
        self.assertFalse(row["abstained"])
        self.assertTrue(score_query([], [])["abstained"])

    def test_aggregate_excludes_zero_relevance_cases(self):
        relevant = score_query(["a.md", "b.md"], ["b.md"])
        no_answer = score_query(["a.md"], [])
        summary = summarize([
            {"metrics": relevant},
            {"metrics": no_answer},
        ])
        self.assertEqual(summary["query_count"], 2)
        self.assertEqual(summary["in_domain_query_count"], 1)
        self.assertEqual(summary["out_of_domain_query_count"], 1)
        self.assertEqual(summary["mean_recall_at_3"], 1.0)
        self.assertAlmostEqual(summary["mean_precision_at_3"], 1 / 3)
        self.assertEqual(summary["out_of_domain_forced_hit_rate"], 1.0)
        self.assertIsNone(summary["ndcg_at_5"])

    def test_all_ood_is_not_a_valid_recall_benchmark(self):
        with self.assertRaisesRegex(ValueError, "al menos una"):
            summarize([{"metrics": score_query(["anything.md"], [])}])
