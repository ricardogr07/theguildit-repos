"""G1 regressions: malformed model output, index lifecycle and evaluator failure."""

import runpy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mcp_vault_search.semantic import Chunk, build_index, note_chunks, semantic_search


_MISSING = object()


class ConfigurableEmbedder:
    def __init__(self, vectors, query_vectors=_MISSING):
        self.vectors = vectors
        self.query_vectors = query_vectors

    def encode(self, texts, *, normalize_embeddings):
        if not normalize_embeddings:
            raise AssertionError("Los embeddings deben solicitarse normalizados")
        if texts == ["consulta"]:
            return [[1.0, 0.0]] if self.query_vectors is _MISSING else self.query_vectors
        return self.vectors


class EmbeddingValidationTest(TestCase):
    def test_build_index_rejects_malformed_vectors(self):
        cases = [
            ([], "vacío"),
            ([0.0, 0.0], "normalizado"),
            ([float("nan"), 0.0], "no finitos"),
            ([float("inf"), 0.0], "no finitos"),
            ([2.0, 0.0], "normalizado"),
            (["invalid", 0.0], "números"),
            (None, "números"),
        ]
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.md").write_text("MCP", encoding="utf-8")
            for vector, message in cases:
                with self.subTest(vector=vector):
                    with self.assertRaisesRegex(ValueError, message):
                        build_index(root, ConfigurableEmbedder([vector]))

    def test_build_index_requires_one_vector_per_chunk(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.md").write_text("MCP", encoding="utf-8")
            for batch in ([], [[1.0, 0.0], [1.0, 0.0]], None):
                with self.subTest(batch=batch):
                    with self.assertRaises(ValueError):
                        build_index(root, ConfigurableEmbedder(batch))

    def test_build_index_rejects_dimensions_that_differ_between_chunks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP", encoding="utf-8")
            (root / "b.md").write_text("Otra nota", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dimensión incompatible"):
                build_index(root, ConfigurableEmbedder([[1.0, 0.0], [1.0, 0.0, 0.0]]))

    def test_query_rejects_malformed_vectors(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP", encoding="utf-8")
            index = build_index(root, ConfigurableEmbedder([[1.0, 0.0]]))
            for query_batch in (
                [], None, [[1.0, 0.0], [1.0, 0.0]],
                [[]], [[0.0, 0.0]], [[2.0, 0.0]],
                [[float("nan"), 0.0]], [[float("inf"), 0.0]],
                [["invalid", 0.0]], [[1.0, 0.0, 0.0]],
            ):
                with self.subTest(query_batch=query_batch):
                    with self.assertRaises(ValueError):
                        semantic_search(index, "consulta",
                                        ConfigurableEmbedder([[1.0, 0.0]], query_batch),
                                        root)

    def test_search_rejects_corrupt_index_vector_even_if_constructed_manually(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP", encoding="utf-8")
            index = build_index(root, ConfigurableEmbedder([[1.0, 0.0]]))
            original = index[0]
            for vector in ([float("nan"), 0.0], [2.0, 0.0], [1.0, 0.0, 0.0]):
                with self.subTest(vector=vector):
                    corrupted = Chunk(original.path, original.text, vector,
                                      original.start_line, original.end_line, original.note_hash)
                    with self.assertRaises(ValueError):
                        semantic_search([corrupted], "consulta",
                                        ConfigurableEmbedder([[1.0, 0.0]]), root)

    def test_empty_index_and_invalid_input_fail_explicitly(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            model = ConfigurableEmbedder([])
            with self.assertRaisesRegex(ValueError, "No chunks found"):
                build_index(root, model)
            with self.assertRaisesRegex(ValueError, "índice semántico está vacío"):
                semantic_search([], "consulta", model, root)
            for query, limit in (("", 5), ("   ", 5), ("consulta", 0), ("consulta", 51)):
                with self.subTest(query=query, limit=limit):
                    with self.assertRaises(ValueError):
                        semantic_search([], query, model, root, limit=limit)

    def test_new_note_does_not_appear_until_reindex(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP", encoding="utf-8")
            model = ConfigurableEmbedder([[1.0, 0.0]])
            index = build_index(root, model)
            (root / "b.md").write_text("Nota nueva", encoding="utf-8")
            self.assertEqual(
                [r["path"] for r in semantic_search(index, "consulta", model, root)],
                ["a.md"],
            )
            updated = build_index(root, ConfigurableEmbedder([[1.0, 0.0], [1.0, 0.0]]))
            self.assertEqual(
                {r["path"] for r in semantic_search(updated, "consulta", model, root)},
                {"a.md", "b.md"},
            )

    def test_source_chunking_with_crlf_and_long_word_does_not_exceed_limits(self):
        class CharacterTokenizer:
            def encode(self, text):
                return [0] * (len(text) + 2)

        with TemporaryDirectory() as temp:
            root = Path(temp)
            original = "cabecera\r\n" + "x" * 260 + "\r\n"
            (root / "long.md").write_bytes(original.encode("utf-8"))
            chunks = note_chunks(root, tokenizer=CharacterTokenizer(),
                                 max_seq_length=32, max_chars=100)
            self.assertTrue(chunks)
            self.assertTrue(all(len(text) <= 100 and len(text) + 2 <= 32
                                for _, text, _, _, _ in chunks))
            self.assertEqual("".join(text for _, text, _, _, _ in chunks), original)
            self.assertTrue(all(start >= 1 and end >= start
                                for _, _, start, end, _ in chunks))

    def test_unrepresentable_character_fails_instead_of_looping(self):
        class ImpossibleTokenizer:
            def encode(self, text):
                return [0] * 10

        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no permite representar"):
                note_chunks(root, tokenizer=ImpossibleTokenizer(), max_seq_length=2)


class EvaluatorFailureTest(TestCase):
    def test_missing_sentence_transformers_fails_with_nonzero_exit(self):
        script = Path(__file__).resolve().parents[1] / "evaluate_semantic.py"
        evaluator = runpy.run_path(str(script), run_name="g1_evaluator_test")
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with patch.object(sys, "argv", [str(script)]):
                with self.assertRaises(SystemExit) as failure:
                    evaluator["main"]()
        self.assertNotEqual(failure.exception.code, 0)

    def test_missing_corpus_is_an_error_not_a_successful_benchmark(self):
        script = Path(__file__).resolve().parents[1] / "evaluate_semantic.py"
        evaluator = runpy.run_path(str(script), run_name="g1_missing_corpus_test")
        def missing_vault(_):
            raise ValueError("MISSING_SYNTHETIC_CORPUS")
        with patch.dict(evaluator["main"].__globals__, {"vault_root": missing_vault}):
            with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace()}):
                with patch.object(sys, "argv", [str(script)]):
                    with self.assertRaisesRegex(ValueError, "MISSING_SYNTHETIC_CORPUS"):
                        evaluator["main"]()

    def test_model_initialization_failure_is_not_swallowed(self):
        script = Path(__file__).resolve().parents[1] / "evaluate_semantic.py"
        evaluator = runpy.run_path(str(script), run_name="g1_model_failure_test")
        class BrokenModel:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("MODEL_INITIALIZATION_FAILED")
        with TemporaryDirectory() as temp:
            with patch.dict(evaluator["main"].__globals__, {"vault_root": lambda _: Path(temp)}):
                with patch.dict(sys.modules, {
                    "sentence_transformers": SimpleNamespace(SentenceTransformer=BrokenModel)
                }):
                    with patch.object(sys, "argv", [str(script)]):
                        with self.assertRaisesRegex(RuntimeError, "MODEL_INITIALIZATION_FAILED"):
                            evaluator["main"]()
