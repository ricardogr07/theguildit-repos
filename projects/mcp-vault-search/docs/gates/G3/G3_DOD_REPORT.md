# G3 — Definition of Done y evaluación preliminar

**Issue:** [#7](https://github.com/ricardogr07/theguildit-repos/issues/7) · **PR:** [#13](https://github.com/ricardogr07/theguildit-repos/pull/13)  
**Estado técnico:** IMPLEMENTADO / CI PASS; **GATE PENDING revisión humana de relevancias**.  
**Evidencia:** [G3 workflow run](https://github.com/ricardogr07/theguildit-repos/actions/runs/43714720353), [artefacto JSON y logs](https://github.com/ricardogr07/theguildit-repos/actions/runs/43714720353/artifacts/14162530262).

## Dataset
- Se conservaron intactas las 4 preguntas históricas.
- 24 consultas nuevas: 16 de desarrollo y 8 holdout no ejecutadas.
- Español, inglés, términos mixtos, distractores, ambigüedad, 5 consultas con varias notas candidatas y 3 preguntas sin respuesta pertinente.
- Las 24 qrels tienen razón editorial, pero su estado sigue siendo **proposed** (revisor/fecha nulos). El corpus está congelado en 12 notas.

## Evidencia técnica de la corrida real (provisional)

- Python 3.11 y modelo multilingüe fijado por revisión.
- [CI estándar](https://github.com/ricardogr07/theguildit-repos/actions/runs/43714720286): 5/5 jobs correctos, **70 pruebas** descubiertas.
- [Benchmark de desarrollo](https://github.com/ricardogr07/theguildit-repos/actions/runs/43714720353): SUCCESS; verificación independiente del JSON = PASS.
- Macro de 15 consultas con relevancia propuesta: Recall@3 **0.8333333**, Recall@5 **0.8666667**, Precision@3 **0.3333333**, MRR@10 **0.8111111**.
- Consulta OOD en desarrollo: tasa de forced-hit **1.0** y abstención **0.0**, porque el buscador actual no tiene umbral para abstenerse.
- nDCG@5 **no calculado**: se necesitan etiquetas graduadas para reportarlo como previsto en el DoD.
- No se usaron resultados del holdout para entrenamiento, selección ni ajustes. **Los archivos holdout son visibles en Git**: aislamiento de procedimiento, no secreto criptográfico.

## DoD del Issue #7

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| >=20 consultas nuevas y 4 históricas separadas | **PASS** | Archivos evaluation/*.json |
| Paráfrasis, idiomas, distractores, multi-relevante y OOD | **PASS** | Dataset de 24 propuestas |
| Qrels 0/1/varias revisadas humanamente con desacuerdos documentados | **PENDING / BLOQUEANTE** | Solicitar revisión independiente de las 24 etiquetas, con nombre y fecha |
| Desarrollo/holdout separados, sin usar holdout para tuning | **PASS con reserva** | Evaluador exige permiso explícito y bloquea holdout no revisado |
| Métricas por consulta y agregadas | **PASS preliminar** | Corrida CPU y auditoría independiente, qrels no aprobadas |
| Protocolo OOD separado | **PASS** | Forced-hit/abstención, sin Recall artificial |

**Dictamen: 5/6 criterios técnicos verificados; G3 NO APROBADO.** Las métricas finales deben reejecutarse después de la revisión independiente. No mergear por automatismo ni liberar holdout.
