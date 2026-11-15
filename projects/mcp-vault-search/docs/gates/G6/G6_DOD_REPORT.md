# G6 — Definition of Done y control de freeze

**Issue:** [#10](https://github.com/ricardogr07/theguildit-repos/issues/10) · **PR:** [#16](https://github.com/ricardogr07/theguildit-repos/pull/16)  
**Estado:** RELEASE GUARD IMPLEMENTADO/PROBADO, **G6 BLOQUEADO**; no tag y no Docker branch creados.

## Pruebas técnicas

- [CI estándar G6](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717546400): cinco jobs exitosos, 101 tests descubiertos (Windows, Linux, wheel).
- [G6 release preflight](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717546387): CI SUCCESS, 101 tests.
- El comando `python -m scripts.check_release_gate` retorna **exit code 2** porque faltan requisitos obligatorios. El job verifica explícitamente que ese rechazo ocurra; `eligible=false` es el comportamiento **correcto**, NO una aprobación.
- `tests/test_g6_release_gate.py` incluye fixtures sintéticos positivos y negativos. La aprobación ficticia de test no significa una aprobación real.
- `docs/gates/G6/RELEASE_MANIFEST.json` es una **plantilla BLOCKED**. Exigir all PRs mergeados, SHA final, firma del owner, firma de un revisor distinto, 24 qrels revisadas y 0 defectos HIGH/CRITICAL.

## DoD de Issue #10

| Criterio | Estado |
| --- | --- |
| Todas las evidencias G0–G5 y 0 defects HIGH/CRITICAL | **PENDING review G3/G5** |
| README de límites y reindexación | Documentado; necesita verificación final del owner |
| CI y modelo real sobre commit integrado definitivo | **PENDING merges #13–#16** |
| Aprobación explícita del responsable | **PENDING** |
| Crear tag inmutable `tutorial-2-stable` | **NO REALIZADO** |
| Manifest final, evidencia durable y rollback | Plantilla y plan preparados; artefacto final externo pendiente |
| Abrir `codex/tutorial-3-docker` DESDE tag | **NO REALIZADO** |

## Condiciones innegociables para cerrar G6

1. Otro agente revisa las 24 qrels de G3 contra las 12 notas y registra nombre/fecha y discrepancias. Las qrels propuestas NO equivalen a revisión independiente.
2. Otro agente hace G5 completo: pruebas nuevas, revisión de diffs, hallazgos y dictamen por SHA, con cero CRITICAL/HIGH abiertos.
3. Ricardo fusiona #13–#16 **en orden hacia `codex/mcp-vault-colab`**, ajustando la base del PR siguiente a la rama de integración después de cada merge (ver [G6_RELEASE_PLAN.md](G6_RELEASE_PLAN.md)).
4. Ejecutar sobre el commit integrado la suite, G2 real y verificadores; documentar hashes y artefactos durables, no solo temporales de Actions.
5. Crear manifest final **externo** con el SHA verificado después del merge #16; ejecutar el validador. El control es una comprobación mecánica y no puede autenticar por sí solo que identidades o links de GitHub sean reales: la aprobación y los merges se cotejan externamente.
6. Solo entonces el owner publica `tutorial-2-stable` y crea `codex/tutorial-3-docker` **desde el tag**; sin mezclar cambios semánticos pendientes.

**Dictamen actual: G6 NO APROBADO**. Nunca anunciar un checkpoint estable por un preflight verde diseñado para rechazar un manifiesto incompleto.
