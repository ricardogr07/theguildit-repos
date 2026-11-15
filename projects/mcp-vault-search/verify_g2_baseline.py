#!/usr/bin/env python
"""Independently verify a G2 real-model JSON report without loading model dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output: Path, historical: Path, root: Path = Path(".")) -> dict:
    report = json.loads(output.read_text(encoding="utf-8"))
    previous = json.loads(historical.read_text(encoding="utf-8"))
    rows = report["results"]
    meta = report["metadata"]
    summary = report["summary"]
    if len(rows) != len(previous) or len(rows) != 4:
        raise AssertionError("No hay exactamente cuatro consultas históricas")

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
    ).strip()
    if meta["git_commit"] != commit:
        raise AssertionError("El reporte no corresponde al commit del checkout")
    for name, expected_hash in meta["code_and_lock_sha256"].items():
        if sha256(root / name) != expected_hash:
            raise AssertionError(f"Hash de código o lockfile incompatible: {name}")

    corpus_expected = previous[0]["evaluation_metadata"]["corpus_sha256"]
    if meta["corpus_sha256"] != corpus_expected or len(corpus_expected) != 12:
        raise AssertionError("El reporte cambió el corpus histórico")
    for name, expected in corpus_expected.items():
        if sha256(root / "examples" / "vault" / name) != expected:
            raise AssertionError(f"Hash del archivo de corpus incorrecto: {name}")
    if meta["model_name"] != previous[0]["evaluation_metadata"]["model_name"]:
        raise AssertionError("El nombre del modelo cambió")
    if meta["model_revision"] != previous[0]["evaluation_metadata"]["model_revision"]:
        raise AssertionError("La revisión del modelo cambió")

    recall3_values = []
    recall5_values = []
    mrr_values = []
    legacy_pass = 0

    for row, expected in zip(rows, previous, strict=True):
        if (row["query"], row["expected_target"], row["designated_distractor"]) != (
            expected["query"], expected["expected_target"], expected["designated_distractor"]
        ):
            raise AssertionError("Las etiquetas históricas fueron modificadas")
        ranked = []
        scores = {}
        for hit in row["full_results"]:
            name = hit["path"]
            if not math.isfinite(hit["score"]):
                raise AssertionError("El reporte contiene un score no finito")
            if name not in ranked:
                ranked.append(name)
                scores[name] = hit["score"]
        if len(ranked) < 10:
            raise AssertionError("Faltan documentos únicos para top 10")
        declared = row["note_rankings"]
        if [r["note"] for r in declared] != ranked:
            raise AssertionError("El orden de notas no corresponde a los hits de chunks")
        for n, record in enumerate(declared, 1):
            if record["rank"] != n or record["score"] != scores[record["note"]]:
                raise AssertionError("Rank o score de documento incorrecto")
        if row["top_10_notes"] != declared[:10]:
            raise AssertionError("El top 10 declarado difiere del ranking completo")

        target, distractor = row["expected_target"], row["designated_distractor"]
        position = ranked.index(target) + 1 if target in ranked else None
        distractor_position = ranked.index(distractor) + 1 if distractor in ranked else None
        if row["target_position"] != position or row["distractor_position"] != distractor_position:
            raise AssertionError("Posiciones objetivo/distractor inconsistentes")
        passed = position is not None and position <= 3 and (
            distractor_position is None or position < distractor_position
        )
        if row["pass"] is not passed:
            raise AssertionError("Criterio PASS/FAIL histórico modificado")
        recall3 = float(position is not None and position <= 3)
        recall5 = float(position is not None and position <= 5)
        reciprocal = 1 / position if position is not None and position <= 10 else 0.0
        for actual, expected_metric in (
            (row["single_target_recall_at_3"], recall3),
            (row["single_target_recall_at_5"], recall5),
            (row["single_target_reciprocal_rank_at_10"], reciprocal),
        ):
            if not math.isclose(actual, expected_metric, abs_tol=1e-12):
                raise AssertionError("Métrica por consulta incorrecta")
        recall3_values.append(recall3)
        recall5_values.append(recall5)
        mrr_values.append(reciprocal)
        legacy_pass += int(passed)

    aggregates = {
        "current_legacy_pass_count": legacy_pass,
        "single_target_recall_at_3": sum(recall3_values) / len(rows),
        "single_target_recall_at_5": sum(recall5_values) / len(rows),
        "single_target_mrr_at_10": sum(mrr_values) / len(rows),
    }
    for name, actual in aggregates.items():
        if not math.isclose(summary[name], actual, abs_tol=1e-12):
            raise AssertionError(f"Métrica agregada incorrecta: {name}")
    if summary["historical_original_pass_count"] != sum(bool(r["pass"]) for r in previous):
        raise AssertionError("Se cambió la tasa histórica en el resumen")
    if not summary["all_independent_checks_passed"]:
        raise AssertionError("La ejecución no declaró todos los checks aprobados")
    return aggregates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("baseline_real.json"))
    parser.add_argument(
        "--historical", type=Path,
        default=Path("evaluate_semantic_results_checkpoint_fixes.json"),
    )
    args = parser.parse_args()
    result = verify(args.output, args.historical)
    print("Independent G2 verification: PASS")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
