# G5 — Adversarial replay and independent-review package

**Issue:** [#9](https://github.com/ricardogr07/theguildit-repos/issues/9) · **PR:** [#15](https://github.com/ricardogr07/theguildit-repos/pull/15)  
**Estado:** pruebas adversariales automatizadas PASS; **revisión por un segundo agente/persona PENDING**, gate no aprobado.  
**Evidencia automatizada:** [G5 adversarial replay](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717392641), [artefacto y logs](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717392641/artifacts/14162002836), [CI estándar](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717392791).

## Ataques implementados
- Reconstrucción positiva de un reporte G2 coherente a partir del histórico.
- Corrupción intencional de top-10, Recall por consulta y hash de lockfile, todas rechazadas.
- Score NaN manipulado, rechazado.
- Intento de marcar una qrel como `approved` sin revisor ni fecha, rechazado.
- Pregunta OOD: no asignar Recall artificial.
- Endurecimiento adicional: `.gitattributes` fuerza LF para notas/código y evita variaciones de SHA-256 en checkouts Windows; descubierto por un fallo adversarial real y corregido.

## CI verificable
- [Suite estándar de G5](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717392791): **5/5 jobs success**, 91 pruebas descubiertas, sin fallos (Windows/Linux y wheel).
- [Replay real](https://github.com/ricardogr07/theguildit-repos/actions/runs/43717392641): **91 pruebas**, G2 real reejecutado con 2/4 y Recall@3=0.75; cálculo independiente PASS.
- La evaluación G3 de desarrollo también fue rehecha con modelo real: Recall@3=0.8333333 sobre etiquetas propuestas, auditoría independiente PASS; holdout NO ejecutado.
- Los logs contienen errores provocados intencionalmente; los procesos permanecen operativos y los jobs terminan en SUCCESS.

## Matriz de riesgos para revisión externa

| Hallazgo | Severidad provisional | Resolución/mitigación |
| --- | --- | --- |
| 24 qrels de G3 todavía propuestas | **BLOQUEANTE** | Otra persona/agente debe revisar 24 consultas contra las 12 notas |
| A/B de G4 todavía condicionado a las qrels | Media | B descartado; producción A no cambia |
| Ausencia de abstención en preguntas sin respuesta | Media | Reportar forced-hit/abstención por separado, sin falsa precisión |
| Rutas locales no garantizan aislamiento OS ni TOCTOU fuerte | Media | Vault pequeño/controlado, no afirmar seguridad remota/multiusuario |
| Reindexación manual necesaria ante notas nuevas/editadas | Baja en uso local | Documentación G1; reconstruir/reiniciar |
| Artefactos de CI caducan tras 90 días | Media | Registrar hashes y archivarlos durablemente antes de G6 |
| p95 solo 32 mediciones y corpus sintético repetido | Media | Reportar valores diagnósticos, no SLA |

- Tras revisión de Codex, los tests del holdout usan fixtures autocontenidas y el verificador A/B comprueba IDs de desarrollo y decisiones de aceptación, sin depender de las qrels aprobadas futuras.

## Petición al revisor **independiente**

1. Inspeccionar código y diffs de #13, #14, #15, no simplemente este reporte.
2. Ejecutar **tres ataques NUEVOS** distintos de los que escribió el implementador y documentar cómo intentó romper el sistema.
3. Recalcular a mano o por segunda implementación los resultados agregados, con especial cuidado en qrels de relevancia múltiple y OOD.
4. Revisar las 24 relevancias propuestas contra las 12 notas, incluidas D02/D08/D14/D16/H05 y tres OOD; registrar discrepancias.
5. Confirmar que el holdout no se usó para seleccionar ranking o pesos.
6. Clasificar hallazgos CRITICAL/HIGH/MEDIUM/LOW y asociar pasos de reproducción, código/línea, mitigación y aprobación.
7. Firmar con identificador y SHA exacto; modificaciones funcionales posteriores requieren revalidación.

## DoD G5

| Condición | Estado |
| --- | --- |
| Suite, G2 real, G3 dev, >=3 casos adversariales automáticos | **PASS (implementador + CI)** |
| Revisor diferente inspecciona los diffs | **PENDING** |
| >=3 ataques nuevos de revisor externo | **PENDING** |
| Hallazgos formalmente clasificados, cero CRITICAL/HIGH abiertos | **NO CERTIFICADO** |
| Riesgos medios aceptados con owner/seguimiento | **PENDING** |
| Dictamen firmado del reviewer sobre SHA final | **PENDING** |

**Dictamen: G5 BLOQUEADO para freeze.** La prueba adversarial automatizada no es una auditoría independiente, aunque haya 91 tests en verde.
