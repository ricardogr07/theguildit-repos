"""Pure document-level retrieval metrics for a ranked list of MCP chunks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence


def unique_note_ranking(results: Sequence[Mapping[str, object]]) -> list[str]:
    """Rank notes by their first matching chunk, preserving original order."""
    notes: list[str] = []
    seen: set[str] = set()
    for result in results:
        path = result.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("Each result must have a nonempty path")
        if path not in seen:
            seen.add(path)
            notes.append(path)
    return notes


def recall_at_k(ranked_notes: Sequence[str], relevant_notes: Iterable[str], k: int) -> float:
    """Fraction of distinct relevant notes retrieved in the first k positions."""
    relevant = set(relevant_notes)
    if k < 1 or not relevant or "" in relevant:
        raise ValueError("k must be positive and relevant_notes nonempty")
    return len(set(ranked_notes[:k]) & relevant) / len(relevant)


def reciprocal_rank_at_k(ranked_notes: Sequence[str], relevant_notes: Iterable[str], k: int) -> float:
    """Reciprocal rank of first relevant note within the first k positions."""
    relevant = set(relevant_notes)
    if k < 1 or not relevant or "" in relevant:
        raise ValueError("k must be positive and relevant_notes nonempty")
    return next((1.0 / rank for rank, note in enumerate(ranked_notes[:k], 1) if note in relevant), 0.0)
