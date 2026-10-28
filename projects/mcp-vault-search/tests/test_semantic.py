from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp_vault_search.semantic import build_index, load_index, semantic_search


class FakeEmbedder:
    def encode(self, texts, *, normalize_embeddings):
        self.normalized = normalize_embeddings
        return [[1.0, 0.0] if "MCP" in text or "agentes" in text else [0.0, 1.0] for text in texts]


class SemanticTest(TestCase):
    def test_index_is_json_and_query_ranks_related_note_first(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mcp.md").write_text("MCP conecta herramientas.", encoding="utf-8")
            (root / "docker.md").write_text("Contenedores reproducibles.", encoding="utf-8")
            index_path = root / "index.json"
            embedder = FakeEmbedder()

            build_index(root, embedder, index_path)
            results = semantic_search(load_index(index_path), "agentes", embedder, limit=1)

            self.assertTrue(embedder.normalized)
            self.assertEqual(results[0]["path"], "mcp.md")
            self.assertEqual(results[0]["score"], 1.0)
