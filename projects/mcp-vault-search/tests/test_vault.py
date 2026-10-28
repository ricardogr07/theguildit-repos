from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp_vault_search.vault import read_note, search_notes, vault_root


class VaultTest(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "mcp.md").write_text(
            "# MCP\n\nMCP conecta agentes con herramientas.\n", encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_search_is_case_insensitive_and_bounded(self):
        matches = search_notes(vault_root(self.root), "mcp", limit=1)
        self.assertEqual(matches[0]["path"], "mcp.md")
        self.assertEqual(len(matches), 1)

    def test_read_note_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            read_note(vault_root(self.root), "../secret.md")

    def test_read_note_returns_markdown(self):
        self.assertIn("herramientas", read_note(vault_root(self.root), "mcp.md"))

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            search_notes(vault_root(self.root), "   ")
