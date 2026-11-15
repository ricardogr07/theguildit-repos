# G1 — Matriz de pruebas

**Gate:** G1 / Issue #5 · **PR:** #11 · **Base:** `98cc296a11d058f79b9d41e5699f8d06381339f7`

Este documento registra qué prueba verifica cada requisito. Los resultados de CI se completan **solo** al disponer de logs en el SHA exacto del PR.

| Prueba / evidencia | Entorno | Comando o archivo | Resultado |
| --- | --- | --- | --- |
| Suite unitaria, integraciones MCP y métricas | Linux Python 3.11 y 3.12 | `uv sync --locked && uv run --locked python -m unittest discover -s tests -v` | PENDING CI |
| Suite unitaria, integraciones MCP y métricas | Windows Python 3.11 y 3.12 | Mismo workflow | PENDING CI |
| Instalación desde wheel, sin fuente editable | Ubuntu Python 3.12 | `uv build` + job "Wheel installation and MCP" | PENDING CI |
| Embedding índice: valores vacíos, cero, no unitarios, NaN/Inf y texto inválido | FakeEmbedder | `test_g1_validation.EmbeddingValidationTest.test_build_index_rejects_malformed_vectors` | PENDING CI |
| Embedding índice: lote y dimensiones inconsistentes | FakeEmbedder | `test_build_index_requires_one_vector_per_chunk`; `test_build_index_rejects_dimensions_that_differ_between_chunks` | PENDING CI |
| Embedding consulta: lote erróneo, valores no finitos, norma inválida y dimensión errónea | FakeEmbedder | `test_query_rejects_malformed_vectors` | PENDING CI |
| Índice construido manualmente con vector corrupto | FakeEmbedder | `test_search_rejects_corrupt_index_vector_even_if_constructed_manually` | PENDING CI |
| Vault vacío, búsqueda sobre índice vacío, consulta y límites inválidos | FakeEmbedder | `test_empty_index_and_invalid_input_fail_explicitly` | PENDING CI |
| Nota nueva no aparece hasta reindexar | FakeEmbedder | `test_new_note_does_not_appear_until_reindex` | PENDING CI |
| Chunk largo CRLF sin exceder límite ni perder texto de origen | Tokenizer simulado | `test_source_chunking_with_crlf_and_long_word_does_not_exceed_limits` | PENDING CI |
| Tokenizer incapaz de representar contenido falla explícitamente | Tokenizer simulado | `test_unrepresentable_character_fails_instead_of_looping` | PENDING CI |
| Evaluación sin `sentence-transformers` falla con código != 0 | Import mocking | `test_missing_sentence_transformers_fails_with_nonzero_exit` | PENDING CI |
| MCP registra herramientas, conserva contratos y responde a errores sin cerrar sesión | Servidor `stdio` real + embedder simulado | `test_server.py`, incluido error `PRIVATE_SENTINEL_INTERNAL` | PENDING CI |
| Path traversal, symlinks/junctions, UTF-8 y lectura protegida | Sistema de archivos | `test_vault.py`, `test_semantic.py` | PENDING CI |
| Fallos parciales de notas/lecturas y hashes de notas modificadas | Sistema de archivos | `test_semantic.py` | PENDING CI |

## Comportamiento deliberadamente no incluido

- **Modelo real y resultados de recuperación:** G2, no G1.
- **Reindexación automática:** no implementada. Notas nuevas no aparecen y notas cambiadas quedan excluidas hasta reconstruir el índice/reiniciar proceso.
- **Sandbox del sistema operativo y TOCTOU:** fuera del alcance local; se documentan los límites de confianza del vault.
- **Límite absoluto al número de notas y bytes indexados:** el ejemplo mantiene dependencia de memoria para vaults pequeños; no se declara apto para entrada hostil o escala grande.

## Registro de aprobación

La aprobación requiere link al workflow exitoso para el commit final, números pass/fail/skip obtenidos de sus logs y dictamen DoD en `G1_DOD_REPORT.md`.
