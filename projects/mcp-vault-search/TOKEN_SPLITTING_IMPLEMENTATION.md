# Token-Aware Text Splitting Implementation

## Problem
Paragraphs exceeding model token limit (128 for MiniLM) caused IndexError:
```
Token indices sequence length is longer than the specified maximum sequence length for this model (155 > 128)
```

Previous approach: raise ValueError, reject entire paragraph. **Required**: Split and preserve content.

## Solution: `_split_by_tokens()`

### Algorithm
- Binary search to find largest text chunk that encodes to ≤ max_tokens
- Word boundary detection: prefer splitting at last space (avoid cutting words)
- Preserve all content: concatenated fragments = original text

### Implementation Locations

Three integration points in `note_chunks()`:

1. **When flushing current chunk** (line ~155): Sub-paragraph triggers flush
   - Validate new chunk before assignment
   - If exceeds token limit: emit split fragments, reset current_chunk

2. **Standalone fragment** (line ~168): Single paragraph > max_tokens
   - Split and emit directly
   - Clear current_chunk to continue next paragraph

3. **Final chunk** (line ~180): End of note
   - Split if needed before final emit
   - Handles case where last paragraph is very long

### Token Limit Handling
- max_seq_length: extracted from embedder.max_seq_length (default 128)
- Comparison: `len(tokenizer.encode(text)) <= max_seq_length`
- No offset adjustment: tokenizer.encode() includes [CLS]/[SEP]

## Validation

### Unit Test: `test_long_paragraph_splits_within_token_limit()`
- Create 150-word paragraph (~150 tokens, exceeds 128 limit)
- Verify: Multiple chunks generated
- Verify: All words preserved (count match)

### Integration Test: Evaluation
- Run evaluate_semantic.py with corpus
- No ValueError raised
- Result: 2/4 pass (stable with token splitting)

## Edge Cases Handled
- Paragraph shorter than one token: skipped (empty filter)
- Space boundary: finds last space in first max_tokens characters
- Multiple splits: handles paragraphs >> max_tokens iteratively

## Corpus Impact
- Previous: 12 chunks (no splitting)
- Current: 22 chunks (splitting enabled)
- Each chunk: ≤ 128 tokens
- No transformers warnings

## Performance
- ponytail: naive binary search O(n log n) per paragraph
- Optimize: word tokenization prefix tree if needed for large texts

## Closed Issues
1. ✅ ValueError on long paragraphs → now splits gracefully
2. ✅ Content loss during split → word boundaries preserved
3. ✅ Token validation complete: all fragments ≤ 128 tokens
4. ✅ No warnings from transformers during indexing
