# G4 — Rendimiento y experimento de ranking: Definition of Done

**Issue:** [#8](https://github.com/ricardogr07/theguildit-repos/issues/8) · **PR:** [#14](https://github.com/ricardogr07/theguildit-repos/pull/14)  
**Estado técnico:** medición reproducible / experimento documentado; **GATE PENDING G3 y revisión externa**.  
**Primera corrida verificada:** [G4 performance run](https://github.com/ricardogr07/theguildit-repos/actions/runs/43715673381) · [JSON y logs](https://github.com/ricardogr07/theguildit-repos/actions/runs/43715673381/artifacts/14162891176) · SHA `5034c41ea23520ce312f3894746c5bb751ba257a`.

## Diseño pre-registrado
- Modelo CPU y corpus sin cambios respecto a G2: 12 notas originales con SHA-256 validado.
- 16 consultas de calentamiento y 32 mediciones warm en desarrollo exclusivamente.
- Indexación a partir de 12/100/1000 archivos sintéticos. Los 100/1000 son **réplicas** para carga; no son corpus independiente de calidad.
- **A (baseline):** ordenar notas por el mejor chunk.
- **B (alternativa):** media de los dos chunks con mayor score, o uno si solo tiene uno.
- Requisito previo para preferir B: delta Recall@3 ≥ +0.05, delta MRR@10 ≥ −0.01, cero regresiones Recall@3 por consulta.

## Resultado CPU (una ejecución, no SLA)

| Métrica | Resultado |
| --- | ---: |
| Modelo CPU, warm query p50 | **18.296 ms** |
| Modelo CPU, warm query p95 | **19.579 ms** |
| Pico RSS del proceso | **1765.94 MiB** |
| 12 notas, 22 chunks, construcción índice | **0.711 s** |
| 100 notas, 183 chunks, construcción índice | **4.315 s** |
| 1000 notas, 1833 chunks, construcción índice | **39.081 s** |

Los picos de memoria son máximos del proceso, no RAM adicional por tramo. La carga fría del modelo puede incluir descargas/caché. Las latencias provienen de 32 mediciones sobre un solo runner; no se deben presentar como SLA.

## Decisión experimental

| Métrica de calidad A/B | Delta B − A en desarrollo, qrels propuestas |
| --- | ---: |
| Macro Recall@3 | **−0.03333** |
| Macro Recall@5 | **+0.10000** |
| Macro Precision@3 | ~0 |
| MRR@10 | **−0.01778** |

**B NO satisface el criterio preregistrado. Se conserva la implementación A sin cambios en producción.** Estas cifras usan qrels todavía no revisadas humanamente; su interpretación de calidad es provisional. Ninguna consulta holdout fue ejecutada.

El [verificador independiente de datos](https://github.com/ricardogr07/theguildit-repos/actions/runs/43715673381) devolvió `independent_verification: PASS` y confirmó hashes, p50/p95, deltas y ausencia de holdout.

## DoD del Issue #8

| Requisito | Estado |
| --- | --- |
| Cold model load, build, memory y >=30 muestras p50/p95 | **PASS** |
| Hardware/CPU, SO, versiones, chunks, repeticiones y datos crudos | **PASS** |
| Escalado sintético 12/100/1000 reproducible | **PASS** |
| Alternativa A/B frente a baseline fijo | **PASS** |
| Deltas por consulta y holdout sin contaminar | **PASS** |
| Adoptar solo evidencia robusta, resultado negativo válido | **PASS: B descartado** |
| Revisión humana de qrels G3, aprobación/merge de Ricardo | **PENDING / BLOQUEANTE para gate** |

**G4 no está formalmente aprobado** mientras G3 y la auditoría externa permanezcan pendientes. El informe técnico se asocia al SHA de CI citado; repetir la validación al modificar la rama.
