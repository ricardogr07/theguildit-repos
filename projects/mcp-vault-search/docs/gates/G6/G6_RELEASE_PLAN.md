# G6 — Release plan and Docker handoff

**Issue:** #10, **Release gate:** G6. **Status:** candidate prepared, NOT stable. No automatic tag or Docker branch is authorized.

## Stacked PRs and merge order (IMPORTANT)

The PR base branches are stacked for parallel review. Merging a child into its feature parent is **NOT** the same as integrating it into `codex/mcp-vault-colab`. Merge sequentially:

1. **#13 G3** base `codex/mcp-vault-colab`: independent reviewer must approve 24 qrels; verify CI; Ricardo merges.
2. Retarget **#14 G4** to `codex/mcp-vault-colab` **after** #13 merges. Verify diff includes *only G4*, not G3; rerun CI on its final SHA, verify performance findings, then Ricardo merges.
3. Retarget **#15 G5** to `codex/mcp-vault-colab` **after** #14 merges. Verify *only G5* diffs; run independent adversarial review, resolve HIGH/CRITICAL, then Ricardo merges.
4. Retarget **#16 G6** to `codex/mcp-vault-colab` **after** #15 merges. Confirm all DoD and evidence, then Ricardo merges. Merge commits from #13–#16 are recorded in a **separate final release attestation**.

**Do not merge directly into feature branch bases as the final integration action.** The expected release branch is `codex/mcp-vault-colab`, not `master` (which still represents tutorial 1).

## Definition of Done before creating stable tag

- [ ] G3: 24 qrels approved by a reviewer distinct from their author, each with name/date/rationale; borderline cases resolved. Holdout evaluated only after an experiment choice is frozen, not used for tuning.
- [ ] G4: CPU benchmark reproducible (12/100/1000 synthetic notes, p50/p95, peak RSS), independent JSON verification. Keep baseline if alternative does not defensibly outperform.
- [ ] G5: independent reviewer inspected code and tests, ran at least 3 new adversarial cases; 0 CRITICAL/HIGH remain, MEDIUM have owner+mitigation.
- [ ] G6: all PRs #13–#16 merged into `codex/mcp-vault-colab`; CI, benchmark and audits refer to the integrated code.
- [ ] Release evidence persisted beyond 90-day GitHub artifact retention; include SHA-256 of downloaded JSON and logs, CI URL, version/model revision and corpus.
- [ ] Ricardo explicitly approves release SHA and medium risks.
- [ ] Final external `RELEASE_MANIFEST.json` identifies exact integrated SHA and signed approvals, and passes `scripts.check_release_gate`.
- [ ] Tag `tutorial-2-stable` is created **only on the approved integrated SHA**, never moved afterwards.
- [ ] Docker branch created **from the stable tag**, not from #16 or another unmerged feature branch.

## Why the final manifest must be external

The proposal in `docs/gates/G6/RELEASE_MANIFEST.json` is intentionally BLOCKED. After all merges, the final SHA cannot be embedded in the same Git commit whose SHA it is supposed to identify: that would create a self-referential hash. Generate the final release manifest as a **release artifact outside the tagged commit** and archive it permanently. Supply that file via `--manifest`.

## Manual freeze commands after all gates PASS

From a clean Git clone with the approved GitHub permissions:

```bash
git fetch origin --prune --tags
git switch codex/mcp-vault-colab
git pull --ff-only origin codex/mcp-vault-colab

# Verify complete integrated commit; do not execute with pending G3/G4/G5.
git rev-parse HEAD

cd projects/mcp-vault-search
uv sync --locked --extra semantic --python 3.11
uv run --locked --extra semantic --python 3.11 python -m unittest discover -s tests -v
uv run --locked --extra semantic --python 3.11 python run_g2_baseline.py --output baseline_real.json --summary baseline_summary.json
uv run --locked --extra semantic --python 3.11 python verify_g2_baseline.py --output baseline_real.json

# The final release manifest is an external artifact, prepared and signed after merges.
uv run --locked --python 3.11 python -m scripts.check_release_gate --manifest /path/to/FINAL_RELEASE_MANIFEST.json
cd ../..

# Only after the validator passes AND the owner explicitly approves:
git tag -a tutorial-2-stable "$(git rev-parse HEAD)" -m "MCP Vault Search: independently reviewed stable semantic checkpoint"
git push origin refs/tags/tutorial-2-stable

# Docker tutorial's new branch must start at this precise tag:
git switch -c codex/tutorial-3-docker tutorial-2-stable
git push -u origin codex/tutorial-3-docker
```

On PowerShell, replace `$(git rev-parse HEAD)` with the commit hash already verified, and adjust POSIX paths. Do not point Docker to the mutable integration branch.

## Rollback

Tags `tutorial-1` and `tutorial-2` remain untouched. Revert a new Docker branch to the stable tag if Docker introduces regressions. Never move historical tags. Any post-freeze functional change requires a new reviewed tag and G5/G6 revalidation.
