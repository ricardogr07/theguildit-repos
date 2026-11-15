# G2 — Reproducción del baseline real: Definition of Done

**Issue:** [#6](https://github.com/ricardogr07/theguildit-repos/issues/6) · **PR:** [#12](https://github.com/ricardogr07/theguildit-repos/pull/12)  
**Estado técnico:** PASS (6/6) sobre el commit de ejecución; pendiente de revisión y merge por el responsable.  
**Commit realmente evaluado:** `8b0d1e73c40486430e00f199658563be6b03b410`.  
**Evidencia:** [G2_EVIDENCE_MANIFEST.json](G2_EVIDENCE_MANIFEST.json).

## Ejecución con modelo real

**Workflow:** [G2 Real Model Baseline, run #1](https://github.com/ricardogr07/theguildit-repos/actions/runs/43674293457), finalizado correctamente.  
**Artefacto descargable:** [baseline_real.json, resumen y logs](https://github.com/ricardogr07/theguildit-repos/actions/runs/43674293457/artifacts/14145414073).

El job instaló el extra `semantic` con `uv sync --locked --extra semantic --python 3.11`; usó un checkout exacto del head del PR, modelo multilingüe fijado por revisión, ejecución CPU, corpus sintético de 12 notas y 4 consultas originales. El modelo **no fue simulado**.

- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Revisión: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`
- Python: 3.11.18
- Dependencias: sentence-transformers 6.2.0, transformers 5.21.0, torch 2.14.1, numpy 2.4.6
- Corpus: 12/12 notas con SHA-256 idénticos al reporte histórico; índice: 22 chunks; 12 notas únicas recuperadas por pregunta.
- Lockfile SHA-256: `06c33f6b484dea191115e7d124cb204a79ac12f5c6cd4382093de01237ea48c1`

## Resultados por consulta

| Consulta abreviada | Target | Rank actual | Distractor | Rank distractor | PASS histórico |
| --- | --- | ---: | --- | ---: | --- |
| Usar funciones de otras aplicaciones | mcp.md | 5 | contenedores.md | 1 | FAIL |
| Encontrar con otras palabras | busqueda-semantica.md | 1 | busqueda.md | 3 | PASS |
| Evitar perder final de apunte largo | fragmentos.md | 1 | bitacora-de-incidente.md | 2 | PASS |
| Controlar documentos fuera del vault | rutas-seguras.md | 3 | datos-y-privacidad.md | 2 | FAIL |

| Métrica | Histórico (calculado) | Corrida G2 real |
| --- | ---: | ---: |
| Criterio legado PASS | 2/4 | 2/4 |
| Recall@3 (una etiqueta relevante) | 0.75 | 0.75 |
| Recall@5 (una etiqueta relevante) | 1.00 | 1.00 |
| MRR@10 (una etiqueta relevante) | ~0.6333 | ~0.6333 |

**Los ranks del objetivo y del distractor coinciden exactamente con el registro histórico.** El cálculo independiente desde el JSON completo pasó (`Independent G2 verification: PASS`). La evidencia contiene top-10 documentos por pregunta con scores, top-12 completo y resultados por chunk. No hubo truncamiento: 22 hits por consulta, menos del límite 50.

## Correctness / CI

- [CI estándar 5/5](https://github.com/ricardogr07/theguildit-repos/actions/runs/43674293471): 57 tests descubiertos, Linux 56 PASS + 1 SKIP de Windows, Windows 57 PASS, wheel 56 PASS + 1 SKIP.
- [CI modelo real](https://github.com/ricardogr07/theguildit-repos/actions/runs/43674293457): instalación con lockfile, 57 tests, modelo real, verificador independiente y subida de los cuatro archivos de evidencia.
- `verify_g2_baseline.py` vuelve a calcular ranking, puntuaciones, posiciones, PASS, Recall y MRR y comprueba hashes de código, lockfile y corpus contra el checkout.

## Definition of Done #6

| Criterio | Resultado | Evidencia |
| --- | --- | --- |
| Corrida del modelo real en entorno limpio fijado | **PASS** | G2 Actions, Python 3.11, extra semántico, CPU |
| 4 consultas originales y criterio legado intactos | **PASS** | Comparación estructural con JSON histórico, 2/4 |
| Top 10 notas con scores y estado de truncamiento | **PASS** | `baseline_real.json` incluido en artefacto |
| Recall@3/5 y RR@10 verificados de forma independiente | **PASS** | `verify_g2_baseline.py` y log PASS |
| SHA del código, hashes del corpus, versiones y ejecución | **PASS** | Metadata JSON y manifest de artefacto |
| Diferencias frente a histórico explícitas | **PASS** | Ranks idénticos; hashes de código diferentes |

## Límites y riesgos residuales

1. Los resultados describen **solo cuatro consultas y una etiqueta relevante por pregunta**. No demuestran generalización; la ampliación y revisión humana corresponde a G3.
2. El código de Sprint 1 no tiene los mismos SHA de `semantic.py`, `server.py` o `evaluate_semantic.py` del registro histórico; la ejecución real sí usa el commit G2 registrado. El ranking se mantuvo idéntico pese a los cambios.
3. Los artefactos de GitHub Actions tienen retención de **90 días**. Para evidencia permanente se conserva el hash de cada archivo en el manifiesto; G6 debe asegurar archivo durable antes del freeze.
4. G2 no midió tiempo, memoria p95 o desempeño a escala. Eso pertenece a G4.
5. El CI de un commit de documentación posterior no sustituye al benchmark original: debe confirmarse que la validación completa corre en el head final del PR.

**Decisión:** 6/6 criterios técnicos PASS para la corrida del modelo real. Issue #6 queda ABIERTO hasta revisión, CI del último commit y merge explícito por Ricardo. No iniciar G3 todavía.
