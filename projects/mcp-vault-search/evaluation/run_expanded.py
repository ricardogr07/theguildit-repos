#!/usr/bin/env python
"""G3 retrieval evaluation: 16 development queries and a sealed 8-query holdout.

Run development with explicit --allow-provisional until annotations are reviewed.
Holdout requires explicit --allow-holdout and approved human relevance judgments.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from evaluate_semantic import QUERIES
from evaluation.dataset import load_json, validate_dataset
from evaluation.metrics import score_query, summarize
from mcp_vault_search.retrieval_metrics import unique_note_ranking
from mcp_vault_search.semantic import MODEL_NAME, MODEL_REVISION, build_index, semantic_search
from mcp_vault_search.vault import markdown_files, vault_root
from run_g2_baseline import commit_sha, digest, load_reference


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def validate_legacy_queries(historical_json: dict) -> None:
    rows = historical_json.get("queries")
    if not isinstance(rows, list) or len(rows) != len(QUERIES):
        raise ValueError("Se modificó el conjunto histórico")
    for row, original in zip(rows, QUERIES, strict=True):
        if (row.get("query"), row.get("target"), row.get("distractor")) != (
            original["query"], original["target"], original["distractor"]
        ):
            raise ValueError("Se modificaron las etiquetas históricas")


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("development", "holdout"), default="development")
    parser.add_argument("--allow-provisional", action="store_true",
                        help="Use unreviewed qrels for exploratory development only")
    parser.add_argument("--allow-holdout", action="store_true",
                        help="Allow the one-time held-out evaluation only after qrels approval")
    parser.add_argument("--output", type=Path, default=HERE / "development_results.json")
    parser.add_argument("--metrics-output", type=Path, default=HERE / "retrieval_metrics.json")
    args = parser.parse_args()

    source_files = {
        name: HERE / name for name in (
            "historical_queries.json", "development_queries.json",
            "holdout_queries.json", "qrels.json",
        )
    }
    if args.output.resolve() == args.metrics_output.resolve():
        raise ValueError("Las rutas de resultados y métricas no pueden coincidir")
    if any(path.resolve() in {args.output.resolve(), args.metrics_output.resolve()}
           for path in source_files.values()):
        raise ValueError("No sobrescribas archivos de consultas o relevancias")

    development = load_json(source_files["development_queries.json"])
    holdout = load_json(source_files["holdout_queries.json"])
    qrels = load_json(source_files["qrels.json"])
    validate_legacy_queries(load_json(source_files["historical_queries.json"]))

    root = vault_root(str(PROJECT / "examples" / "vault"))
    corpus_paths = {
        path.relative_to(root).as_posix() for path in markdown_files(root)
    }
    summary = validate_dataset(development, holdout, qrels, corpus_paths)
    if args.split == "holdout":
        if not args.allow_holdout or args.allow_provisional:
            raise ValueError(
                "Holdout sellado: requiere --allow-holdout, sin --allow-provisional"
            )
        if not summary["qrels_fully_reviewed"]:
            raise ValueError(
                "Holdout bloqueado: se requiere revisión humana de todas las qrels"
            )
    elif not summary["qrels_fully_reviewed"] and not args.allow_provisional:
        raise ValueError(
            "Qrels preliminares: el modo de desarrollo requiere --allow-provisional"
        )

    previous = load_reference(PROJECT / "evaluate_semantic_results_checkpoint_fixes.json")
    expected = previous[0]["evaluation_metadata"]
    corpus_hashes = {
        path.relative_to(root).as_posix(): digest(path)
        for path in markdown_files(root)
    }
    if corpus_hashes != expected["corpus_sha256"] or len(corpus_hashes) != 12:
        raise ValueError("El corpus debe coincidir exactamente con las doce notas históricas")
    if (MODEL_NAME, MODEL_REVISION) != (expected["model_name"], expected["model_revision"]):
        raise ValueError("Modelo o revisión no corresponden al baseline G2")

    # Everything above runs before downloading the model. No silent holdout peeking.
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    chunks = build_index(root, embedder)
    rows = development["queries"] if args.split == "development" else holdout["queries"]
    labels = {row["query_id"]: row for row in qrels["judgments"]}
    results = []
    for spec in rows:
        hits = semantic_search(chunks, spec["query"], embedder, root, limit=50)
        ranked = unique_note_ranking(hits)
        if len(ranked) < min(10, len(corpus_paths)):
            raise RuntimeError("Posible truncamiento: no se observan 10 notas únicas")
        best = {}
        for hit in hits:
            best.setdefault(hit["path"], hit)
        judgment = labels[spec["id"]]
        metric = score_query(ranked, judgment["relevant_notes"])
        results.append({
            "id": spec["id"], "query": spec["query"],
            "category": spec["category"], "split": spec["split"],
            "relevant_notes": judgment["relevant_notes"],
            "review_status": judgment["review_status"],
            "metrics": metric,
            "ranked_notes": [
                {
                    "note": note, "rank": n,
                    "score": best[note]["score"],
                    "line_start": best[note]["line_start"],
                    "line_end": best[note]["line_end"],
                }
                for n, note in enumerate(ranked, 1)
            ],
            "top_10_notes": ranked[:10],
            "retrieved_chunks": len(hits),
            "chunk_limit_reached": len(hits) == 50,
        })
        print(
            f"{spec['id']}: relevant={len(judgment['relevant_notes'])}; "
            f"first={ranked[0] if ranked else 'none'}; "
            f"status={judgment['review_status']}"
        )

    metrics = summarize(results)
    metrics["annotation_status"] = (
        "human_reviewed" if summary["qrels_fully_reviewed"] else "provisional_unreviewed"
    )
    metrics["split"] = args.split
    metrics["not_a_release_gate_without_review"] = not summary["qrels_fully_reviewed"]

    metadata = {
        "git_commit": commit_sha(),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "device": "cpu",
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "packages": {
            name: version(name)
            for name in ("sentence-transformers", "transformers", "torch")
        },
        "source_sha256": {
            path.relative_to(PROJECT).as_posix(): digest(path)
            for path in [
                HERE / "run_expanded.py", HERE / "metrics.py",
                HERE / "dataset.py", PROJECT / "uv.lock",
                PROJECT / "src" / "mcp_vault_search" / "semantic.py",
                *source_files.values(),
            ]
        },
        "corpus_sha256": corpus_hashes,
        "dataset_validation": summary,
        "chunk_count": len(chunks),
        "chunk_limit": 50,
        "historical_queries_preserved": True,
        "holdout_accessed": args.split == "holdout",
        "human_review_completed": summary["qrels_fully_reviewed"],
        "method": "rank unique notes by highest first matching chunk (same as G2)",
        "ndcg_at_5": None,
        "ndcg_reason": "No graded human relevance labels",
    }
    report = {"metadata": metadata, "metrics": metrics, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.metrics_output.write_text(
        json.dumps({"metadata": metadata, "metrics": metrics}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2))
    print(f"Saved results: {args.output}; metrics: {args.metrics_output}")


if __name__ == "__main__":
    run()
