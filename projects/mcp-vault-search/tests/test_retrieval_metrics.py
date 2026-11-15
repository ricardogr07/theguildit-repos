from unittest import TestCase

from mcp_vault_search.retrieval_metrics import recall_at_k, reciprocal_rank_at_k, unique_note_ranking


class RetrievalMetricsTest(TestCase):
    def test_deduplicates_chunks_before_ranking(self):
        chunks = [{"path": "a.md"}, {"path": "a.md"}, {"path": "b.md"}, {"path": "a.md"}]
        self.assertEqual(unique_note_ranking(chunks), ["a.md", "b.md"])

    def test_recall_with_multiple_relevant_notes(self):
        self.assertEqual(recall_at_k(["a.md", "b.md", "c.md"], ["b.md", "c.md"], 2), 0.5)
        self.assertEqual(recall_at_k(["a.md", "b.md", "c.md"], ["b.md", "c.md"], 3), 1.0)

    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank_at_k(["a.md", "b.md"], ["b.md"], 10), 0.5)
        self.assertEqual(reciprocal_rank_at_k(["a.md", "b.md"], ["b.md"], 1), 0.0)

    def test_historical_baseline(self):
        positions = [5, 1, 1, 3]
        recall = sum(
            recall_at_k([f"other-{i}" for i in range(p - 1)] + ["target.md"], ["target.md"], 3)
            for p in positions
        ) / len(positions)
        mrr = sum(
            reciprocal_rank_at_k([f"other-{i}" for i in range(p - 1)] + ["target.md"], ["target.md"], 10)
            for p in positions
        ) / len(positions)
        self.assertEqual(recall, 0.75)
        self.assertAlmostEqual(mrr, 0.6333333333333333)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            unique_note_ranking([{"path": ""}])
        with self.assertRaises(ValueError):
            recall_at_k([], [], 3)
        with self.assertRaises(ValueError):
            reciprocal_rank_at_k([], ["a.md"], 0)
