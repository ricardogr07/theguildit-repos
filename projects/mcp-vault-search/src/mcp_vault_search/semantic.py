from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .vault import markdown_files, vault_root


class Embedder(Protocol):
    def encode(self, texts: Sequence[str], *, normalize_embeddings: bool) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class Chunk:
    path: str
    text: str
    vector: list[float]


def note_chunks(root: Path, max_chars: int = 1_000) -> list[tuple[str, str]]:
    if max_chars < 100:
        raise ValueError("max_chars debe ser al menos 100")

    root = vault_root(root)
    chunks: list[tuple[str, str]] = []
    for path in markdown_files(root):
        paragraphs = [part.strip() for part in path.read_text(encoding="utf-8").split("\n\n") if part.strip()]
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip()
            if current and len(candidate) > max_chars:
                chunks.append((path.relative_to(root).as_posix(), current))
                current = paragraph
            else:
                current = candidate
        if current:
            chunks.append((path.relative_to(root).as_posix(), current))
    return chunks


def build_index(root: Path, embedder: Embedder, output: Path) -> list[Chunk]:
    source = note_chunks(root)
    vectors = embedder.encode([text for _, text in source], normalize_embeddings=True)
    chunks = [Chunk(path, text, list(map(float, vector))) for (path, text), vector in zip(source, vectors, strict=True)]
    output.write_text(json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False), encoding="utf-8")
    return chunks


def load_index(path: Path) -> list[Chunk]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Chunk(path=item["path"], text=item["text"], vector=item["vector"]) for item in data]


def semantic_search(chunks: Sequence[Chunk], query: str, embedder: Embedder, limit: int = 5) -> list[dict[str, object]]:
    if not query.strip():
        raise ValueError("La consulta no puede estar vacía")
    if limit < 1 or limit > 50:
        raise ValueError("limit debe estar entre 1 y 50")

    query_vector = embedder.encode([query], normalize_embeddings=True)[0]
    scored = [
        (sum(a * b for a, b in zip(chunk.vector, query_vector, strict=True)), chunk)
        for chunk in chunks
    ]
    return [
        {"path": chunk.path, "score": round(float(score), 4), "text": chunk.text[:500]}
        for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
    ]
