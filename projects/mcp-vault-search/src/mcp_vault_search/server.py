from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from mcp_vault_search.semantic import build_index, semantic_search
from mcp_vault_search.vault import read_note as read_note_file
from mcp_vault_search.vault import search_notes as search_vault
from mcp_vault_search.vault import vault_root

logger = logging.getLogger(__name__)
mcp = MCPServer("mcp-vault-search")

# Lazy-loaded semantic index
_semantic_index = None
_semantic_enabled = bool(os.environ.get("VAULT_SEMANTIC"))


def configured_root() -> Path:
    return vault_root(os.environ.get("VAULT_PATH", "examples/vault"))


def _ensure_semantic_index():
    """Load or build semantic index on first use."""
    global _semantic_index
    if _semantic_index is not None:
        return _semantic_index

    root = configured_root()
    try:
        import sentence_transformers
    except ImportError:
        raise ToolError("sentence-transformers not installed; install with --extra semantic")

    embedder = sentence_transformers.SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    _semantic_index = build_index(root, embedder, root / ".index.json")
    return _semantic_index


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


# Only register semantic search if explicitly enabled
if _semantic_enabled:
    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
    def search_semantic(query: str, limit: int = 5) -> str:
        """Busca notas por similitud semántica usando embeddings."""
        try:
            index = _ensure_semantic_index()
            # Re-import embedder for each search
            try:
                import sentence_transformers
                embedder = sentence_transformers.SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            except ImportError as exc:
                raise ToolError("sentence-transformers no disponible") from exc

            results = semantic_search(index, query, embedder, configured_root(), limit)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except ToolError:
            raise
        except Exception as exc:
            logger.exception("Error en búsqueda semántica")
            raise ToolError(f"Error interno: {exc}") from exc

        return json.dumps(results, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
