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

# The experiment records precisely these seven inputs. Allowing the report to
# supply an arbitrary subset would make the provenance check opt-in.
REQUIRED_SOURCE_FILES = frozenset({
    "evaluation/experiment_g4.py",
    "evaluation/metrics.py",
    "evaluation/qrels.json",
    "evaluation/development_queries.json",
    "evaluation/holdout_queries.json",
    "uv.lock",
    "src/mcp_vault_search/semantic.py",
})


def assert_source_provenance(
    declared: dict, commit_sha: str, project: Path = PROJECT
) -> None:
    """Reject partial manifests, dirty local sources, and non-committed evidence."""
    if not isinstance(declared, dict) or set(declared) != REQUIRED_SOURCE_FILES:
        raise AssertionError("Source-hash manifest must include the exact frozen G4 inputs")
    repository = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=project, text=True,
    ).strip())
    prefix = project.resolve().relative_to(repository.resolve()).as_posix()
    for name in sorted(REQUIRED_SOURCE_FILES):
        claimed = declared[name]
        working_bytes = (project / name).read_bytes()
        # git show returns the committed blob, not any modified working-tree bytes.
        object_name = f"{commit_sha}:{prefix}/{name}" if prefix != "." else f"{commit_sha}:{name}"
        try:
            committed_bytes = subprocess.check_output(
                ["git", "show", object_name], cwd=repository, stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            raise AssertionError(f"G4 input missing from recorded commit: {name}") from exc
        if (not isinstance(claimed, str)
                or hashlib.sha256(working_bytes).hexdigest() != claimed
                or hashlib.sha256(committed_bytes).hexdigest() != claimed):
            raise AssertionError(f"Source hash differs from working tree or commit: {name}")


def assert_annotation_attestation(metadata: dict, judgments: list[dict]) -> str:
    """Derive review state from all qrels, never trust a report's own label."""
    if not isinstance(judgments, list) or len(judgments) != 24:
        raise AssertionError("Expected exactly 24 actual qrel review records")
    for qrel in judgments:
        if not isinstance(qrel, dict) or qrel.get("review_status") not in ("proposed", "approved"):
            raise AssertionError("Invalid qrel review status")
        if qrel["review_status"] == "approved" and (
            not qrel.get("reviewer") or not qrel.get("reviewed_at")
        ):
            raise AssertionError("Approved qrel lacks reviewer identity or review date")
    approved = all(qrel["review_status"] == "approved" for qrel in judgments)
    actual_status = "human_reviewed" if approved else "provisional_unreviewed"
    if metadata.get("annotation_status") != actual_status:
        raise AssertionError("Claimed annotation status differs from actual qrels")
    return actual_status


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


def assert_frozen_corpus(metadata: dict, historical: dict) -> set[str]:
    """Check complete membership AND exact bytes of all 12 historical notes."""
    reference = historical.get("corpus_sha256")
    declared = metadata.get("corpus_sha256")
    if not isinstance(reference, dict) or len(reference) != 12 or declared != reference:
        raise AssertionError("Corpus manifest differs from frozen G2 benchmark")
    root = PROJECT / "examples" / "vault"
    present = {p.relative_to(root).as_posix() for p in root.rglob("*.md")}
    if present != set(reference):
        raise AssertionError("Working corpus note membership differs from historical manifest")
    for name, expected_digest in reference.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected_digest:
            raise AssertionError(f"Frozen corpus note changed: {name}")
    return set(reference)


def assert_frozen_rankings(rows: list[dict], notes: set[str]) -> None:
    """Both rankings must contain all and only original benchmark notes."""
    for row in rows:
        for key in ("baseline_ranking", "candidate_ranking"):
            ranking = row[key]
            if len(ranking) != len(notes) or len(set(ranking)) != len(notes) or set(ranking) != notes:
                raise AssertionError(f"Ranking {row['id']}/{key} has forged or missing frozen corpus notes")


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
    assert_source_provenance(md.get("source_sha256"), ref)
    historical = json.loads(
        (PROJECT / "evaluate_semantic_results_checkpoint_fixes.json").read_text(encoding="utf-8")
    )[0]["evaluation_metadata"]
    frozen_notes = assert_frozen_corpus(md, historical)
    assert_frozen_rankings(rows, frozen_notes)
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

    from evaluation.dataset import load_json, validate_dataset
    qrels = load_json(PROJECT / "evaluation" / "qrels.json")
    holdout = load_json(PROJECT / "evaluation" / "holdout_queries.json")
    validated = validate_dataset(
        {"queries": development}, holdout, qrels, frozen_notes,
    )
    status = assert_annotation_attestation(md, qrels["judgments"])
    if validated["qrels_fully_reviewed"] != (status == "human_reviewed"):
        raise AssertionError("Validated qrels disagree with review attestation")
    labels = {q["query_id"]: set(q["relevant_notes"]) for q in qrels["judgments"]}
    baseline_rows, other_rows = [], []
    for row in rows:
        qid = row["id"]
        rel = labels[qid]
        if row["relevant_count"] != len(rel):
            raise AssertionError("Reported relevant count does not match frozen qrels")
        a, b = row["baseline_ranking"], row["candidate_ranking"]
        if set(a) != frozen_notes or set(b) != frozen_notes:
            raise AssertionError("Rankings do not match the frozen corpus")
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
        "annotation_status": status,
        "holdout_evaluated": False,
        "independent_verification": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT / "evaluation" / "g4_performance_results.json")
    args = parser.parse_args()
    print(json.dumps(verify(args.output), indent=2))
