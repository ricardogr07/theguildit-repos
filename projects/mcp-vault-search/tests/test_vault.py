import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from mcp_vault_search.vault import markdown_files, read_note, search_notes, vault_root


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

    def test_invalid_limits_are_rejected(self):
        for limit in (0, 51):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                search_notes(self.root, "MCP", limit)
        with self.assertRaises(ValueError):
            read_note(self.root, "mcp.md", max_chars=0)

    def test_absolute_paths_and_other_extensions_are_rejected(self):
        for path in (str(self.root / "mcp.md"), "note.txt"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                read_note(self.root, path)

    def test_missing_note_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            read_note(self.root, "missing.md")

    def test_invalid_vault_is_reported(self):
        with self.assertRaises(ValueError):
            vault_root(self.root / "missing")

    def test_empty_note_and_exact_boundary(self):
        (self.root / "empty.md").write_text("", encoding="utf-8")
        self.assertEqual(read_note(self.root, "empty.md"), "")
        (self.root / "boundary.md").write_text("á" * 20, encoding="utf-8")
        self.assertEqual(read_note(self.root, "boundary.md", 20), "á" * 20)

    def test_read_is_truncated_without_reading_entire_file(self):
        # Invalid bytes far beyond the requested prefix must never be decoded.
        (self.root / "large.md").write_bytes(b"a" * 100_000 + b"\xff")
        self.assertEqual(
            read_note(self.root, "large.md", 20),
            "a" * 20 + "\n\n[contenido truncado]",
        )

    def test_invalid_utf8_is_skipped_by_search_and_reported_by_read(self):
        (self.root / "a-bad.md").write_bytes(b"\xff\xfe")
        with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
            self.assertEqual(len(search_notes(self.root, "MCP")), 2)
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            read_note(self.root, "a-bad.md")

    def test_unreadable_note_does_not_hide_other_results(self):
        blocked = (self.root / "a-blocked.md").resolve()
        blocked.write_text("MCP", encoding="utf-8")
        original_open = Path.open

        def open_note(path, *args, **kwargs):
            if path == blocked:
                raise PermissionError("Prueba de archivo sin permisos")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_note):
            with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
                self.assertEqual(len(search_notes(self.root, "MCP")), 2)
            with self.assertRaises(PermissionError):
                read_note(self.root, "a-blocked.md")

    def test_late_decoding_error_discards_partial_matches_from_that_note(self):
        (self.root / "a-bad.md").write_bytes(b"MCP\n" + b"x\n" * 10_000 + b"\xff")
        with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
            matches = search_notes(self.root, "MCP")
        self.assertEqual([match["path"] for match in matches], ["mcp.md", "mcp.md"])

    def test_search_order_lines_preview_and_no_matches(self):
        (self.root / "a.md").write_text("none\nMCP " + "x" * 600, encoding="utf-8")
        matches = search_notes(self.root, "mcp", 2)
        self.assertEqual([match["path"] for match in matches], ["a.md", "mcp.md"])
        self.assertEqual(matches[0]["line"], 2)
        self.assertEqual(len(matches[0]["text"]), 500)
        self.assertEqual(search_notes(self.root, "absent"), [])

    def test_nested_markdown_and_uppercase_extension(self):
        (self.root / "nested").mkdir()
        (self.root / "nested" / "note.MD").write_text("Nested MCP", encoding="utf-8")
        self.assertEqual(read_note(self.root, "nested/note.MD"), "Nested MCP")
        self.assertIn("nested/note.MD", [m["path"] for m in search_notes(self.root, "MCP")])

    def make_link(self, link, target, *, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as exc:
            if os.name != "nt":
                raise
            self.skipTest(f"El entorno no permite crear enlaces: {exc}")

    def test_external_file_link_is_excluded_from_search_and_read(self):
        with TemporaryDirectory() as outside:
            secret = Path(outside) / "secret.md"
            secret.write_text("PRIVATE_SENTINEL", encoding="utf-8")
            self.make_link(self.root / "linked.md", secret)
            with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
                self.assertEqual(search_notes(self.root, "PRIVATE_SENTINEL"), [])
            with self.assertRaises(ValueError):
                read_note(self.root, "linked.md")

    def test_internal_file_links_are_also_excluded(self):
        self.make_link(self.root / "linked.md", self.root / "mcp.md")
        with self.assertRaises(ValueError):
            read_note(self.root, "linked.md")
        with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
            self.assertEqual(len(list(markdown_files(self.root))), 1)

    def test_cyclic_link_does_not_interrupt_search(self):
        link = self.root / "loop.md"
        self.make_link(link, link)
        with self.assertLogs("mcp_vault_search.vault", level="WARNING"):
            self.assertEqual(len(search_notes(self.root, "MCP")), 2)
        with self.assertRaises((ValueError, OSError)):
            read_note(self.root, "loop.md")

    def test_external_directory_link_is_not_followed(self):
        with TemporaryDirectory() as outside:
            (Path(outside) / "secret.md").write_text("PRIVATE_SENTINEL", encoding="utf-8")
            self.make_link(self.root / "linked", Path(outside), directory=True)
            self.assertEqual(search_notes(self.root, "PRIVATE_SENTINEL"), [])
            with self.assertRaises(ValueError):
                read_note(self.root, "linked/secret.md")

    @skipUnless(os.name == "nt", "Las junctions son específicas de Windows")
    def test_windows_junction_is_not_followed(self):
        with TemporaryDirectory() as outside:
            (Path(outside) / "secret.md").write_text("PRIVATE_SENTINEL", encoding="utf-8")
            junction = self.root / "junction"
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), outside],
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            try:
                self.assertEqual(search_notes(self.root, "PRIVATE_SENTINEL"), [])
                with self.assertRaises(ValueError):
                    read_note(self.root, "junction/secret.md")
            finally:
                junction.rmdir()
