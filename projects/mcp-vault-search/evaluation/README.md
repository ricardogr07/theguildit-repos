# G3 — Expanded retrieval benchmark: annotation protocol

**Issue:** #7. **Corpus:** the 12 synthetic Markdown notes from G2. **Model:** pinned multilingual MiniLM on CPU. **Status:** 24 proposed, NOT independently approved.

## Dataset and frozen evaluation splits

- 4 original queries are copied verbatim to `historical_queries.json`; their historical single-target labels are **not** retuned.
- 16 new `development_queries.json` queries support diagnostics and later changes in G4.
- 8 new `holdout_queries.json` queries are reserved for **one-time, post-selection testing**. They are stored in the same repository, so they are *not cryptographically sealed*. Researchers reviewing this PR can see them. Do not inspect their outcomes or tune on their labels.
- `qrels.json` holds 24 proposed relevance judgments (including multi-relevant and 0-relevant); no independent human annotation has been completed yet.
- Zero-relevance queries are counted in a separate forced-hit/abstention diagnostic. The current semantic retriever has **no threshold for saying no answer**. Do not report OOD Recall or MRR as zero or 100%.
- Relevance judgments are binary. nDCG@5 is left undefined until graded, independently reviewed labels exist.

## Reviewer checklist (mandatory for G3 PASS)

1. Read **all 12 actual notes** in `examples/vault`, then read each of the 24 queries.
2. For each query, decide which of the 12 notes genuinely answer it; include **all** defensible relevant notes, not just the seeded proposal. Verify there are 0/1/multiple cases. Treat the listed `rationale` as a hypothesis, not as an instruction.
3. Record actual reviewer ID, date, rationale and disagreements in `qrels.json`. Set each `review_status` to `approved` **only after reading each relevant and borderline note**.
4. Have a separate person or agent challenge the judgments for ambiguous cases. Record disagreements and their resolution, especially D02, D08, D14, D16, H05 and OOD D15/H07/H08.
5. Do **not** use the holdout to choose thresholds, corpus changes, chunking, ranking weights, prompts or architectures. Record the candidate model/strategy and commit before running the holdout.
6. Re-execute the development benchmark after final annotations are merged, and only then run the holdout as a one-time acceptance check.

## Reproduction

From `projects/mcp-vault-search`:

```bash
uv sync --locked --extra semantic --python 3.11
uv run --locked --extra semantic --python 3.11 python -m unittest discover -s tests -v

# Exploratory only, explicitly marked as unreviewed:
uv run --locked --extra semantic --python 3.11 python -m evaluation.run_expanded --split development --allow-provisional --output evaluation/development_results.json --metrics-output evaluation/retrieval_metrics.json
uv run --locked --extra semantic --python 3.11 python -m evaluation.verify_expanded --split development --output evaluation/development_results.json

# Only once all qrels have been independently reviewed:
uv run --locked --extra semantic --python 3.11 python -m evaluation.run_expanded --split holdout --allow-holdout --output evaluation/holdout_results.json --metrics-output evaluation/holdout_metrics.json
```

All outputs are descriptive measurements of this tiny synthetic corpus; no claims of broad retrieval accuracy or generalization are warranted.
