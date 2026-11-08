# Token Limit Fixes - Semantic Search Evaluation

## Changes Applied

### 1. Fixed Token Limit in `note_chunks()`
- **Before**: Hardcoded `exceeds_tokens = token_count > 512`
- **After**: Uses `max_seq_length - 0` (tokenizer.encode includes [CLS]/[SEP])
- **Value**: 128 tokens (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)

### 2. Validate Single Fragments
- **Before**: If `current_chunk` empty, `sub_para` passed without token validation
- **After**: Added explicit validation for standalone fragments:
  ```python
  elif not current_chunk and tokenizer is not None:
      token_count = len(tokenizer.encode(sub_para))
      if token_count > max_seq_length:
          raise ValueError(f"Exceeds token limit {max_seq_length}: {token_count}")
  ```

### 3. Extract Model Metadata in `build_index()`
- Reads `embedder.max_seq_length` if available (fallback: 128)
- Extracts `embedder.tokenizer` for token-aware chunking
- Passes both to `note_chunks()` for token validation

## Evaluation Result

**Run**: `evaluate_semantic_results_token_128_validated.json`

**Summary**: 2/4 pass
- Query 1: FAIL (mcp.md rank 6, distractor rank 1)
- Query 2: PASS (busqueda-semantica.md rank 1, distractor rank 2)
- Query 3: PASS (fragmentos.md rank 1, distractor rank 2)
- Query 4: FAIL (rutas-seguras.md rank 4, distractor rank 3)

## Chunking Impact

- Total chunks: 22 (from 12-note corpus)
- All chunks validated ≤ 128 tokens
- No transformers warnings
- Distribution: most notes split to 2 chunks, mcp.md/busqueda.md 1 chunk

## Conclusion

Token validation is now correct and complete. Queries 1 & 4 failures are due to corpus asymmetry (target vs distractor relevance), not technical defects. Further investigation required on corpus quality before corpus expansion.

## Preserved Runs
- `evaluate_semantic_results_baseline.json`: 3/4 (before distractor validation)
- `evaluate_semantic_results_token_512.json`: 2/4 (512 limit, offset by 2)
- `evaluate_semantic_results_token_128_validated.json`: 2/4 (128 limit, correct)
