from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server import MCPServer

from .vault import read_note as read_note_file
from .vault import search_notes as search_vault
from .vault import vault_root

mcp = MCPServer("mcp-vault-search")


def configured_root() -> Path:
    return vault_root(os.environ.get("VAULT_PATH", "examples/vault"))


@mcp.tool()
def search_notes(query: str, limit: int = 10) -> str:
    """Busca texto literal en notas Markdown del vault configurado."""
    matches = search_vault(configured_root(), query, limit)
    return json.dumps(matches, ensure_ascii=False, indent=2)


@mcp.tool()
def read_note(path: str) -> str:
    """Lee una nota Markdown usando una ruta relativa al vault configurado."""
    return read_note_file(configured_root(), path)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
