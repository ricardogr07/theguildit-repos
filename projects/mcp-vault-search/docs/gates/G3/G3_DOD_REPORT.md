# G3 — Implementation and Definition of Done

**Issue:** [#7](https://github.com/ricardogr07/theguildit-repos/issues/7) · **Status:** implementation for external review; **gate not approved**.

## Implemented

- 24 new distinct queries, 16 development and 8 holdout; four original queries remain intact.
- 24 proposed human relevance candidates tied to the actual twelve synthetic notes; zero-relevant and multiple-relevant cases included.
- Read-only per-note metrics: Recall@3/5, Precision@3, MRR@10, plus separate OOD forced-hit and abstention.
- Developer-run benchmark with pinned real model, metadata, corpus/code hashes and independent JSON verifier.
- Explicit holdout opt-in; refuses held-out run while annotations have not been approved.
- Offline unit tests for partition integrity, duplicate queries, missing qrels, impossible relevant files, and label approval.
- GitHub Actions workflow runs **development only**, marking all metrics provisional and publishing JSON/logs for independent review.

## Definition of Done

| Issue #7 criterion | Status | Evidence / work outstanding |
| --- | --- | --- |
| At least 20 new queries (24) separate from four historical | IMPLEMENTED | `evaluation/{historical,development,holdout}_queries.json` |
| Spanish/English, distractors, ambiguity, multi-relevant, no-answer | IMPLEMENTED | `evaluation/qrels.json` proposed, review pending |
| Human-reviewed 0/1/many qrels, rationale and disagreements | **BLOCKED** | Independent review with actual reviewer ID and date is required; do not self-certify |
| Holdout separate and untouched for tuning | IMPLEMENTED WITH CAVEAT | Split exists and runner denies it by default; labels are stored in Git and thus visible, not secret |
| Per-query and aggregate metrics, plus nDCG if graded | PENDING CI | nDCG N/A with binary labels; real-model dev run and independent verification must pass |
| No-answer/abstention evaluated independently | IMPLEMENTED, PENDING CI | Current retriever returns hits on OOD; no built-in abstention threshold |

## Next steps

1. Have independent reviewer approve/refine every qrel against all twelve notes, and record any disputes.
2. Check CI on the final PR SHA: unit matrix, model on development, JSON verifier and evidence artifacts.
3. Do not open/test holdout until strategy is frozen for G4.
4. Merge only after owner review; the gate does not PASS simply because CI succeeds.
