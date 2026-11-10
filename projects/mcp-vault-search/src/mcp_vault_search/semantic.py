from __future__ import annotations

import hashlib
import logging
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .vault import _note_path, markdown_files, vault_root


logger = logging.getLogger(__name__)
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


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
    """Split at whitespace when possible, retaining the exact source text."""
    result = []
    position = 0
    while position < len(paragraph):
        end = min(position + max_chars, len(paragraph))
        if end < len(paragraph):
            boundary = max(paragraph.rfind(space, position, end) for space in " \t\r\n")
            if boundary > position:
                end = boundary + 1
        result.append(paragraph[position:end])
        position = end
    return result


def _split_by_tokens(text: str, tokenizer, max_tokens: int) -> list[str]:
    """Retain source slices whose encoded length includes special tokens."""
    if tokenizer is None:
        return _split_paragraph(text, max_tokens * 4)
    result = []
    position = 0
    while position < len(text):
        if len(tokenizer.encode(text[position:])) <= max_tokens:
            result.append(text[position:])
            break

        left, right = position, len(text)
        end = position
        while left < right:
            middle = (left + right + 1) // 2
            if len(tokenizer.encode(text[position:middle])) <= max_tokens:
                end = middle
                left = middle
            else:
                right = middle - 1

        boundary = max(text.rfind(space, position, end) for space in " \t\r\n")
        if boundary > position:
            end = boundary + 1
            content_end = position + len(text[position:end].rstrip(" \t"))
            if content_end > position:
                end = content_end
        # A different prefix boundary can tokenize differently. Verify the slice.
        while end > position and len(tokenizer.encode(text[position:end])) > max_tokens:
            end -= 1
        if end == position:
            raise ValueError("El límite de tokens no permite representar el texto")
        result.append(text[position:end])
        position = end
    return result


def _compute_content_hash(text: str) -> str:
    """Hash the full decoded UTF-8 content, including whitespace and line endings."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def note_chunks(root: Path, max_chars: int = 1_000, tokenizer=None, max_seq_length: int = 128) -> list[tuple[str, str, int, int, str]]:
    """Return source slices with inclusive, one-based line ranges and a note hash."""
    if max_chars < 100:
        raise ValueError("max_chars debe ser al menos 100")
    if max_seq_length < 1:
        raise ValueError("max_seq_length debe ser positivo")

    root = vault_root(root)
    chunks: list[tuple[str, str, int, int, str]] = []
    for path in markdown_files(root):
        relative_path = path.relative_to(root).as_posix()
        try:
            target = _note_path(root, relative_path)
            content = target.read_bytes().decode("utf-8")
        except (OSError, UnicodeError, ValueError) as exc:
            logger.warning("Se omite nota %s: %s", relative_path, exc)
            continue

        note_hash = _compute_content_hash(content)
        line_starts = []
        paragraphs = []
        paragraph_start = None
        offset = 0
        for line in content.splitlines(keepends=True):
            line_starts.append(offset)
            if line.strip():
                if paragraph_start is None:
                    paragraph_start = offset
            elif paragraph_start is not None:
                paragraphs.append((paragraph_start, offset))
                paragraph_start = None
            offset += len(line)
        if paragraph_start is not None:
            paragraphs.append((paragraph_start, len(content)))

        spans = []
        chunk_start = None
        chunk_end = 0
        for start, end in paragraphs:
            position = start
            for paragraph_piece in _split_paragraph(content[start:end], max_chars):
                pieces = [paragraph_piece]
                if tokenizer is not None:
                    pieces = _split_by_tokens(paragraph_piece, tokenizer, max_seq_length)
                for piece in pieces:
                    piece_end = position + len(piece)
                    if chunk_start is not None:
                        candidate = content[chunk_start:piece_end]
                        fits = len(candidate) <= max_chars
                        if tokenizer is not None:
                            fits = fits and len(tokenizer.encode(candidate)) <= max_seq_length
                        if not fits:
                            spans.append((chunk_start, chunk_end))
                            chunk_start = None
                    if chunk_start is None:
                        chunk_start = position
                    chunk_end = piece_end
                    position = piece_end
        if chunk_start is not None:
            spans.append((chunk_start, chunk_end))

        for start, end in spans:
            chunks.append((
                relative_path,
                content[start:end],
                bisect_right(line_starts, start),
                bisect_right(line_starts, end - 1),
                note_hash,
            ))
    return chunks


def build_index(root: Path, embedder: Embedder) -> list[Chunk]:
    """Build in-memory index from vault. Returns chunks without persistence."""
    # Extract tokenizer and max_seq_length from embedder for token-aware chunking
    tokenizer = None
    max_seq_length = 128  # sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 default

    if hasattr(embedder, 'tokenizer'):
        tokenizer = embedder.tokenizer
    if hasattr(embedder, 'max_seq_length'):
        max_seq_length = embedder.max_seq_length

    source = note_chunks(root, tokenizer=tokenizer, max_seq_length=max_seq_length)
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

    vault_root_path = vault_root(vault_root_path)
    query_vector = embedder.encode([query], normalize_embeddings=True)[0]
    scored = [
        (sum(a * b for a, b in zip(chunk.vector, query_vector, strict=True)), chunk)
        for chunk in chunks
    ]

    results = []
    note_validity: dict[str, bool] = {}  # Cache: path -> is_valid (True/False)

    for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True):
        # Check validity cache; validate once per note per query
        if chunk.path not in note_validity:
            try:
                # Apply vault access rules (same as search_notes/read_note)
                note_path = _note_path(vault_root_path, chunk.path)
                current_content = note_path.read_bytes().decode("utf-8")
                # Validate freshness: compare hash of full note
                is_valid = _compute_content_hash(current_content) == chunk.note_hash
                note_validity[chunk.path] = is_valid
            except (OSError, UnicodeError, ValueError):
                note_validity[chunk.path] = False  # Mark as invalid

        # Skip all chunks from invalid notes
        if not note_validity[chunk.path]:
            continue

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
