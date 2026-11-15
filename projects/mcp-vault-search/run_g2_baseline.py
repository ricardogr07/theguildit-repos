#!/usr/bin/env python
"""G2: reproduce the four original semantic retrieval queries with the real CPU model.

Does not change the legacy benchmark, corpus, semantic algorithm or qrels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from evaluate_semantic import QUERIES
from mcp_vault_search.retrieval_metrics import recall_at_k, reciprocal_rank_at_k, unique_note_ranking
from mcp_vault_search.semantic import MODEL_NAME, MODEL_REVISION, build_index, semantic_search
from mcp_vault_search.vault import markdown_files, vault_root


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commit_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parent, capture_output=True, text=True, check=True,
    )
    sha = result.stdout.strip()
    if len(sha) != 40:
        raise RuntimeError("No se pudo identificar el commit del benchmark")
    return sha


def load_reference(path: Path) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != len(QUERIES):
        raise ValueError("El reporte histórico debe contener exactamente cuatro consultas")
    for row, spec in zip(records, QUERIES, strict=True):
        if (
            row["query"] != spec["query"]
            or row["expected_target"] != spec["target"]
            or row["designated_distractor"] != spec["distractor"]
        ):
            raise ValueError("Las consultas, targets o distractores históricos no coinciden")
    return records


def independently_rank(raw_hits: list[dict]) -> list[str]:
    """Independent first-occurrence ranking, without the retrieval_metrics helper."""
    result: list[str] = []
    for hit in raw_hits:
        name = hit["path"]
        if name not in result:
            result.append(name)
    return result


def analyze_hits(hits: list[dict], spec: dict, expected_documents: int) -> dict:
    """Keep legacy PASS semantics, but report scored note-level top 10."""
    if len(hits) > 50:
        raise ValueError("La consulta devolvió más de 50 fragmentos")
    ranking = unique_note_ranking(hits)
    independent = independently_rank(hits)
    if ranking != independent:
        raise AssertionError("La deduplicación no coincide con el cálculo independiente")
    if len(ranking) < min(10, expected_documents):
        raise RuntimeError(
            "No se recuperaron suficientes notas únicas para top 10; "
            "posible truncamiento de los primeros 50 fragmentos"
        )

    first_hits: dict[str, dict] = {}
    for hit in hits:
        first_hits.setdefault(hit["path"], hit)

    ranks = {name: n for n, name in enumerate(ranking, 1)}
    target = spec["target"]
    distractor = spec["distractor"]
    target_rank = ranks.get(target)
    distractor_rank = ranks.get(distractor)

    recall3 = recall_at_k(ranking, [target], 3)
    recall5 = recall_at_k(ranking, [target], 5)
    rr10 = reciprocal_rank_at_k(ranking, [target], 10)
    independent_rank = next((n for n, name in enumerate(independent, 1) if name == target), None)
    expected = (
        float(independent_rank is not None and independent_rank <= 3),
        float(independent_rank is not None and independent_rank <= 5),
        1 / independent_rank if independent_rank is not None and independent_rank <= 10 else 0.0,
    )
    if (recall3, recall5, rr10) != expected:
        raise AssertionError("Recall/MRR no concuerda con las posiciones independientes")

    note_rankings = [
        {
            "note": name,
            "rank": number,
            "score": first_hits[name]["score"],
            "line_start": first_hits[name]["line_start"],
            "line_end": first_hits[name]["line_end"],
        }
        for number, name in enumerate(ranking, 1)
    ]
    return {
        "query": spec["query"],
        "expected_target": target,
        "designated_distractor": distractor,
        "target_position": target_rank,
        "distractor_position": distractor_rank,
        "pass": (
            target_rank is not None and target_rank <= 3
            and (distractor_rank is None or target_rank < distractor_rank)
        ),
        "note_rankings": note_rankings,
        "top_10_notes": note_rankings[:10],
        "full_results": hits,
        "retrieved_chunks": len(hits),
        "hit_limit_reached": len(hits) == 50,
        "single_target_recall_at_3": recall3,
        "single_target_recall_at_5": recall5,
        "single_target_reciprocal_rank_at_10": rr10,
        "independent_metrics_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("baseline_real.json"))
    parser.add_argument("--summary", type=Path, default=Path("baseline_summary.json"))
    parser.add_argument(
        "--historical", type=Path,
        default=Path("evaluate_semantic_results_checkpoint_fixes.json"),
    )
    args = parser.parse_args()
    if len({p.resolve() for p in (args.output, args.summary, args.historical)}) != 3:
        raise ValueError("Los archivos de salida deben ser distintos del histórico")

    historical = load_reference(args.historical)
    previous = historical[0]["evaluation_metadata"]
    root = vault_root("examples/vault")
    corpus = {
        path.relative_to(root).as_posix(): digest(path)
        for path in markdown_files(root)
    }
    if corpus != previous["corpus_sha256"] or len(corpus) != 12:
        raise ValueError("El corpus sintético ya no coincide con las 12 notas históricas")
    if MODEL_NAME != previous["model_name"] or MODEL_REVISION != previous["model_revision"]:
        raise ValueError("El nombre o revisión del modelo difieren del histórico")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    index = build_index(root, model)
    if {chunk.path for chunk in index} != set(corpus):
        raise ValueError("El índice no contiene exactamente las 12 notas sintéticas")
    token_counts = [len(model.tokenizer.encode(chunk.text)) for chunk in index]
    if not token_counts or max(token_counts) > model.max_seq_length:
        raise ValueError("Los fragmentos exceden el límite real de tokens del modelo")

    hashes = {
        name: digest(Path(name))
        for name in (
            "src/mcp_vault_search/semantic.py",
            "src/mcp_vault_search/server.py",
            "src/mcp_vault_search/retrieval_metrics.py",
            "evaluate_semantic.py",
            "run_g2_baseline.py",
            "uv.lock",
        )
    }
    metadata = {
        "git_commit": commit_sha(),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "os": platform.platform(),
        "cpu_count": os.cpu_count(),
        "processor": platform.processor(),
        "device": "cpu",
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "package_versions": {
            name: version(name) for name in
            ("sentence-transformers", "transformers", "torch", "numpy")
        },
        "corpus_sha256": corpus,
        "code_and_lock_sha256": hashes,
        "historical_file_sha256": digest(args.historical),
        "historical_code_hashes_match": {
            name: previous_hash == hashes[name]
            for name, previous_hash in previous["code_sha256"].items()
        },
        "chunk_count": len(index),
        "max_chunk_tokens": max(token_counts),
        "model_token_limit": model.max_seq_length,
        "retrieval_limit_chunks": 50,
        "ranking_unit": "unique note, first matching chunk ranked by score",
        "invocation": [sys.executable, Path(__file__).name, *sys.argv[1:]],
    }

    results = []
    for spec in QUERIES:
        hits = semantic_search(index, spec["query"], model, root, limit=50)
        result = analyze_hits(hits, spec, len(corpus))
        results.append(result)
        print(
            f"{'PASS' if result['pass'] else 'FAIL'}: {spec['target']} "
            f"rank={result['target_position']} "
            f"distractor={result['distractor_position']} "
            f"unique_notes={len(result['note_rankings'])}"
        )

    comparison = [
        {
            "query": old["query"],
            "historical_target_rank": old["target_position"],
            "current_target_rank": now["target_position"],
            "historical_distractor_rank": old["distractor_position"],
            "current_distractor_rank": now["distractor_position"],
            "historical_pass": old["pass"],
            "current_pass": now["pass"],
            "rank_changed": old["target_position"] != now["target_position"],
        }
        for old, now in zip(historical, results, strict=True)
    ]
    summary = {
        "historical_query_count": len(QUERIES),
        "historical_original_pass_count": sum(old["pass"] for old in historical),
        "current_legacy_pass_count": sum(result["pass"] for result in results),
        "single_target_recall_at_3": sum(r["single_target_recall_at_3"] for r in results) / len(results),
        "single_target_recall_at_5": sum(r["single_target_recall_at_5"] for r in results) / len(results),
        "single_target_mrr_at_10": sum(r["single_target_reciprocal_rank_at_10"] for r in results) / len(results),
        "comparison": comparison,
        "all_independent_checks_passed": all(r["independent_metrics_verified"] for r in results),
        "corpus_matches_historical": True,
        "model_matches_historical": True,
        "model_code_hashes_differ_from_historical": [
            name for name, matches in metadata["historical_code_hashes_match"].items()
            if not matches
        ],
        "reproduced_historical_ranks": all(
            not item["rank_changed"] and item["historical_distractor_rank"] == item["current_distractor_rank"]
            for item in comparison
        ),
        "note": "Los números son para una sola nota relevante por consulta; G3 revisará la relevancia múltiple.",
    }
    args.output.write_text(
        json.dumps({"metadata": metadata, "summary": summary, "results": results}, ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8",
    )
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {key: summary[key] for key in (
            "historical_original_pass_count", "current_legacy_pass_count",
            "single_target_recall_at_3", "single_target_recall_at_5",
            "single_target_mrr_at_10", "reproduced_historical_ranks",
        )}, indent=2,
    ))
    print(f"Results: {args.output}; summary: {args.summary}")


if __name__ == "__main__":
    main()
