"""Offline regression tests for G2 report generation (no model download required)."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from run_g2_baseline import analyze_hits, independently_rank, load_reference


class G2ReportTest(TestCase):
    @staticmethod
    def hits():
        hits = [
            {"path": f"doc{i}.md", "score": round(1 - i / 20, 4),
             "line_start": 1, "line_end": 2}
            for i in range(12)
        ]
        return [hits[0], hits[0], *hits[1:]]

    def test_rank_by_first_unique_chunk_with_scores(self):
        spec = {"query": "consulta", "target": "doc2.md", "distractor": "doc6.md"}
        result = analyze_hits(self.hits(), spec, expected_documents=12)
        self.assertEqual(len(result["top_10_notes"]), 10)
        self.assertEqual(len(result["note_rankings"]), 12)
        self.assertEqual(result["target_position"], 3)
        self.assertEqual(result["distractor_position"], 7)
        self.assertTrue(result["pass"])
        self.assertEqual(result["single_target_recall_at_3"], 1.0)
        self.assertAlmostEqual(result["single_target_reciprocal_rank_at_10"], 1 / 3)
        self.assertEqual(result["top_10_notes"][0]["score"], 1.0)
        self.assertEqual(result["top_10_notes"][0]["line_start"], 1)
        self.assertEqual(independently_rank(self.hits())[:3],
                         ["doc0.md", "doc1.md", "doc2.md"])

    def test_legacy_rule_requires_target_ahead_of_distractor(self):
        spec = {"query": "consulta", "target": "doc2.md", "distractor": "doc1.md"}
        result = analyze_hits(self.hits(), spec, expected_documents=12)
        self.assertFalse(result["pass"])
        self.assertEqual(result["single_target_recall_at_5"], 1.0)

    def test_top_ten_must_be_observable(self):
        spec = {"query": "consulta", "target": "doc2.md", "distractor": "doc1.md"}
        with self.assertRaisesRegex(RuntimeError, "suficientes notas"):
            analyze_hits(self.hits()[:9], spec, expected_documents=12)

    def test_excess_hits_are_rejected(self):
        spec = {"query": "consulta", "target": "doc2.md", "distractor": "doc1.md"}
        with self.assertRaisesRegex(ValueError, "más de 50"):
            analyze_hits(self.hits() * 5, spec, expected_documents=12)

    def test_historical_labels_match_exactly(self):
        reference = Path(__file__).resolve().parents[1] / "evaluate_semantic_results_checkpoint_fixes.json"
        records = load_reference(reference)
        self.assertEqual(len(records), 4)
        self.assertEqual([r["target_position"] for r in records], [5, 1, 1, 3])
        self.assertEqual(sum(r["pass"] for r in records), 2)

    def test_mutated_historical_query_is_rejected(self):
        reference = Path(__file__).resolve().parents[1] / "evaluate_semantic_results_checkpoint_fixes.json"
        records = json.loads(reference.read_text(encoding="utf-8"))
        records[0]["expected_target"] = "other.md"
        with TemporaryDirectory() as temp:
            mutated = Path(temp) / "historical.json"
            mutated.write_text(json.dumps(records), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no coinciden"):
                load_reference(mutated)
