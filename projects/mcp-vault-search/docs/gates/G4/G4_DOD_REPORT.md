# G4 — Rendimiento y experimentos: Definition of Done

**Issue:** [#8](https://github.com/ricardogr07/theguildit-repos/issues/8). **Estado:** implementación disponible para revisión; no se acepta el gate hasta CI, evidencia y qrels revisadas.

## Diseño pre-registrado
- Modelo y corpus sin cambios respecto a G2: 12 notas sintéticas, multilingüe MiniLM CPU fijado.
- Calentamiento de 16 consultas, luego **32 mediciones warm** sobre las 16 consultas de desarrollo.
- Métricas: carga de modelo, indexación, latencias p50/p95/mean (ms), memoria máxima real de proceso en Linux (`ru_maxrss`).
- Corpus sintético escalado de 12 / 100 / 1,000 archivos. Las copias determinísticas solo prueban capacidad y NO calidad.
- **A (baseline):** nota clasificada por el mejor chunk.
- **B (experimental):** media de los dos chunks más relevantes por nota; si hay solo uno, usarlo.
- Criterio para preferir B al baseline: `delta mean Recall@3 >= +0.05`, `delta MRR@10 >= -0.01`, cero regresiones en Recall@3 por consulta. Todo sobre desarrollo; **nunca promover automáticamente B**.

## DoD técnico
| Criterio | Estado | Evidencia |
| --- | --- | --- |
| Inicio frío, tiempo de indexación, memoria y p50/p95 de >=30 mediciones | PENDING CI | `evaluation/experiment_g4.py`, workflow G4 |
| Hardware, versión, repeticiones, notas/chunks y datos crudos | PENDING CI | JSON `g4_performance_results.json` |
| Escalado reproducible con 12, 100 y 1000 notas | PENDING CI | Conteo de notas y chunks en JSON |
| Comparar >=1 alternativa contra baseline congelado | IMPLEMENTADO / PENDING CI | A (best chunk) vs B (mean top 2 chunks), mismo dataset, misma consulta |
| Deltas por consulta y regresiones; no contaminar holdout | IMPLEMENTADO / PENDING CI | `per_query`, `used_development_only: true` |
| Promover solo ganancia defendible y sin regresiones críticas | NO PROMOVIDA | No se cambia producción, no hay qrels aprobadas |
| Reporte y revisión por owner | PENDING | Este reporte y comentarios en PR |

## Caveats
Los valores comparados se calculan sobre qrels propuestas de G3. Son exploratorios y no certifican calidad hasta revisión humana. No se ejecuta el holdout hasta G3 aprobado y la estrategia elegida fijada. La memoria reporta **pico de proceso**, no incremento por escala; la carga del modelo puede incluir descarga desde Hugging Face. No se altera `semantic.py`, `server.py` ni `evaluate_semantic.py`.

**Estado del gate:** pendiente de evidencia CI y revisión independiente; el responsable fusiona PRs.
