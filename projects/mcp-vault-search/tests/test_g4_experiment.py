"""G4 local regression tests; do not load the real embedding model."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from evaluation.experiment_g4 import (
    compare_results,
    mean_of_best_two,
    nearest_percentile,
    synthetic_scale,
)
from evaluation.metrics import score_query
from evaluation.verify_g4 import assert_development_split, assert_candidate_selection


class RankingAlternativeTests(TestCase):
    def test_mean_of_best_two_is_deterministic(self):
        hits = [
            {"path": "b.md", "score": 0.95},
            {"path": "a.md", "score": 0.94},
            {"path": "b.md", "score": 0.10},
            {"path": "a.md", "score": 0.90},
        ]
        self.assertEqual(mean_of_best_two(hits), ["a.md", "b.md"])
        self.assertEqual(mean_of_best_two(list(reversed(hits))), ["a.md", "b.md"])

    def test_single_chunk_documents_have_defined_score(self):
        self.assertEqual(
            mean_of_best_two([{"path": "b.md", "score": 0.5}, {"path": "a.md", "score": 0.8}]),
            ["a.md", "b.md"],
        )

    def test_equal_scores_tie_break_by_path(self):
        self.assertEqual(
            mean_of_best_two([{"path": "b.md", "score": 0.8}, {"path": "a.md", "score": 0.8}]),
            ["a.md", "b.md"],
        )

    def test_nonfinite_chunk_score_fails(self):
        for invalid in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(ValueError, "Non-finite"):
                    mean_of_best_two([{"path": "a.md", "score": invalid}])

    def test_percentile_linear_interpolation_and_invalid_input(self):
        self.assertAlmostEqual(nearest_percentile([4, 1, 3, 2], .5), 2.5)
        self.assertAlmostEqual(nearest_percentile([4, 1, 3, 2], .95), 3.85)
        for values, q in (([], .5), ([1], -1), ([2, 3], 1.1)):
            with self.subTest(values=values, q=q):
                with self.assertRaises(ValueError):
                    nearest_percentile(values, q)

    def test_compare_same_data_does_not_falsely_claim_improvement(self):
        metric = score_query(["a.md", "b.md", "c.md"], ["b.md"])
        out_of_domain = score_query(["a.md"], [])
        results = [
            {
                "id": "D01", "relevant_count": 1,
                "baseline_metrics": metric, "candidate_metrics": metric,
            },
            {
                "id": "D02", "relevant_count": 0,
                "baseline_metrics": out_of_domain, "candidate_metrics": out_of_domain,
            },
        ]
        comparison = compare_results(results)
        self.assertEqual(comparison["delta_b_minus_a"]["mean_recall_at_3"], 0.0)
        self.assertFalse(comparison["pre_registered_candidate_qualification"]["passed_on_provisional_development"])
        self.assertFalse(comparison["pre_registered_candidate_qualification"]["may_merge_to_production"])

    def test_recall_regression_blocks_candidate_even_if_another_query_improves(self):
        miss = score_query(["x.md", "y.md", "z.md", "target.md"], ["target.md"])
        hit = score_query(["target.md", "x.md", "y.md", "z.md"], ["target.md"])
        rows = [
            {"id": "D01", "relevant_count": 1, "baseline_metrics": miss, "candidate_metrics": hit},
            {"id": "D02", "relevant_count": 1, "baseline_metrics": hit, "candidate_metrics": miss},
        ]
        result = compare_results(rows)
        self.assertEqual(result["recall_3_improvement_query_ids"], ["D01"])
        self.assertEqual(result["recall_3_regression_query_ids"], ["D02"])
        self.assertFalse(result["pre_registered_candidate_qualification"]["passed_on_provisional_development"])

    def test_repeated_scaling_uses_reusable_note_source(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            one = root / "one.md"
            one.write_text("# synthetic original", encoding="utf-8")
            notes = [one]
            synthetic_scale(notes, root / "small", 100)
            synthetic_scale(notes, root / "large", 1000)
            self.assertEqual(len(list((root / "small").glob("*.md"))), 100)
            self.assertEqual(len(list((root / "large").glob("*.md"))), 1000)

    def test_empty_source_corpus_fails_explicitly(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "empty source corpus"):
                synthetic_scale([], Path(temp) / "scaled", 100)

    def test_development_verifier_rejects_holdout_ids_disguised_as_development(self):
        root = Path(__file__).resolve().parents[1] / "evaluation"
        dev = json.loads((root / "development_queries.json").read_text(encoding="utf-8"))["queries"]
        hold = json.loads((root / "holdout_queries.json").read_text(encoding="utf-8"))["queries"]
        rows = [
            {"id": row["id"], "query": row["query"], "category": row["category"], "split": "development"}
            for row in dev
        ]
        assert_development_split(rows, dev)
        rows[0] = {
            "id": hold[0]["id"], "query": hold[0]["query"],
            "category": hold[0]["category"], "split": "development",
        }
        with self.assertRaisesRegex(AssertionError, "non-development"):
            assert_development_split(rows, dev)

    def test_verifier_rejects_forged_positive_qualification(self):
        metric = score_query(["a.md", "b.md", "c.md"], ["a.md"])
        rows = [{"id": "D01", "relevant_count": 1,
                 "baseline_metrics": metric, "candidate_metrics": metric}]
        report = compare_results(rows)
        assert_candidate_selection(rows, report)
        report["pre_registered_candidate_qualification"]["passed_on_provisional_development"] = True
        with self.assertRaisesRegex(AssertionError, "Qualification decision"):
            assert_candidate_selection(rows, report)

    def test_verifier_rejects_suppressed_regression_ids(self):
        hit = score_query(["a.md", "b.md", "c.md"], ["a.md"])
        miss = score_query(["x.md", "y.md", "z.md", "a.md"], ["a.md"])
        rows = [{"id": "D01", "relevant_count": 1,
                 "baseline_metrics": hit, "candidate_metrics": miss}]
        report = compare_results(rows)
        self.assertEqual(report["recall_3_regression_query_ids"], ["D01"])
        report["recall_3_regression_query_ids"] = []
        with self.assertRaisesRegex(AssertionError, "regression lists"):
            assert_candidate_selection(rows, report)

    def test_scaled_synthetic_corpus_is_deterministic_and_unique_by_path(self):
        with TemporaryDirectory() as temp:
            temp_path = Path(temp)
            notes = [temp_path / "original.md"]
            notes[0].write_text("# Nota sintética\nMCP\n", encoding="utf-8")
            destination = temp_path / "scale"
            synthetic_scale(notes, destination, 100)
            created = sorted(destination.glob("*.md"))
            self.assertEqual(len(created), 100)
            self.assertEqual(len({p.name for p in created}), 100)
            self.assertTrue(all(p.read_text(encoding="utf-8") == notes[0].read_text(encoding="utf-8")
                                for p in created))
