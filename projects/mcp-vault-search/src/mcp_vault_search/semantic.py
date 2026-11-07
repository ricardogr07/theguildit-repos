from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .vault import markdown_files, vault_root, _note_path


class Embedder(Protocol):
    def encode(self, texts: Sequence[str], *, normalize_embeddings: bool) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class Chunk:
    path: str
    text: str
    vector: list[float]
    start_line: int = 0
    end_line: int = 0
    note_hash: str = ""  # SHA-256 hash of full note; same for all chunks from note


def _split_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split a single paragraph if it exceeds max_chars."""
    if len(paragraph) <= max_chars:
        return [paragraph]
    lines = paragraph.split("\n")
    result = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}".strip() if current else line
        if current and len(candidate) > max_chars:
            result.append(current)
            current = line
        else:
            current = candidate
    if current:
        result.append(current)
    return result or [paragraph]


def _compute_content_hash(text: str) -> str:
    """SHA-256 hash of normalized text."""
    normalized = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def note_chunks(root: Path, max_chars: int = 1_000) -> list[tuple[str, str, int, int, str]]:
    """Generate (path, text, start_line, end_line, note_hash) for each paragraph."""
    if max_chars < 100:
        raise ValueError("max_chars debe ser al menos 100")

    root = vault_root(root)
    chunks: list[tuple[str, str, int, int, str]] = []
    for path in markdown_files(root):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue

        note_hash = _compute_content_hash(content)
        lines = content.split("\n")

        # Group lines into paragraphs separated by blank lines
        paragraphs: list[tuple[int, int, str]] = []
        current_start = 0
        current_lines = []
        for i, line in enumerate(lines):
            if line.strip():
                current_lines.append(line)
            elif current_lines:
                para_text = "\n".join(current_lines).strip()
                paragraphs.append((current_start, i, para_text))
                current_lines = []
                current_start = i + 1
        if current_lines:
            para_text = "\n".join(current_lines).strip()
            paragraphs.append((current_start, len(lines) - 1, para_text))

        # Chunk paragraphs, splitting long ones
        current_chunk = ""
        chunk_start = 0
        for start_line, end_line, para_text in paragraphs:
            for sub_para in _split_paragraph(para_text, max_chars):
                candidate = f"{current_chunk}\n\n{sub_para}".strip() if current_chunk else sub_para
                if current_chunk and len(candidate) > max_chars:
                    chunks.append((path.relative_to(root).as_posix(), current_chunk, chunk_start, end_line, note_hash))
                    current_chunk = sub_para
                    chunk_start = start_line
                else:
                    current_chunk = candidate
                    if not chunk_start:
                        chunk_start = start_line

        if current_chunk:
            chunks.append((path.relative_to(root).as_posix(), current_chunk, chunk_start, len(lines) - 1, note_hash))

    return chunks


def build_index(root: Path, embedder: Embedder) -> list[Chunk]:
    """Build in-memory index from vault. Returns chunks without persistence."""
    source = note_chunks(root)
    if not source:
        raise ValueError("No chunks found in vault")

    texts = [text for _, text, _, _, _ in source]
    vectors = embedder.encode(texts, normalize_embeddings=True)
    chunks = [
        Chunk(
            path=path,
            text=text,
            vector=list(map(float, vector)),
            start_line=start_line,
            end_line=end_line,
            note_hash=note_hash,
        )
        for (path, text, start_line, end_line, note_hash), vector in zip(source, vectors, strict=True)
    ]
    return chunks


def semantic_search(chunks: Sequence[Chunk], query: str, embedder: Embedder, vault_root_path: Path, limit: int = 5) -> list[dict[str, object]]:
    """Search chunks by similarity, validating freshness and vault access."""
    if not query.strip():
        raise ValueError("La consulta no puede estar vacía")
    if limit < 1 or limit > 50:
        raise ValueError("limit debe estar entre 1 y 50")

    query_vector = embedder.encode([query], normalize_embeddings=True)[0]
    scored = [
        (sum(a * b for a, b in zip(chunk.vector, query_vector, strict=True)), chunk)
        for chunk in chunks
    ]

    results = []
    seen_paths = set()  # Track which notes we've validated in this query

    for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True):
        # Validate each note once per query
        if chunk.path not in seen_paths:
            seen_paths.add(chunk.path)
            try:
                # Apply vault access rules (same as search_notes/read_note)
                note_path = _note_path(vault_root_path, chunk.path)
                current_content = note_path.read_text(encoding="utf-8")
                # Validate freshness: compare hash of full note
                if _compute_content_hash(current_content) != chunk.note_hash:
                    continue  # Note changed; skip all chunks from this note
            except (OSError, UnicodeError, ValueError):
                continue  # Note inaccessible, invalid, or outside vault; skip all chunks

        # If we reach here, note passed validation; include this chunk
        results.append({
            "path": chunk.path,
            "text": chunk.text[:500],
            "score": round(float(score), 4),
            "line_start": chunk.start_line,
            "line_end": chunk.end_line,
        })

        if len(results) == limit:
            break

    return results
