"""Validate frozen evaluation splits and provisional/approved qrels."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"El archivo {path} debe contener un objeto JSON")
    return result


def validate_dataset(
    development: dict, holdout: dict, qrels: dict, available_notes: set[str]
) -> dict:
    """Reject leakage, incomplete labels, unknown notes and false approval."""
    dev = development.get("queries")
    test = holdout.get("queries")
    judgments = qrels.get("judgments")
    if not isinstance(dev, list) or len(dev) != 16:
        raise ValueError("El set de desarrollo debe contener exactamente 16 consultas")
    if not isinstance(test, list) or len(test) != 8:
        raise ValueError("El holdout debe contener exactamente 8 consultas")
    if not isinstance(judgments, list) or len(judgments) != 24:
        raise ValueError("Deben existir exactamente 24 anotaciones qrels")

    rows = dev + test
    ids = [row.get("id") for row in rows]
    queries = [row.get("query") for row in rows]
    if any(not isinstance(q, str) or not q.strip() for q in queries):
        raise ValueError("Hay consultas vacías")
    if any(not isinstance(q, str) or not q.strip() for q in ids):
        raise ValueError("Hay IDs vacíos")
    if len(set(ids)) != 24 or len({q.casefold().strip() for q in queries}) != 24:
        raise ValueError("Hay consultas o IDs duplicados entre splits")
    for split, split_rows, prefix in [
        ("development", dev, "D"),
        ("holdout", test, "H"),
    ]:
        for row in split_rows:
            if row.get("split") != split or not row["id"].startswith(prefix):
                raise ValueError(f"Una consulta no respeta el split {split}")
            if not isinstance(row.get("category"), str) or not row["category"]:
                raise ValueError(f"Categoría ausente: {row['id']}")

    by_id = {}
    for judgment in judgments:
        qid = judgment.get("query_id")
        if qid in by_id:
            raise ValueError("Una misma consulta tiene qrels duplicadas")
        by_id[qid] = judgment
        relevant = judgment.get("relevant_notes")
        if not isinstance(relevant, list) or len(set(relevant)) != len(relevant):
            raise ValueError(f"Notas relevantes duplicadas o malformadas: {qid}")
        if not set(relevant).issubset(available_notes):
            raise ValueError(f"Qrel referencia notas desconocidas: {qid}")
        if any(not isinstance(item, str) or not item.endswith(".md") for item in relevant):
            raise ValueError(f"Qrel contiene rutas no Markdown: {qid}")
        if not isinstance(judgment.get("rationale"), str) or not judgment["rationale"].strip():
            raise ValueError(f"Falta justificación de relevancia: {qid}")
        status = judgment.get("review_status")
        if status not in ("proposed", "approved"):
            raise ValueError(f"Estado de anotación inválido: {qid}")
        if status == "approved" and (
            not judgment.get("reviewer") or not judgment.get("reviewed_at")
        ):
            raise ValueError(f"Una qrel aprobada debe identificar revisor y fecha: {qid}")

    if set(by_id) != set(ids):
        raise ValueError("Las qrels no coinciden exactamente con los IDs de las consultas")

    # The frozen historical four are imported by the runner, never trained on.
    multi = sum(len(q["relevant_notes"]) > 1 for q in judgments)
    missing = sum(len(q["relevant_notes"]) == 0 for q in judgments)
    if multi < 2 or missing < 2:
        raise ValueError("El benchmark debe incluir relevancia múltiple y preguntas sin respuesta")

    approved = sum(q["review_status"] == "approved" for q in judgments)
    return {
        "development_count": len(dev),
        "holdout_count": len(test),
        "new_queries_count": len(rows),
        "multiple_relevant_count": multi,
        "out_of_domain_count": missing,
        "approved_qrels_count": approved,
        "proposed_qrels_count": len(judgments) - approved,
        "qrels_fully_reviewed": approved == len(judgments),
        "all_query_ids": ids,
    }
