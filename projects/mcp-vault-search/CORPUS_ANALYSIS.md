# Corpus Analysis - Query 1 & 4 Failure Investigation

## Evaluation Status
- **Result**: 2/4 pass with complete token validation
- **Query 2 & 3**: PASS ✓
- **Query 1 & 4**: FAIL (corpus/distractor analysis needed)

## Query 1: "¿Cómo puede un asistente usar funciones de otras aplicaciones?"

### Target Analysis
- **Target**: mcp.md (rank 6)
- **Relevance**: Directly answers question—MCP (Model Context Protocol) enables using external functions
- **Content**: Brief (217B), explains MCP connects clients with tools via common protocol

### Distractor Analysis
- **Distractor**: contenedores.md (rank 1)
- **Relevance**: Partially relevant—Docker containers *execute* the server, enabling "use of external functions" in infrastructure context
- **Content**: Detailed (704B), explains containerization, volume mounting, distribution

### Additional Relevant Note
- **herramientas-mcp.md**: Not designated distractor, but also answers the query
- **Observation**: Query 1 may have multiple valid answers; mcp.md + herramientas-mcp.md are semantically equivalent
- **Issue**: contenedores.md (infrastructure context) ranks above both despite being about "how to run" not "how to use functions"

### Hypothesis
- mcp.md is too brief (217B) to compete with contenedores.md (704B) on semantic similarity
- Model may conflate "using external functions" with "executing external code" (containers do execute)
- herramientas-mcp.md likely contains richer semantics than mcp.md but both are functionally correct answers

### Recommendation
- Current criterion (target ranks better than designated distractor) is valid
- Defer corpus expansion until confirming query semantics with human review
- Note: herramientas-mcp.md should be evaluated as secondary target if available

---

## Query 4: "¿Cómo evito que el asistente abra documentos fuera de la carpeta que le compartí?"

### Target Analysis
- **Target**: rutas-seguras.md (rank 4)
- **Relevance**: Directly answers question—explains path validation, rejecting absolute paths and symlinks
- **Content**: Medium (629B), explains validation logic and restrictions

### Distractor Analysis
- **Distractor**: datos-y-privacidad.md (rank 3)
- **Relevance**: Partially relevant—explains privacy limits, but primarily about data transmission to external providers
- **Content**: Detailed (781B), explains local embedding execution, fragment limits

### Query/Corpus Mismatch
- Query focuses on: **Access control within vault** (rutas-seguras theme)
- Distractor addresses: **Data privacy during transmission** (datos-y-privacidad theme)
- **Semantic confusion**: Both use keywords "privacidad" / "control" / "restricción"
- Model ranks datos-y-privacidad higher due to length and shared privacy vocabulary

### Hypothesis
- Query 4 is semantically clean (rutas-seguras is the correct answer)
- datos-y-privacidad is a stronger semantic match due to length and shared privacy terminology
- This is a **distractor selection issue**, not corpus weakness
- If query truly means "prevent access outside folder", rutas-seguras is unambiguously correct
- If query intended to include privacy concerns, distractor choice is wrong

### Recommendation
- Current criterion (target ranks better than designated distractor) is valid
- Query 4 criterion may need re-evaluation: Is distractor too semantically similar?
- Consider if datos-y-privacidad should be the target instead (privacy-focused interpretation)
- Defer corpus expansion; this is a query/distractor alignment issue

---

## Summary

| Query | Target | Target Rank | Distractor | Distractor Rank | Issue |
|-------|--------|-------------|-----------|-----------------|-------|
| 1 | mcp.md | 6 | contenedores.md | 1 | Target too brief; distractor semantically strong on "using/executing" |
| 2 | busqueda-semantica.md | 1 | busqueda.md | 2 | ✓ PASS |
| 3 | fragmentos.md | 1 | bitacora-de-incidente.md | 2 | ✓ PASS |
| 4 | rutas-seguras.md | 4 | datos-y-privacidad.md | 3 | Target correct; distractor semantically similar on privacy/control |

## Next Steps (per plan)

1. **Do not expand corpus yet** — Defer until after human review of query relevance
2. **Query 1**: herramientas-mcp.md should be investigated as alternative target or multi-valid answer
3. **Query 4**: Confirm query intent; consider if distractor alignment is issue
4. **Preserve results**: Keep 2/4 evaluation as evidence before any corpus changes

## Token Validation Status
- ✅ All fragments validated ≤ 128 tokens (MiniLM limit)
- ✅ Validation covers: initial chunks, reassigned chunks, final chunk
- ✅ No fragments exceed limit
