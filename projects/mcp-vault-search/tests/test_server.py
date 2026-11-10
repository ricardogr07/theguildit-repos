import asyncio
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ServerTest(TestCase):
    def test_installed_entrypoint_over_stdio(self):
        executable = shutil.which("mcp-vault-search")
        self.assertIsNotNone(executable, "Instala el paquete y ejecuta las pruebas con uv run")
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mcp.md").write_text("# MCP\nHerramientas locales", encoding="utf-8")
            asyncio.run(asyncio.wait_for(self.check_server(executable, root), timeout=30))

    async def check_server(self, executable, root):
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.pop("VAULT_SEMANTIC", None)
        environment["VAULT_PATH"] = str(root)
        parameters = StdioServerParameters(command=executable, args=[], env=environment)
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                self.assertEqual({tool.name for tool in tools.tools}, {"search_notes", "read_note"})
                self.assertTrue(all(tool.annotations.read_only_hint for tool in tools.tools))
                search = await client.call_tool("search_notes", {"query": "mcp", "limit": 1})
                self.assertFalse(search.is_error)
                matches = json.loads(search.content[0].text)
                self.assertEqual(matches, [{"path": "mcp.md", "line": 1, "text": "# MCP"}])
                note = await client.call_tool("read_note", {"path": "mcp.md"})
                self.assertFalse(note.is_error)
                self.assertIn("Herramientas locales", note.content[0].text)
                for name, arguments, message in (
                    ("read_note", {"path": "../secret.md"}, "La ruta sale del vault permitido"),
                    ("read_note", {"path": "missing.md"}, "La nota no existe"),
                    ("search_notes", {"query": " "}, "La consulta no puede estar vacía"),
                    ("search_notes", {"query": "MCP", "limit": 51}, "limit debe estar entre 1 y 50"),
                ):
                    result = await client.call_tool(name, arguments)
                    self.assertTrue(result.is_error, (name, arguments))
                    self.assertIn(message, result.content[0].text)
                # Tool errors must leave the session usable.
                self.assertEqual(len((await client.list_tools()).tools), 2)

    def test_semantic_entrypoint_filters_edits_and_deletions_in_same_session(self):
        executable = shutil.which("mcp-vault-search")
        self.assertIsNotNone(executable)
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            root = directory / "vault"
            root.mkdir()
            for name in "abcdefg":
                (root / f"{name}.md").write_text("# Note\n\nif allowed:\n    run()\n", encoding="utf-8")
            # A local model substitute keeps the installed MCP process test offline.
            (directory / "sentence_transformers.py").write_text(
                "class Tokenizer:\n"
                "    def encode(self, text):\n"
                "        return [0] * (len(text.split()) + 2)\n"
                "class SentenceTransformer:\n"
                "    tokenizer = Tokenizer()\n"
                "    max_seq_length = 128\n"
                "    def __init__(self, name, *, revision, device):\n"
                "        pass\n"
                "    def encode(self, texts, *, normalize_embeddings):\n"
                "        return [[1.0, 0.0] for text in texts]\n",
                encoding="utf-8",
            )
            asyncio.run(asyncio.wait_for(self.check_semantic_server(executable, directory, root), timeout=30))

    async def check_semantic_server(self, executable, directory, root):
        environment = dict(os.environ)
        environment.update(VAULT_PATH=str(root), VAULT_SEMANTIC="1", PYTHONPATH=str(directory))
        parameters = StdioServerParameters(command=executable, args=[], env=environment)
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                self.assertEqual({tool.name for tool in tools.tools}, {"search_notes", "read_note", "search_semantic"})
                first = await client.call_tool("search_semantic", {"query": "note", "limit": 5})
                self.assertFalse(first.is_error)
                results = json.loads(first.content[0].text)
                self.assertEqual([item["path"] for item in results], [f"{name}.md" for name in "abcde"])
                self.assertEqual((results[0]["line_start"], results[0]["line_end"]), (1, 4))

                (root / "a.md").write_text("# Note\n\nif allowed:\nrun()\n", encoding="utf-8")
                edited = await client.call_tool("search_semantic", {"query": "note", "limit": 5})
                self.assertFalse(edited.is_error)
                self.assertEqual([item["path"] for item in json.loads(edited.content[0].text)], [f"{name}.md" for name in "bcdef"])
                (root / "b.md").unlink()
                removed = await client.call_tool("search_semantic", {"query": "note", "limit": 5})
                self.assertFalse(removed.is_error)
                self.assertEqual([item["path"] for item in json.loads(removed.content[0].text)], [f"{name}.md" for name in "cdefg"])
                self.assertEqual(sorted(path.name for path in root.iterdir()), [f"{name}.md" for name in "acdefg"])
