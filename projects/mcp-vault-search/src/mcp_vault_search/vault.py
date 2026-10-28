from __future__ import annotations

from pathlib import Path


def vault_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"El vault no existe o no es un directorio: {root}")
    return root


def markdown_files(root: Path):
    yield from sorted(root.rglob("*.md"))


def search_notes(root: Path, query: str, limit: int = 10) -> list[dict[str, object]]:
    term = query.strip().casefold()
    if not term:
        raise ValueError("La consulta no puede estar vacía")
    if limit < 1 or limit > 50:
        raise ValueError("limit debe estar entre 1 y 50")

    matches: list[dict[str, object]] = []
    for path in markdown_files(root):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if term in line.casefold():
                matches.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip()[:500],
                    }
                )
                if len(matches) == limit:
                    return matches
    return matches


def read_note(root: Path, relative_path: str, max_chars: int = 20_000) -> str:
    if max_chars < 1:
        raise ValueError("max_chars debe ser positivo")

    requested = Path(relative_path)
    if requested.is_absolute() or requested.suffix.lower() != ".md":
        raise ValueError("La ruta debe ser relativa y apuntar a un archivo Markdown")

    target = (root / requested).resolve()
    if not target.is_relative_to(root):
        raise ValueError("La ruta sale del vault permitido")
    if not target.is_file():
        raise FileNotFoundError(relative_path)

    content = target.read_text(encoding="utf-8")
    return content if len(content) <= max_chars else content[:max_chars] + "\n\n[contenido truncado]"
