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
    """Split a single paragraph if it exceeds max_chars, breaking long lines if needed."""
    if len(paragraph) <= max_chars:
        return [paragraph]
    lines = paragraph.split("\n")
    result = []
    current = ""
    for line in lines:
        # Force-break lines that exceed max_chars individually, preserving word boundaries
        if len(line) > max_chars:
            if current:
                result.append(current)
                current = ""
            # Break long line into max_chars chunks, respecting word boundaries (spaces)
            pos = 0
            while pos < len(line):
                chunk_end = min(pos + max_chars, len(line))
                # Find last space in chunk [pos, chunk_end)
                chunk = line[pos:chunk_end]
                last_space = chunk.rfind(" ")
                if last_space > 0:
                    chunk_end = pos + last_space
                result.append(line[pos:chunk_end].rstrip())
                pos = chunk_end
                # Skip whitespace
                while pos < len(line) and line[pos] == " ":
                    pos += 1
            continue

        candidate = f"{current}\n{line}".strip() if current else line
        if current and len(candidate) > max_chars:
            result.append(current)
            current = line
        else:
            current = candidate
    if current:
        result.append(current)
    return result or [paragraph]


def _split_by_tokens(text: str, tokenizer, max_tokens: int) -> list[str]:
    """Split text into fragments, each ≤ max_tokens when encoded.

    Uses binary search to find split point, always at word boundary (space).
    Preserves all content: concatenated fragments == original text.
    ponytail: naive binary search; optimize if performance matters.
    """
    if tokenizer is None:
        # Fallback: char-based split at max_tokens * 4 (rough estimate)
        max_chars = max_tokens * 4
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    token_count = len(tokenizer.encode(text))
    if token_count <= max_tokens:
        return [text]

    # Binary search for largest substring that fits in max_tokens
    result = []
    pos = 0
    while pos < len(text):
        # Binary search: find largest substring starting at pos that fits max_tokens
        left, right = pos, len(text)
        best_split = pos + 1  # At least one character from current position

        while left < right:
            mid = (left + right + 1) // 2
            chunk = text[pos:mid]
            if len(tokenizer.encode(chunk)) <= max_tokens:
                best_split = mid
                left = mid
            else:
                right = mid - 1

        # Find last space in region [pos, best_split) to preserve word boundaries
        search_region = text[pos:best_split]
        last_space_offset = search_region.rfind(" ")

        if last_space_offset > 0:
            # Split at last space within region
            split_pos = pos + last_space_offset
        else:
            # No space found; split at best_split anyway (avoid infinite loop on single long word)
            split_pos = best_split

        # Extract fragment and add to result
        fragment = text[pos:split_pos].strip()
        if fragment:
            result.append(fragment)

        # Skip whitespace and continue
        pos = split_pos
        while pos < len(text) and text[pos].isspace():
            pos += 1

    return result


def _compute_content_hash(text: str) -> str:
    """SHA-256 hash of normalized text."""
    normalized = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def note_chunks(root: Path, max_chars: int = 1_000, tokenizer=None, max_seq_length: int = 128) -> list[tuple[str, str, int, int, str]]:
    """Generate (path, text, start_line, end_line, note_hash) for each paragraph.

    If tokenizer provided, validates each chunk respects token limit before grouping.
    max_seq_length: model's max sequence length (account for [CLS]/[SEP] ~2 tokens).
    ponytail: token validation only if embedder+tokenizer provided to caller.
    """
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

        # Chunk paragraphs, splitting long ones; validate token limit if tokenizer available
        current_chunk = ""
        chunk_start = 0
        for start_line, end_line, para_text in paragraphs:
            for sub_para in _split_paragraph(para_text, max_chars):
                candidate = f"{current_chunk}\n\n{sub_para}".strip() if current_chunk else sub_para

                # Check token limit if tokenizer available; tokenizer.encode() includes [CLS]/[SEP]
                exceeds_tokens = False
                if tokenizer is not None:
                    token_count = len(tokenizer.encode(candidate))
                    exceeds_tokens = token_count > max_seq_length  # max_seq_length already includes special tokens

                if current_chunk and (len(candidate) > max_chars or exceeds_tokens):
                    chunks.append((path.relative_to(root).as_posix(), current_chunk, chunk_start, end_line, note_hash))
                    # Handle new chunk; split if it exceeds token limit
                    if tokenizer is not None:
                        token_count = len(tokenizer.encode(sub_para))
                        if token_count > max_seq_length:
                            # Split and emit fragments individually
                            for frag in _split_by_tokens(sub_para, tokenizer, max_seq_length):
                                chunks.append((path.relative_to(root).as_posix(), frag, start_line, end_line, note_hash))
                            current_chunk = ""
                            chunk_start = 0
                        else:
                            current_chunk = sub_para
                            chunk_start = start_line
                    else:
                        current_chunk = sub_para
                        chunk_start = start_line
                elif not current_chunk and tokenizer is not None and sub_para.strip():
                    # Handle single sub_para; split if it exceeds token limit
                    token_count = len(tokenizer.encode(sub_para))
                    if token_count > max_seq_length:
                        # Split and emit fragments individually
                        for frag in _split_by_tokens(sub_para, tokenizer, max_seq_length):
                            chunks.append((path.relative_to(root).as_posix(), frag, start_line, start_line, note_hash))
                        current_chunk = ""
                        chunk_start = 0
                    else:
                        current_chunk = sub_para
                        if not chunk_start:
                            chunk_start = start_line
                else:
                    current_chunk = candidate
                    if not chunk_start:
                        chunk_start = start_line

        if current_chunk:
            # Handle final chunk; split if it exceeds token limit
            if tokenizer is not None:
                token_count = len(tokenizer.encode(current_chunk))
                if token_count > max_seq_length:
                    # Split and emit fragments individually
                    for frag in _split_by_tokens(current_chunk, tokenizer, max_seq_length):
                        chunks.append((path.relative_to(root).as_posix(), frag, chunk_start, len(lines) - 1, note_hash))
                else:
                    chunks.append((path.relative_to(root).as_posix(), current_chunk, chunk_start, len(lines) - 1, note_hash))
            else:
                chunks.append((path.relative_to(root).as_posix(), current_chunk, chunk_start, len(lines) - 1, note_hash))

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
                current_content = note_path.read_text(encoding="utf-8")
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
