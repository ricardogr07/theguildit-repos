# G0 — Resumen de implementación y Definition of Done

**Estado:** PARCIAL / BLOQUEADO PARA G1  
**Fecha:** 2026-11-14  
**Rama de evidencia:** `codex/g0-baseline-evidence`  
**Base comparada:** `codex/sprint-1-semantic-evaluation`, SHA `4a0ceb46a5ae2a6daa8f15939bca44d6198272c4`  
**Evidencia principal:** [BASELINE_MANIFEST.json](BASELINE_MANIFEST.json)

## Trabajo completado

1. Se compararon las referencias de Git para `master`, parte 2 semántica, Colab y PR #3. La parte 2 está en una rama divergente respecto a `master`; Colab contiene un commit adicional y el PR #3 agrega tres commits de métricas.
2. Se identificó `eb62f5d69b42a069bb4fde4c32fe918ac37a28ca` como el checkpoint que declara el README del proyecto. **Esto verifica la declaración del repositorio, no el artículo publicado.**
3. Se registraron SHA-256 del `uv.lock` y `pyproject.toml` del commit base, revisión del modelo y hashes SHA-256 de los 12 Markdown sintéticos.
4. Se compararon los 12 hashes de notas contra `evaluate_semantic_results_checkpoint_fixes.json`: **12/12 coinciden**.
5. Se diferenciaron claramente métricas históricas de cualquier nueva corrida: 4 consultas, 2/4 bajo regla histórica, posiciones objetivo [5,1,1,3], Recall@3=0.75, MRR@10≈0.6333 con un solo target por consulta.
6. Se detectó una diferencia de código: los SHA-256 de `semantic.py` y `evaluate_semantic.py` actuales **no son** los registrados en el reporte histórico. El `server.py` coincide. Por tanto, la corrida histórica no demuestra el comportamiento del commit de Sprint 1.

## DoD y dictamen

| Criterio | Estado | Evidencia / condición pendiente |
| --- | --- | --- |
| G0-1: árbol de commits y baseline identificados | **PASS** | Comparaciones de ramas y SHAs registrados en el manifest |
| G0-2: lockfile, modelo y corpus fijados | **PASS** | SHA-256 de dependencias y 12 archivos, revisión fijada |
| G0-3: evidencia histórica separada de una nueva medición | **PASS** | Reporte histórico y discrepancia de hashes de código documentados |
| G0-4: checkpoint contrastado con artículo 2 publicado | **PENDING** | Falta URL o registro editorial de publicación que permita cotejar el commit publicado |

**Resultado G0:** 3/4 criterios cumplidos. **NO APROBADO** hasta resolver G0-4. La existencia de un README que referencia un checkpoint no demuestra qué commit enlaza realmente el tutorial publicado.

## Pendiente único para aprobar G0

Obtener URL del artículo 2 publicado o un registro editorial de publicación fiable. Abrir el artículo y comprobar el enlace/referencia al código. Si no contiene commit ni tag fijo, documentar el SHA realmente reproducible y la corrección editorial necesaria. Actualizar manifest y este resumen con evidencia y volver a evaluar G0-4.

## Alcance y seguridad

- No se modificaron `semantic.py`, `server.py`, el evaluador ni las pruebas.
- No se corrió el modelo real; eso corresponde a G2.
- No se ejecutó ni adelantó G1.
- No se fusionó ningún PR ni se creó tag/release.
- Solo se utilizó un vault sintético.

## Referencias

- [Sprint Issue #2](https://github.com/ricardogr07/theguildit-repos/issues/2)
- [PR de métricas #3](https://github.com/ricardogr07/theguildit-repos/pull/3)
- [Commit declarado para Parte 2](https://github.com/ricardogr07/theguildit-repos/commit/eb62f5d69b42a069bb4fde4c32fe918ac37a28ca)
