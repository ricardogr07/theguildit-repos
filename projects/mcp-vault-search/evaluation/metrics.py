"""G3 document-level metrics with a separate no-answer protocol.

Unjudged queries must not silently count as reviewed. A semantic retriever with
no rejection threshold always returns candidates even for out-of-domain input.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def score_query(ranked_notes: Sequence[str], relevant_notes: Iterable[str]) -> dict:
    """Evaluate a complete *unique-note* ranking, not duplicate chunk hits."""
    ranked = list(ranked_notes)
    if len(set(ranked)) != len(ranked):
        raise ValueError("El ranking contiene notas duplicadas; deduplica chunks primero")
    if any(not isinstance(name, str) or not name for name in ranked):
        raise ValueError("Los resultados deben tener rutas de nota no vacías")
    relevant = set(relevant_notes)
    if any(not isinstance(name, str) or not name for name in relevant):
        raise ValueError("Las notas relevantes deben tener rutas válidas")

    if not relevant:
        # Recall is undefined when there is no relevant document.  Do not
        # average these queries into regular recall, MRR, or precision.
        return {
            "relevant_count": 0,
            "is_out_of_domain": True,
            "recall_at_3": None,
            "recall_at_5": None,
            "precision_at_3": None,
            "mrr_at_10": None,
            "abstained": len(ranked) == 0,
            "forced_hit": len(ranked) > 0,
        }

    hit3 = len(set(ranked[:3]) & relevant)
    hit5 = len(set(ranked[:5]) & relevant)
    first_rank = next((i for i, note in enumerate(ranked[:10], 1) if note in relevant), None)
    return {
        "relevant_count": len(relevant),
        "is_out_of_domain": False,
        "recall_at_3": hit3 / len(relevant),
        "recall_at_5": hit5 / len(relevant),
        "precision_at_3": hit3 / 3,
        "mrr_at_10": 1 / first_rank if first_rank is not None else 0.0,
        "abstained": len(ranked) == 0,
        "forced_hit": False,
    }


def summarize(rows: Sequence[dict]) -> dict:
    """Macro-average relevant queries only; separate zero-relevance diagnostics."""
    if not rows:
        raise ValueError("No hay consultas que resumir")
    in_domain = [row["metrics"] for row in rows if not row["metrics"]["is_out_of_domain"]]
    out_of_domain = [row["metrics"] for row in rows if row["metrics"]["is_out_of_domain"]]
    if not in_domain:
        raise ValueError("Se requiere al menos una consulta con documentos relevantes")

    result = {
        "query_count": len(rows),
        "in_domain_query_count": len(in_domain),
        "out_of_domain_query_count": len(out_of_domain),
        "mean_recall_at_3": sum(row["recall_at_3"] for row in in_domain) / len(in_domain),
        "mean_recall_at_5": sum(row["recall_at_5"] for row in in_domain) / len(in_domain),
        "mean_precision_at_3": sum(row["precision_at_3"] for row in in_domain) / len(in_domain),
        "mrr_at_10": sum(row["mrr_at_10"] for row in in_domain) / len(in_domain),
        "out_of_domain_abstention_rate": (
            sum(row["abstained"] for row in out_of_domain) / len(out_of_domain)
            if out_of_domain else None
        ),
        "out_of_domain_forced_hit_rate": (
            sum(row["forced_hit"] for row in out_of_domain) / len(out_of_domain)
            if out_of_domain else None
        ),
        "no_answer_protocol": "No threshold or abstention policy exists in the current retriever.",
        "ndcg_at_5": None,
        "ndcg_note": "Not computed: binary judgments only; graded human relevance unavailable.",
    }
    return result
