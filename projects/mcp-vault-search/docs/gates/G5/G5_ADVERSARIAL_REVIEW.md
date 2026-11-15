# G5 — Adversarial verification / independent review

**Issue:** [#9](https://github.com/ricardogr07/theguildit-repos/issues/9) · **Estado:** revisión independiente pendiente.

## Paquete de reproducción y ataque

La siguiente evidencia es **automática y escrita por el implementador**. No sustituye la revisión de otro agente/persona.

- `tests/test_g5_adversarial.py` reconstruye un reporte G2 válido a partir de hits históricos para confirmar que el verificador acepta datos coherentes.
- Se alteran deliberadamente **top-10, Recall por consulta, hash de lockfile y score NaN**; cada corrupción debe producir un error comprobable.
- Se intenta autoaprobar una qrel sin revisor ni fecha: el validador debe impedirlo.
- Las consultas sin respuesta pertinente no se convierten artificialmente a Recall 0.
- El CI G5 vuelve a ejecutar el modelo real con las cuatro consultas históricas y las 16 de desarrollo; compara las métricas con verificadores que leen resultados guardados.
- Se reserva el holdout; ningún test de calidad usa sus resultados.

## Hallazgos y riesgos que se entregan al revisor

| Riesgo | Severidad preliminar | Estado / mitigación |
| --- | --- | --- |
| 24 qrels todavía propuestas sin validación humana | **Gate blocker** | Solicitar revisión de cada nota para cada query en PR #13 |
| Comparación A/B sobre qrels provisionales | Media / Gate blocker para promover B | Mantener producción A; no decidir con este benchmark |
| Modelo siempre entrega una nota incluso en consultas OOD | Media | Registrar forced-hit como 100 % cuando ocurre; diseñar abstención como trabajo posterior |
| Comprobación de rutas no equivale a sandbox resistente a cambios concurrentes hostiles | Media | Mantener uso de vault local controlado, volúmenes de solo lectura en Docker |
| Índice de memoria no se actualiza automáticamente | Baja en tutorial local / mayor en servicio continuo | Reinicio o reindexación, documentado en G1 |
| Corridas y JSON en artefactos GitHub de 90 días | Media para auditabilidad a largo plazo | Archivar evidencias durables antes de G6 |
| Estudios p95 con 32 mediciones y corpus copiado | Media para extrapolación | Reportar alcance diagnóstico, no SLA |

## Solicitud al revisor independiente

1. Revisar los diffs de PRs #13, #14 y #15 con una actitud adversarial. Reconstruir resultados desde un checkout limpio.
2. Recalcular a mano o en código independiente la media por consulta de Recall@3/5, Precision@3 y MRR@10; verificar que OOD queda fuera del denominador.
3. Ejecutar tres o más ataques nuevos fuera de los tests publicados (ej.: reemplazar un archivo por symlink al correr, forzar truncamiento de 50 chunks, manipular un hash).
4. Leer las 12 notas y todas las qrels: documentar falsos positivos/negativos y discrepancias de relevancia.
5. Clasificar cada defecto CRITICAL/HIGH/MEDIUM/LOW con archivo/línea, pasos y resolución. **Solo el revisor debe marcar su aprobación.**
6. Verificar que ningún cambio del paquete altera contratos MCP, y que el holdout no fue usado para tuning.
7. Firmar el dictamen con identificador de revisor y commit exacto. Si se cambia código después, revalidar lo afectado.

## Gate G5 Definition of Done

| Criterio | Estado |
| --- | --- |
| Revisión de diffs por revisor diferente del implementador | **PENDING** |
| Suite, benchmark histórico, métricas y ≥3 ataques reprodu­cidos | Implementado en CI; pendiente de verificar resultados |
| Hallazgos clasificados con trazabilidad y reproducción | **PENDING** revisor independiente |
| Cero CRITICAL/HIGH abiertos | **NO CERTIFICADO** |
| MEDIUM aceptados con propietario, mitigación y seguimiento | PENDING |
| Dictamen independiente sobre SHA final | **PENDING** |

**No declarar PASS de G5 ni congelar un tag estable antes de obtener la revisión independiente.** El PR está abierto para comentarios.
