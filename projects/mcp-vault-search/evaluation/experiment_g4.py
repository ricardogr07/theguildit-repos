#!/usr/bin/env python
"""G4: measure retrieval costs and evaluate a preregistered ranking alternative.

Evaluation only. No production code changes, no tuning on the reserved holdout.
Synthetic scaling replicates the twelve example notes; not a quality benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
try:
    import resource
except ImportError:  # Windows has no resource module; performance job runs on Linux.
    resource = None
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from evaluation.dataset import load_json, validate_dataset
from evaluation.metrics import score_query, summarize
from evaluation.run_expanded import HERE, PROJECT, validate_legacy_queries
from mcp_vault_search.retrieval_metrics import unique_note_ranking
from mcp_vault_search.semantic import MODEL_NAME, MODEL_REVISION, build_index, semantic_search
from mcp_vault_search.vault import markdown_files, vault_root
from run_g2_baseline import commit_sha, digest, load_reference


def nearest_percentile(values: list[float], quantile: float) -> float:
    """Linear interpolation between nearest values, not a charting convenience."""
    if not values or not 0 <= quantile <= 1:
        raise ValueError("Percentile inputs invalid")
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def mean_of_best_two(raw_hits: list[dict]) -> list[str]:
    """Alternative B: mean of a document's two best chunk scores (or one, if only one)."""
    by_note: dict[str, list[float]] = defaultdict(list)
    for hit in raw_hits:
        score = float(hit["score"])
        if not math.isfinite(score):
            raise ValueError("Non-finite similarity score")
        by_note[hit["path"]].append(score)
    # Stable tie-breaker using relative path, not input order.
    scores = {
        name: statistics.mean(sorted(values, reverse=True)[:2])
        for name, values in by_note.items()
    }
    return sorted(scores, key=lambda name: (-scores[name], name))


def compare_results(rows: list[dict]) -> dict:
    """All relevance metrics computed over identical development qrels and chunk hits."""
    original = [{"metrics": row["baseline_metrics"]} for row in rows]
    candidate = [{"metrics": row["candidate_metrics"]} for row in rows]
    baseline = summarize(original)
    alternative = summarize(candidate)
    keys = ("mean_recall_at_3", "mean_recall_at_5", "mean_precision_at_3", "mrr_at_10")
    deltas = {key: alternative[key] - baseline[key] for key in keys}
    improvements = [
        row["id"] for row in rows
        if row["relevant_count"] and row["candidate_metrics"]["recall_at_3"] > row["baseline_metrics"]["recall_at_3"]
    ]
    regressions = [
        row["id"] for row in rows
        if row["relevant_count"] and row["candidate_metrics"]["recall_at_3"] < row["baseline_metrics"]["recall_at_3"]
    ]
    # Pre-registered decision criterion; no changes after observing the results.
    qualifies = (
        deltas["mean_recall_at_3"] >= 0.05
        and deltas["mrr_at_10"] >= -0.01
        and not regressions
    )
    return {
        "strategy_a": "highest individual chunk score per note (production baseline)",
        "strategy_b": "mean of two highest chunk scores per note, one if only one chunk",
        "baseline": baseline,
        "alternative": alternative,
        "delta_b_minus_a": deltas,
        "recall_3_improvement_query_ids": improvements,
        "recall_3_regression_query_ids": regressions,
        "pre_registered_candidate_qualification": {
            "min_mean_recall_at_3_gain": 0.05,
            "min_mrr_at_10_delta": -0.01,
            "no_recall_at_3_query_regressions": True,
            "passed_on_provisional_development": qualifies,
            "may_merge_to_production": False,
            "reason": "Provisional unreviewed qrels and untouched holdout. G4 is exploratory; no production ranking change.",
        },
    }


def synthetic_scale(notes: list[Path], root: Path, count: int) -> None:
    """Generate deterministic UTF-8 Markdown copies for capacity testing only."""
    if count <= 0:
        raise ValueError("Scaling requires a positive count")
    root.mkdir(parents=True, exist_ok=True)
    original = [note.read_text(encoding="utf-8") for note in notes]
    if not original:
        raise ValueError("Cannot scale an empty source corpus")
    for idx in range(count):
        note = root / f"synthetic-note-{idx:04d}.md"
        note.write_text(original[idx % len(original)], encoding="utf-8")


def rss_mib() -> float:
    # Linux ru_maxrss reports KiB. This is process-level peak including PyTorch native allocations.
    if resource is None:
        raise RuntimeError("El benchmark RSS requiere Linux/POSIX")
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def measure():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "g4_performance_results.json")
    parser.add_argument("--warm-repetitions", type=int, default=32)
    parser.add_argument("--scale-counts", type=int, nargs="+", default=[100, 1000])
    args = parser.parse_args()
    if args.warm_repetitions < 30:
        raise ValueError("At least 30 warm query measurements are required")
    if args.scale_counts != sorted(set(args.scale_counts)) or any(s < 12 or s > 1000 for s in args.scale_counts):
        raise ValueError("Expected sorted unique scale sizes in [12,1000]")

    corpus_root = vault_root(str(PROJECT / "examples" / "vault"))
    historical = load_reference(PROJECT / "evaluate_semantic_results_checkpoint_fixes.json")
    expected_metadata = historical[0]["evaluation_metadata"]
    actual_hashes = {p.relative_to(corpus_root).as_posix(): digest(p) for p in markdown_files(corpus_root)}
    if actual_hashes != expected_metadata["corpus_sha256"] or len(actual_hashes) != 12:
        raise ValueError("Synthetic corpus differs from G2 baseline")
    if (MODEL_NAME, MODEL_REVISION) != (
        expected_metadata["model_name"], expected_metadata["model_revision"]
    ):
        raise ValueError("Model/revision differs from G2")
    dev = load_json(HERE / "development_queries.json")
    holdout = load_json(HERE / "holdout_queries.json")
    qrels = load_json(HERE / "qrels.json")
    validate_legacy_queries(load_json(HERE / "historical_queries.json"))
    validation = validate_dataset(dev, holdout, qrels, set(actual_hashes))
    if validation["qrels_fully_reviewed"]:
        print("Annotations reviewed; G4 nevertheless evaluates DEVELOPMENT only.")
    else:
        print("WARNING: All reported quality metrics are PROVISIONAL; independent qrel review missing.")

    from sentence_transformers import SentenceTransformer
    t0 = time.perf_counter()
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    model_load_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    chunks = build_index(corpus_root, model)
    baseline_index_s = time.perf_counter() - t1
    labels = {j["query_id"]: j["relevant_notes"] for j in qrels["judgments"]}
    raw = {}
    rows = []
    for spec in dev["queries"]:
        hits = semantic_search(chunks, spec["query"], model, corpus_root, limit=50)
        if len(unique_note_ranking(hits)) != 12:
            raise RuntimeError("Insufficient unique notes: possible chunk truncation")
        baseline_rank = unique_note_ranking(hits)
        candidate_rank = mean_of_best_two(hits)
        if set(baseline_rank) != set(candidate_rank):
            raise AssertionError("Candidate and baseline evaluate different notes")
        qid = spec["id"]
        raw[qid] = hits
        rows.append({
            "id": qid,
            "category": spec["category"],
            "relevant_count": len(labels[qid]),
            "baseline_ranking": baseline_rank,
            "candidate_ranking": candidate_rank,
            "baseline_metrics": score_query(baseline_rank, labels[qid]),
            "candidate_metrics": score_query(candidate_rank, labels[qid]),
            "rank_changed": baseline_rank != candidate_rank,
        })
    comparison = compare_results(rows)

    # Warm up model inference, then measure >=30 repeat queries, without holdout.
    for spec in dev["queries"]:
        semantic_search(chunks, spec["query"], model, corpus_root, limit=50)
    warm_ms = []
    for n in range(args.warm_repetitions):
        query = dev["queries"][n % len(dev["queries"])]["query"]
        start = time.perf_counter()
        semantic_search(chunks, query, model, corpus_root, limit=50)
        warm_ms.append((time.perf_counter() - start) * 1000)

    scaled = [{"note_count": 12, "chunk_count": len(chunks), "index_build_s": baseline_index_s,
               "process_peak_rss_mib": rss_mib()}]
    notes = list(markdown_files(corpus_root))
    for count in args.scale_counts:
        with tempfile.TemporaryDirectory(prefix="mcp-vault-g4-") as tmp:
            synthetic_scale(notes, Path(tmp), count)
            start = time.perf_counter()
            index = build_index(Path(tmp), model)
            build_s = time.perf_counter() - start
            scaled.append({
                "note_count": count,
                "chunk_count": len(index),
                "index_build_s": build_s,
                "process_peak_rss_mib": rss_mib(),
                "memory_kind": "process peak high-water mark, NOT incremental per-size memory",
            })
            if len({chunk.path for chunk in index}) != count:
                raise AssertionError("Scaling lost or duplicated notes")
        print(f"Indexed {count} synthetic notes in {build_s:.2f}s")

    meta = {
        "code_sha": commit_sha(),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "platform": platform.platform(), "processor": platform.processor(),
        "cpu_count": os.cpu_count(), "python": platform.python_version(),
        "device": "cpu", "model_name": MODEL_NAME, "model_revision": MODEL_REVISION,
        "packages": {name: version(name) for name in ("sentence-transformers", "transformers", "torch")},
        "annotation_status": "human_reviewed" if validation["qrels_fully_reviewed"] else "provisional_unreviewed",
        "used_development_only": True, "holdout_evaluated": False,
        "corpus_sha256": actual_hashes,
        "source_sha256": {
            str(path.relative_to(PROJECT)): digest(path)
            for path in [
                HERE / "experiment_g4.py", HERE / "metrics.py", HERE / "qrels.json",
                HERE / "development_queries.json", HERE / "holdout_queries.json",
                PROJECT / "uv.lock", PROJECT / "src/mcp_vault_search/semantic.py",
            ]
        },
    }
    performance = {
        "model_load_seconds": model_load_s,
        "warmup_queries": len(dev["queries"]),
        "warm_query_samples_ms": warm_ms,
        "warm_query_count": len(warm_ms),
        "warm_query_p50_ms": nearest_percentile(warm_ms, 0.50),
        "warm_query_p95_ms": nearest_percentile(warm_ms, 0.95),
        "warm_query_mean_ms": statistics.mean(warm_ms),
        "scale": scaled,
        "process_peak_rss_mib": rss_mib(),
        "native_memory_note": "Linux ru_maxrss includes native allocations; values are high-water marks and do not indicate incremental cost.",
        "cold_load_note": "Model load time may include cache/download; do not compare to a prewarmed offline model.",
        "scaling_caveat": "Repeated synthetic notes are used ONLY for indexing capacity and memory, not retrieval quality.",
    }
    report = {"metadata": meta, "performance": performance, "comparison": comparison, "per_query": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "p50_ms": performance["warm_query_p50_ms"],
        "p95_ms": performance["warm_query_p95_ms"],
        "peak_rss_mib": performance["process_peak_rss_mib"],
        "scale": scaled,
        "quality_deltas": comparison["delta_b_minus_a"],
        "candidate_qualifies_on_provisional_dev": comparison["pre_registered_candidate_qualification"]["passed_on_provisional_development"],
        "holdout_evaluated": False,
    }, indent=2))
    print(f"Saved experimental evidence to {args.output}")


if __name__ == "__main__":
    measure()
