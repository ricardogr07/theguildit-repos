from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from mcp_vault_search.vault import read_note as read_note_file
from mcp_vault_search.vault import search_notes as search_vault
from mcp_vault_search.vault import vault_root

mcp = MCPServer("mcp-vault-search")


def configured_root() -> Path:
    return vault_root(os.environ.get("VAULT_PATH", "examples/vault"))


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def search_notes(query: str, limit: int = 10) -> str:
    """Busca texto literal en notas Markdown del vault configurado."""
    try:
        matches = search_vault(configured_root(), query, limit)
    except (ValueError, OSError) as exc:
        raise ToolError(str(exc)) from exc
    return json.dumps(matches, ensure_ascii=False, indent=2)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def read_note(path: str) -> str:
    """Lee una nota Markdown usando una ruta relativa al vault configurado."""
    try:
        return read_note_file(configured_root(), path)
    except FileNotFoundError as exc:
        raise ToolError("La nota no existe") from exc
    except PermissionError as exc:
        raise ToolError("No hay permiso para leer la nota") from exc
    except (ValueError, OSError) as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
