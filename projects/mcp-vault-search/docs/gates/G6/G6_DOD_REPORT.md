# G6 — Definition of Done

**Issue:** [#10](https://github.com/ricardogr07/theguildit-repos/issues/10).  
**Status:** BLOCKED / PREPARED, **not** approved. No tag and no Docker branch created.

| Gate criterion | Status |
| --- | --- |
| Archive G0–G5 evidence and resolve CRITICAL/HIGH | PENDING independent G3/G5 reviews |
| Document reproducibility, reindexing and security limitations | PREPARED in project docs; owner must verify |
| Verify test suite and real model against **integrated final SHA** | PENDING G3–G6 merges |
| Explicit owner signoff | PENDING |
| Create immutable `tutorial-2-stable` tag | BLOCKED |
| Persist final release manifest and rollback instructions | TEMPLATE IMPLEMENTED; external manifest pending |
| Docker branch from stable tag | BLOCKED; no feature work mixed in |

## Implemented safeguards

- `scripts/check_release_gate.py`: rejects missing merge SHAs, unsigned owner/independent reviews, unreviewed qrels, unknown candidate SHA, missing evidence, model revision changes or HIGH/CRITICAL defects.
- `tests/test_g6_release_gate.py`: synthetic positive and negative fixtures, not fabricated production approvals.
- Workflow G6 tests the guard and expects exit **2** for the deliberately blocked in-repo manifest.
- No release/tag or Docker branch mutation is performed by these files.

## Conditions for PASS

See [G6_RELEASE_PLAN.md](G6_RELEASE_PLAN.md). Approval requires real independent attestations, the four PRs merged to integration branch, final CI and an external final manifest generated after the last merge. A green preflight CI is **not** a G6 PASS.

**Do not close #10 or #2 while any condition remains unmet.**
