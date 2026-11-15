# G1 — Definition of Done y registro de aprobación

**Issue:** #5 · **PR:** #11 · **Estado inicial:** PENDING CI / revisión técnica  
**Base:** `codex/mcp-vault-colab`, SHA `98cc296a11d058f79b9d41e5699f8d06381339f7`.  
**Rama:** `codex/g1-semantic-correctness`

## Cambios introducidos

1. Validación de embeddings numéricos y finitos, norma L2 ~1 y dimensiones consistentes en índice, consulta y búsqueda; rechazar índices y lotes malformados.
2. Rechazo de consultas vacías y `limit` inválido previo a cargar el modelo.
3. Excepciones inesperadas no exponen mensajes internos a clientes MCP; detalles se registran en stderr.
4. Evaluador semántico retorna estado no exitoso cuando falta la dependencia.
5. Nuevas pruebas unitarias y prueba MCP de proceso real con errores, recuperación y redacción.
6. README documenta necesidad de reindexar y evita sobrescribir informes históricos.

## Definition of Done

| Criterio bloqueante del Issue #5 | Estado | Evidencia |
| --- | --- | --- |
| Evaluador termina con error ante dependencia faltante | IMPLEMENTADO / PENDING CI | `evaluate_semantic.py`, `test_missing_sentence_transformers_fails_with_nonzero_exit` |
| Embeddings invalidos: NaN, Inf, cero, dimensiones, normas | IMPLEMENTADO / PENDING CI | `semantic.py`, `test_g1_validation.py` |
| Chunking, índice vacío, consultas y límites | IMPLEMENTADO / PENDING CI | `test_semantic.py`, `test_g1_validation.py` |
| Rutas, junctions, UTF-8, notas editadas, borradas | CUBIERTO EN PR / PENDING CI | `test_vault.py`, `test_semantic.py`, `test_server.py` |
| Contratos MCP y continuidad tras errores | IMPLEMENTADO / PENDING CI | `test_server.py` con proceso `stdio` instalado |
| Linux/Windows Python 3.11/3.12 y wheel | PENDING CI | Workflow `.github/workflows/mcp-vault-search.yml` |
| Documentar reindexación diferida | IMPLEMENTADO | README y `G1_TEST_MATRIX.md` |

## Requisitos para cerrar

- Confirmar el resultado de CI en el SHA final del PR, incluyendo la matriz Linux/Windows y wheel.
- Resolver cualquier fallo descubierto sin rebajar los tests.
- Registrar conteos exactos y URL de CI.
- Recibir revisión técnica del responsable y **merge realizado por Ricardo**.

**Dictamen preliminar:** NO CERRAR G1 hasta evidencias CI + aprobación/merge. No se ha iniciado G2.
