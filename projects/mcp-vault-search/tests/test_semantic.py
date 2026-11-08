import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp_vault_search.semantic import build_index, note_chunks, semantic_search


class FakeEmbedder:
    def encode(self, texts, *, normalize_embeddings):
        self.normalized = normalize_embeddings
        return [[1.0, 0.0] if "MCP" in text or "agentes" in text else [0.0, 1.0] for text in texts]


class SemanticTest(TestCase):
    def test_chunks_normalize_the_vault_root_before_computing_relative_paths(self):
        # Keep the fixture on the working directory's drive on Windows.
        with TemporaryDirectory(dir=Path.cwd()) as temp:
            root = Path(temp)
            (root / "nested").mkdir()
            (root / "mcp.md").write_text("MCP", encoding="utf-8")
            chunks = note_chunks(root / "nested" / "..")
            self.assertEqual([(path, text) for path, text, _, _, _ in chunks], [("mcp.md", "MCP")])
            relative = Path(os.path.relpath(root))
            self.assertFalse(relative.is_absolute())
            chunks = note_chunks(relative)
            self.assertEqual([(path, text) for path, text, _, _, _ in chunks], [("mcp.md", "MCP")])
            built = build_index(relative, FakeEmbedder())
            self.assertEqual([chunk.path for chunk in built], ["mcp.md"])

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
                chunks = build_index(root, FakeEmbedder())
            self.assertEqual([chunk.path for chunk in chunks], ["mcp.md"])
            # Verify sensitive content not indexed
            all_text = " ".join(chunk.text for chunk in chunks)
            self.assertNotIn("PRIVATE_SENTINEL", all_text)

    def test_index_is_json_and_query_ranks_related_note_first(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mcp.md").write_text("MCP conecta herramientas.", encoding="utf-8")
            (root / "docker.md").write_text("Contenedores reproducibles.", encoding="utf-8")
            embedder = FakeEmbedder()

            index = build_index(root, embedder)
            results = semantic_search(index, "agentes", embedder, vault_root_path=root, limit=1)

            self.assertTrue(embedder.normalized)
            self.assertEqual(results[0]["path"], "mcp.md")
            self.assertEqual(results[0]["score"], 1.0)

    def test_semantic_search_skips_stale_chunks(self):
        """When vault content changes, chunks are skipped until reindex."""
    def test_semantic_search_skips_removed_note(self):
        """When note is removed, its chunks are skipped on search."""
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("MCP herramientas", encoding="utf-8")
            (root / "b.md").write_text("Contenedores Docker", encoding="utf-8")
            
            embedder = FakeEmbedder()
            chunks = build_index(root, embedder)
            
            # Remove note; search skips it
            (root / "a.md").unlink()
            results = semantic_search(chunks, "MCP", embedder, vault_root_path=root, limit=5)
            
            # Only b.md remains
            self.assertEqual([r["path"] for r in results], ["b.md"])
    
    def test_semantic_search_skips_changed_note(self):
        """When note content changes, its chunks are skipped until reindex."""
        with TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "test.md"
            note.write_text("MCP herramientas", encoding="utf-8")

            embedder = FakeEmbedder()
            chunks = build_index(root, embedder)

            # Edit note in place
            note.write_text("Docker containers", encoding="utf-8")
            results = semantic_search(chunks, "MCP", embedder, vault_root_path=root, limit=5)

            # Chunk skipped due to hash mismatch
            self.assertEqual(results, [])

    def test_long_paragraph_splits_within_token_limit(self):
        """Paragraph exceeding token limit is split into multiple fragments."""
        try:
            import sentence_transformers
        except ImportError:
            self.skipTest("sentence-transformers not installed")

        with TemporaryDirectory() as temp:
            root = Path(temp)
            # Create a paragraph that exceeds 128 tokens
            # ~150 words, each word ~1 token, exceeds 128 limit
            words = ["herramienta"] * 150
            long_text = " ".join(words)
            (root / "long.md").write_text(long_text, encoding="utf-8")

            embedder = sentence_transformers.SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            chunks = build_index(root, embedder)

            # Verify:
            # 1. Multiple chunks generated (long text split)
            # 2. Content is fully preserved
            self.assertTrue(len(chunks) > 1, "Long paragraph should split into multiple chunks")

            # Verify content preservation: all words present
            all_text = " ".join(chunk.text for chunk in chunks)
            self.assertEqual(all_text.count("herramienta"), 150, "All words should be preserved after split")
