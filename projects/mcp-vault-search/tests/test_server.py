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
