from __future__ import annotations

import logging
import os
import stat
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)


def vault_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"El vault no existe o no es un directorio: {root}")
    return root


def _is_link(path: Path) -> bool:
    """Include Windows junctions and other reparse points in the exclusion."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _note_path(root: Path, relative_path: str) -> Path:
    requested = Path(relative_path)
    if requested.is_absolute() or requested.drive or requested.root or requested.suffix.lower() != ".md":
        raise ValueError("La ruta debe ser relativa y apuntar a un archivo Markdown")

    candidate = root / requested
    try:
        target = candidate.resolve()
    except RuntimeError as exc:
        raise ValueError("No se pudo resolver la ruta: posible enlace cíclico") from exc
    if not target.is_relative_to(root):
        raise ValueError("La ruta sale del vault permitido")
    cursor = candidate
    while cursor != root:
        if _is_link(cursor):
            raise ValueError("No se permiten enlaces ni puntos de reanálisis en el vault")
        cursor = cursor.parent
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    return target


def markdown_files(root: Path) -> Iterator[Path]:
    root = vault_root(root)
    paths: list[Path] = []

    def report_error(error: OSError) -> None:
        logger.warning("No se pudo recorrer el vault: %s", error)

    for directory, directories, filenames in os.walk(root, followlinks=False, onerror=report_error):
        parent = Path(directory)
        safe_directories = []
        for name in directories:
            try:
                if not _is_link(parent / name):
                    safe_directories.append(name)
            except OSError as exc:
                logger.warning("Se omite directorio %s: %s", name, exc)
        directories[:] = safe_directories
        for name in filenames:
            if Path(name).suffix.lower() != ".md":
                continue
            relative = (parent / name).relative_to(root)
            try:
                paths.append(_note_path(root, str(relative)))
            except (OSError, ValueError) as exc:
                logger.warning("Se omite nota %s: %s", relative, exc)
    yield from sorted(paths)


def search_notes(root: Path, query: str, limit: int = 10) -> list[dict[str, object]]:
    term = query.strip().casefold()
    if not term:
        raise ValueError("La consulta no puede estar vacía")
    if limit < 1 or limit > 50:
        raise ValueError("limit debe estar entre 1 y 50")

    root = vault_root(root)
    matches: list[dict[str, object]] = []
    for path in markdown_files(root):
        previous_count = len(matches)
        try:
            # Recheck immediately before opening; this is not an OS sandbox.
            target = _note_path(root, str(path.relative_to(root)))
            with target.open(encoding="utf-8") as source:
                for line_number, line in enumerate(source, 1):
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
        except (OSError, UnicodeError, ValueError) as exc:
            del matches[previous_count:]
            logger.warning("Se omite nota %s: %s", path.relative_to(root), exc)
    return matches


def read_note(root: Path, relative_path: str, max_chars: int = 20_000) -> str:
    if max_chars < 1:
        raise ValueError("max_chars debe ser positivo")

    root = vault_root(root)
    target = _note_path(root, relative_path)
    try:
        with target.open(encoding="utf-8") as source:
            content = source.read(max_chars + 1)
    except UnicodeError as exc:
        raise ValueError(f"La nota no es UTF-8 válido: {relative_path}") from exc
    return content if len(content) <= max_chars else content[:max_chars] + "\n\n[contenido truncado]"
