import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp_vault_search.semantic import build_index, load_index, note_chunks, semantic_search


class FakeEmbedder:
    def encode(self, texts, *, normalize_embeddings):
        self.normalized = normalize_embeddings
        return [[1.0, 0.0] if "MCP" in text or "agentes" in text else [0.0, 1.0] for text in texts]


class SemanticTest(TestCase):
    def test_chunks_normalize_the_vault_root_before_computing_relative_paths(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nested").mkdir()
            (root / "mcp.md").write_text("MCP", encoding="utf-8")
            self.assertEqual(note_chunks(root / "nested" / ".."), [("mcp.md", "MCP")])

    def test_index_excludes_external_link(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            secret = Path(outside) / "secret.md"
            secret.write_text("PRIVATE_SENTINEL", encoding="utf-8")
            (root / "mcp.md").write_text("MCP", encoding="utf-8")
            try:
                (root / "linked.md").symlink_to(secret)
            except OSError as exc:
                if os.name != "nt":
                    raise
                self.skipTest(f"El entorno no permite crear enlaces: {exc}")
            with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
                chunks = build_index(root, FakeEmbedder(), root / "index.json")
            self.assertEqual([chunk.path for chunk in chunks], ["mcp.md"])
            self.assertNotIn("PRIVATE_SENTINEL", (root / "index.json").read_text(encoding="utf-8"))

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
