#!/usr/bin/env python
"""Independent audit of G4 experiment data, provenance and numerical claims."""

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path

from evaluation.metrics import score_query, summarize
from evaluation.experiment_g4 import nearest_percentile


PROJECT = Path(__file__).resolve().parents[1]


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-9)


def assert_development_split(rows: list[dict], queries: list[dict]) -> None:
    """Check actual IDs, query texts and categories, not just a length and a flag."""
    if len(rows) != len(queries):
        raise AssertionError("Development split size changed")
    for actual, expected in zip(rows, queries, strict=True):
        if (
            actual.get("id") != expected["id"]
            or actual.get("query") != expected["query"]
            or actual.get("category") != expected["category"]
            or actual.get("split") != "development"
        ):
            raise AssertionError("Benchmark includes non-development query or altered ID")


def assert_candidate_selection(rows: list[dict], comparison: dict) -> None:
    """Recompute A/B decisions and per-query regressions independently."""
    improvements = [
        row["id"] for row in rows
        if row["relevant_count"] and row["candidate_metrics"]["recall_at_3"] > row["baseline_metrics"]["recall_at_3"]
    ]
    regressions = [
        row["id"] for row in rows
        if row["relevant_count"] and row["candidate_metrics"]["recall_at_3"] < row["baseline_metrics"]["recall_at_3"]
    ]
    if (
        comparison["recall_3_improvement_query_ids"] != improvements
        or comparison["recall_3_regression_query_ids"] != regressions
    ):
        raise AssertionError("Candidate improvement/regression lists do not match per-query metrics")
    conditions = comparison["pre_registered_candidate_qualification"]
    if (
        conditions["min_mean_recall_at_3_gain"] != 0.05
        or conditions["min_mrr_at_10_delta"] != -0.01
        or conditions["no_recall_at_3_query_regressions"] is not True
    ):
        raise AssertionError("Pre-registered qualification thresholds were changed")
    delta = comparison["delta_b_minus_a"]
    qualifies = (
        delta["mean_recall_at_3"] >= 0.05
        and delta["mrr_at_10"] >= -0.01
        and not regressions
    )
    if conditions["passed_on_provisional_development"] is not qualifies:
        raise AssertionError("Qualification decision conflicts with pre-registered thresholds")
    if conditions["may_merge_to_production"] is not False:
        raise AssertionError("Unreviewed candidate must not be automatically promoted")


def verify(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    md = report["metadata"]
    p = report["performance"]
    comparison = report["comparison"]
    rows = report["per_query"]
    ref = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=PROJECT).strip()
    if md["code_sha"] != ref:
        raise AssertionError("Benchmark commit differs from checkout")
    if md["holdout_evaluated"] or not md["used_development_only"]:
        raise AssertionError("Holdout data was used in a development experiment")
    for name, expected in md["source_sha256"].items():
        if hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() != expected:
            raise AssertionError(f"Source file changed since benchmark: {name}")
    if len(rows) != 16 or len({r["id"] for r in rows}) != 16:
        raise AssertionError("Expected exactly 16 distinct development queries")
    development = json.loads(
        (PROJECT / "evaluation" / "development_queries.json").read_text(encoding="utf-8")
    )["queries"]
    assert_development_split(rows, development)
    if p["warm_query_count"] < 30 or len(p["warm_query_samples_ms"]) != p["warm_query_count"]:
        raise AssertionError("Too few or missing warm latency samples")
    timings = p["warm_query_samples_ms"]
    if any(not math.isfinite(t) or t <= 0 for t in timings):
        raise AssertionError("Nonpositive or nonfinite latency")
    for stat, actual in (
        ("warm_query_p50_ms", nearest_percentile(timings, .50)),
        ("warm_query_p95_ms", nearest_percentile(timings, .95)),
        ("warm_query_mean_ms", statistics.mean(timings)),
    ):
        if not close(p[stat], actual):
            raise AssertionError(f"Incorrect percentile: {stat}")
    if [s["note_count"] for s in p["scale"]] != [12, 100, 1000]:
        raise AssertionError("Scale must include 12/100/1000 notes")
    if any(s["index_build_s"] <= 0 or s["process_peak_rss_mib"] <= 0 for s in p["scale"]):
        raise AssertionError("Invalid performance measurement")

    labels = {
        q["query_id"]: set(q["relevant_notes"])
        for q in json.loads((PROJECT / "evaluation" / "qrels.json").read_text(encoding="utf-8"))["judgments"]
    }
    baseline_rows, other_rows = [], []
    for row in rows:
        qid = row["id"]
        rel = labels[qid]
        if row["relevant_count"] != len(rel):
            raise AssertionError("Reported relevant count does not match frozen qrels")
        a, b = row["baseline_ranking"], row["candidate_ranking"]
        if len(a) != 12 or len(b) != 12 or set(a) != set(b) or len(set(a)) != 12:
            raise AssertionError("Rankings must include the same 12 notes")
        for key, rank in (("baseline_metrics", a), ("candidate_metrics", b)):
            actual = score_query(rank, rel)
            claimed = row[key]
            for metric in ("recall_at_3", "recall_at_5", "precision_at_3", "mrr_at_10"):
                if actual[metric] is None:
                    if claimed[metric] is not None:
                        raise AssertionError("OOD has non-null retrieval metric")
                elif not close(actual[metric], claimed[metric]):
                    raise AssertionError(f"Wrong query metric {qid}/{key}/{metric}")
        baseline_rows.append({"metrics": score_query(a, rel)})
        other_rows.append({"metrics": score_query(b, rel)})
    base, alt = summarize(baseline_rows), summarize(other_rows)
    for name in ("mean_recall_at_3", "mean_recall_at_5", "mean_precision_at_3", "mrr_at_10"):
        if not close(base[name], comparison["baseline"][name]):
            raise AssertionError(f"Baseline aggregate inconsistent: {name}")
        if not close(alt[name], comparison["alternative"][name]):
            raise AssertionError(f"Candidate aggregate inconsistent: {name}")
        if not close(alt[name] - base[name], comparison["delta_b_minus_a"][name]):
            raise AssertionError(f"Reported delta inconsistent: {name}")
    assert_candidate_selection(rows, comparison)
    return {
        "code_sha": ref,
        "p50_ms": p["warm_query_p50_ms"],
        "p95_ms": p["warm_query_p95_ms"],
        "peak_rss_mib": p["process_peak_rss_mib"],
        "delta_recall_at_3": comparison["delta_b_minus_a"]["mean_recall_at_3"],
        "annotation_status": md["annotation_status"],
        "holdout_evaluated": False,
        "independent_verification": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT / "evaluation" / "g4_performance_results.json")
    args = parser.parse_args()
    print(json.dumps(verify(args.output), indent=2))
