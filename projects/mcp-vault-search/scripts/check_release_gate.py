#!/usr/bin/env python
"""Read-only G6 gate validator. It NEVER creates tags or branches.

A final release manifest is an external attestation generated AFTER all PRs have
merged; do not edit a commit to contain its own SHA (self-referential hash).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_GATES = ("G0", "G1", "G2", "G3", "G4", "G5")
REQUIRED_MERGES = ("13", "14", "15", "16")
PROJECT = Path(__file__).resolve().parents[1]
DEFAULT = PROJECT / "docs" / "gates" / "G6" / "RELEASE_MANIFEST.json"


def release_blockers(manifest: dict, qrels: dict, current_sha: str) -> list[str]:
    """Deterministic validation of attestations, annotations and code SHA."""
    blocked: list[str] = []
    if manifest.get("project") != "mcp-vault-search":
        blocked.append("Project manifest does not identify mcp-vault-search")
    if manifest.get("release_target_branch") != "codex/mcp-vault-colab":
        blocked.append("Release must come from the integrated repository branch")
    if manifest.get("proposed_release_tag") != "tutorial-2-stable":
        blocked.append("Unexpected stable tag")
    if manifest.get("proposed_docker_branch") != "codex/tutorial-3-docker":
        blocked.append("Unexpected Docker branch")
    if manifest.get("status") != "APPROVED_FOR_FREEZE":
        blocked.append("Release approval status is not APPROVED_FOR_FREEZE")
    candidate_sha = manifest.get("candidate_commit_sha")
    if not isinstance(candidate_sha, str) or not SHA.fullmatch(candidate_sha):
        blocked.append("Missing valid final candidate SHA")
    elif candidate_sha != current_sha:
        blocked.append("The release manifest does not identify the checkout HEAD")

    approvals = manifest.get("gate_approvals") or {}
    for gate in REQUIRED_GATES:
        if not isinstance(approvals.get(gate), dict) or approvals[gate].get("pass") is not True:
            blocked.append(f"Gate {gate} has not been formally approved")

    merges = manifest.get("pr_merges") or {}
    for pr in REQUIRED_MERGES:
        commit = merges.get(pr)
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            blocked.append(f"PR #{pr} has no recorded merge SHA (verify via GitHub)")

    owner = manifest.get("owner_approval") or {}
    if not owner.get("reviewer") or not owner.get("approved_at_utc"):
        blocked.append("The project owner did not sign off on the candidate")
    review = manifest.get("independent_review") or {}
    if not (
        review.get("reviewer") and review.get("reviewed_at_utc")
        and isinstance(review.get("reviewed_commit_sha"), str)
        and SHA.fullmatch(review["reviewed_commit_sha"])
        and review.get("report_path")
    ):
        blocked.append("Missing independent adversarial review and reviewed code SHA")

    for severity in ("critical", "high"):
        items = manifest.get(f"open_{severity}_defects")
        if items is None or not isinstance(items, list):
            blocked.append(f"Missing {severity} defect inventory")
        elif items:
            blocked.append(f"Open {severity.upper()} defects: {len(items)}")

    judgments = qrels.get("judgments")
    if not isinstance(judgments, list) or len(judgments) != 24:
        blocked.append("Expected 24 reviewed qrel judgments")
    elif any(
        not isinstance(j, dict)
        or j.get("review_status") != "approved"
        or not j.get("reviewer")
        or not j.get("reviewed_at")
        or not j.get("rationale")
        for j in judgments
    ):
        blocked.append("One or more relevance judgments lack independent human approval")

    evidence = manifest.get("release_evidence") or {}
    for name in ("g2_real_model_ci", "g3_dev", "g4_performance", "g5_independent", "head_ci"):
        if not evidence.get(name):
            blocked.append(f"Missing CI or approval evidence: {name}")

    model = manifest.get("model") or {}
    if model.get("revision") != "e8f8c211226b894fcb81acc59f3b34ba3efd5f42":
        blocked.append("Embedding model revision changed")
    return blocked


def repo_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT)
    parser.add_argument("--qrels", type=Path, default=PROJECT / "evaluation" / "qrels.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    qrels = json.loads(args.qrels.read_text(encoding="utf-8"))
    current = repo_head()
    blockers = release_blockers(manifest, qrels, current)
    result = {
        "gate": "G6", "candidate_commit": current,
        "eligible": not blockers, "blockers": blockers,
        "side_effects": "none; no tag or branch created",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if blockers:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
