#!/usr/bin/env python
"""Independently verify G3 result JSON without loading an embedding model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from evaluation.dataset import load_json, validate_dataset


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(left, right) -> bool:
    return math.isclose(left, right, rel_tol=0, abs_tol=1e-12)


G3_REQUIRED_SOURCES = {
    "evaluation/run_expanded.py",
    "evaluation/metrics.py",
    "evaluation/dataset.py",
    "evaluation/historical_queries.json",
    "evaluation/development_queries.json",
    "evaluation/holdout_queries.json",
    "evaluation/qrels.json",
    "src/mcp_vault_search/semantic.py",
    "uv.lock",
}


def assert_approval_attestation(metadata: dict, aggregate: dict, validated: dict, split: str) -> None:
    """No generated JSON can proclaim reviewed labels when the qrels disagree."""
    reviewed = validated["qrels_fully_reviewed"]
    if metadata.get("dataset_validation") != validated:
        raise AssertionError("Dataset validation metadata conflicts with actual qrels")
    if metadata.get("human_review_completed") is not reviewed:
        raise AssertionError("Report human-review flag conflicts with actual qrels")
    expected_status = "human_reviewed" if reviewed else "provisional_unreviewed"
    if aggregate.get("annotation_status") != expected_status:
        raise AssertionError("Report approval status conflicts with actual qrels")
    if aggregate.get("not_a_release_gate_without_review") is not (not reviewed):
        raise AssertionError("Release-approval flag conflicts with actual qrels")
    if split == "holdout" and not reviewed:
        raise AssertionError("Unreviewed holdout report cannot pass independent verification")


def verify(output: Path, expected_split: str = "development") -> dict:
    report = json.loads(output.read_text(encoding="utf-8"))
    metadata, aggregate, rows = report["metadata"], report["metrics"], report["results"]
    actual_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
    ).strip()
    if actual_sha != metadata["git_commit"]:
        raise AssertionError("Se verificó un SHA distinto del usado en el benchmark")
    if set(metadata["source_sha256"]) != G3_REQUIRED_SOURCES:
        raise AssertionError("Incomplete or unexpected G3 source-hash manifest")
    for name, hash_value in metadata["source_sha256"].items():
        if digest(PROJECT / name) != hash_value:
            raise AssertionError(f"Archivo de código/dataset modificado: {name}")
        blob = subprocess.check_output(
            ["git", "show", "HEAD:projects/mcp-vault-search/" + name],
            cwd=PROJECT,
        )
        if hashlib.sha256(blob).hexdigest() != hash_value:
            raise AssertionError(f"Source file hash does not match committed Git blob: {name}")
    historical = json.loads(
        (PROJECT / "evaluate_semantic_results_checkpoint_fixes.json").read_text(encoding="utf-8")
    )[0]["evaluation_metadata"]
    if metadata["corpus_sha256"] != historical["corpus_sha256"]:
        raise AssertionError("Corpus manifest differs from frozen historical notes")
    if (metadata["model_name"], metadata["model_revision"]) != (
        historical["model_name"], historical["model_revision"]
    ):
        raise AssertionError("Embedding model or revision changed")
    for name, hash_value in metadata["corpus_sha256"].items():
        if digest(PROJECT / "examples" / "vault" / name) != hash_value:
            raise AssertionError(f"Archivo de corpus modificado: {name}")
    if metadata["holdout_accessed"] != (expected_split == "holdout"):
        raise AssertionError("Bandera holdout inconsistente")
    if aggregate["split"] != expected_split:
        raise AssertionError("Split incorrecto en resultado")

    query_file = HERE / (
        "development_queries.json" if expected_split == "development"
        else "holdout_queries.json"
    )
    queries = json.loads(query_file.read_text(encoding="utf-8"))["queries"]
    development = load_json(HERE / "development_queries.json")
    holdout = load_json(HERE / "holdout_queries.json")
    full_qrels = load_json(HERE / "qrels.json")
    available = set(metadata["corpus_sha256"])
    validated = validate_dataset(development, holdout, full_qrels, available)
    assert_approval_attestation(metadata, aggregate, validated, expected_split)
    qrels = {item["query_id"]: item for item in full_qrels["judgments"]}
    if [row["id"] for row in rows] != [row["id"] for row in queries]:
        raise AssertionError("Las consultas no coinciden con el split congelado")
    if len(rows) != (16 if expected_split == "development" else 8):
        raise AssertionError("Número de consultas incorrecto")
    domain, ood = [], []
    for row, query in zip(rows, queries, strict=True):
        if row["query"] != query["query"] or row["split"] != expected_split:
            raise AssertionError("La consulta o el split fue modificado")
        judgment = qrels[row["id"]]
        relevant = set(judgment["relevant_notes"])
        if set(row["relevant_notes"]) != relevant:
            raise AssertionError("Las qrels difieren del dataset")
        if row["review_status"] != judgment["review_status"]:
            raise AssertionError("Estado de revisión de qrel inconsistente")
        ranked_rows = row["ranked_notes"]
        ranked = [item["note"] for item in ranked_rows]
        if len(ranked) != len(set(ranked)):
            raise AssertionError("Ranking contiene documentos duplicados")
        if set(ranked) != available:
            raise AssertionError("Ranking contains notes outside the frozen corpus or is incomplete")
        if len(ranked) < 10 or row["top_10_notes"] != ranked[:10]:
            raise AssertionError("El top-10 es incompleto o incorrecto")
        for position, result in enumerate(ranked_rows, 1):
            if result["rank"] != position or not math.isfinite(result["score"]):
                raise AssertionError("Posiciones o puntuaciones corruptas")
        if row["retrieved_chunks"] < len(ranked):
            raise AssertionError("Más notas que fragmentos recuperados")
        if row["chunk_limit_reached"]:
            raise AssertionError("G3 no permite reportar truncamientos sin explicación")
        metric = row["metrics"]
        if not relevant:
            if not metric["is_out_of_domain"] or metric["relevant_count"] != 0:
                raise AssertionError("Consulta sin respuesta mal clasificada")
            if any(metric[name] is not None for name in (
                "recall_at_3", "recall_at_5", "precision_at_3", "mrr_at_10"
            )):
                raise AssertionError("No calcular Recall/MRR sobre qrels vacías")
            if metric["abstained"] != (len(ranked) == 0):
                raise AssertionError("Abstención mal calculada")
            if metric["forced_hit"] != (len(ranked) > 0):
                raise AssertionError("Hit forzado mal calculado")
            ood.append(metric)
        else:
            hit3 = sum(note in relevant for note in ranked[:3])
            hit5 = sum(note in relevant for note in ranked[:5])
            first = next((n for n, note in enumerate(ranked[:10], 1) if note in relevant), None)
            expected = {
                "recall_at_3": hit3 / len(relevant),
                "recall_at_5": hit5 / len(relevant),
                "precision_at_3": hit3 / 3,
                "mrr_at_10": 1 / first if first else 0.0,
            }
            for name, value in expected.items():
                if metric[name] is None or not close(metric[name], value):
                    raise AssertionError(f"Fórmula mal calculada: {name}")
            if metric["is_out_of_domain"] or metric["relevant_count"] != len(relevant):
                raise AssertionError("Consulta relevante mal clasificada")
            domain.append(expected)

    if not domain:
        raise AssertionError("Sin consultas evaluables")
    expected_macro = {
        "query_count": len(rows),
        "in_domain_query_count": len(domain),
        "out_of_domain_query_count": len(ood),
        "mean_recall_at_3": sum(d["recall_at_3"] for d in domain) / len(domain),
        "mean_recall_at_5": sum(d["recall_at_5"] for d in domain) / len(domain),
        "mean_precision_at_3": sum(d["precision_at_3"] for d in domain) / len(domain),
        "mrr_at_10": sum(d["mrr_at_10"] for d in domain) / len(domain),
        "out_of_domain_abstention_rate": (
            sum(d["abstained"] for d in ood) / len(ood) if ood else None
        ),
        "out_of_domain_forced_hit_rate": (
            sum(d["forced_hit"] for d in ood) / len(ood) if ood else None
        ),
    }
    for name, val in expected_macro.items():
        observed = aggregate[name]
        if isinstance(val, float):
            if observed is None or not close(observed, val):
                raise AssertionError(f"Métrica agregada incorrecta: {name}")
        elif observed != val:
            raise AssertionError(f"Conteo agregado incorrecto: {name}")
    return expected_macro


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "development_results.json")
    parser.add_argument("--split", choices=("development", "holdout"), default="development")
    args = parser.parse_args()
    result = verify(args.output, args.split)
    print("G3 independent verification: PASS")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
