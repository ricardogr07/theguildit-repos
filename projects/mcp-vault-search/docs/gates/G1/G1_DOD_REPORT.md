# G1 — Definition of Done y aprobación técnica

**Issue:** [#5](https://github.com/ricardogr07/theguildit-repos/issues/5) · **PR:** [#11](https://github.com/ricardogr07/theguildit-repos/pull/11)  
**Estado:** IMPLEMENTACIÓN Y PRUEBAS APROBADAS; REVISIÓN Y MERGE DEL RESPONSABLE PENDIENTES  
**Fecha del registro:** 2026-11-14  
**Base de PR:** `codex/mcp-vault-colab`, SHA `98cc296a11d058f79b9d41e5699f8d06381339f7`.  
**Rama:** `codex/g1-semantic-correctness`.

## Cambios introducidos

1. `semantic.py`: validación del número de embeddings, dimensión entre chunks y consulta, números finitos y norma L2 aproximadamente igual a 1; rechaza índices vacíos y corruptos.
2. `server.py`: valida solicitudes antes de cargar el modelo; oculta el detalle de excepciones inesperadas y de errores de embeddings, mientras mantiene diagnósticos en `stderr`.
3. `evaluate_semantic.py`: error de importación finaliza con código no exitoso; fallos del corpus o modelo tampoco se silencian.
4. `tests/test_g1_validation.py`: **12 pruebas nuevas** para valores inválidos, chunking, índice, reindexación y errores del evaluador.
5. `tests/test_server.py`: casos de error de ejecución y vector malformado con verificación de que el proceso MCP sigue atendiendo solicitudes.
6. README: comportamiento de reindexación e instrucciones para no sobrescribir archivos históricos.

## CI y evidencia

[GitHub Actions, run #46](https://github.com/ricardogr07/theguildit-repos/actions/runs/43672528222), ejecutado para el código en SHA `25c37c2174a5a74d677beb21bb7a590b4cf9afe8`.

| Plataforma / job | Tests descubiertos | Passed | Skipped | Job |
| --- | ---: | ---: | ---: | --- |
| Ubuntu, Python 3.11 | 51 | 50 | 1 | SUCCESS |
| Ubuntu, Python 3.12 | 51 | 50 | 1 | SUCCESS |
| Windows, Python 3.11 | 51 | 51 | 0 | SUCCESS |
| Windows, Python 3.12 | 51 | 51 | 0 | SUCCESS |
| Wheel instalado, Ubuntu Python 3.12 | 51 | 50 | 1 | SUCCESS |

El skip único es la prueba de junction de Windows ejecutándose en Linux. Se ejecutaron pruebas del proceso `stdio` con modelo simulado; no se certifica la calidad del modelo real, que pertenece a G2. El mensaje ERROR de los logs corresponde a un fallo provocado a propósito para comprobar manejo y recuperación de sesiones.

## Definition of Done del Issue #5

| Criterio | Dictamen técnico | Evidencia |
| --- | --- | --- |
| Evaluador devuelve estado no exitoso para dependencia, corpus o modelo indisponibles | **PASS** | 3 pruebas negativas del evaluador |
| Validación de embeddings vacíos, NaN/Inf, normas y dimensiones | **PASS** | `test_g1_validation.py` |
| Pruebas de chunking, índice vacío, consulta y límites inválidos | **PASS** | `test_g1_validation.py` y `test_semantic.py` |
| Rutas, symlinks/junctions, UTF-8, notas editadas/borradas y fallos parciales | **PASS** | `test_vault.py`, `test_semantic.py`, `test_server.py` |
| Contratos `search_notes`, `read_note`, `search_semantic` y recuperación después de errores | **PASS** | `test_server.py` por proceso `stdio` |
| CI Linux/Windows Python 3.11/3.12 y empaquetado | **PASS** | Cinco jobs exitosos y conteos conciliados del run #46 |
| Reindexación pospuesta documentada | **PASS** | README y G1_TEST_MATRIX.md |

## Restricciones y riesgos residuales

- No hay mecanismo automático para incorporar notas nuevas o editadas: hay que reiniciar el proceso para reconstruir el índice. Las notas modificadas se excluyen hasta entonces.
- La indexación sigue cargando notas completas en memoria. No hay presupuesto duro para el tamaño de una colección: destinado a vaults locales pequeños y controlados.
- Las comprobaciones de rutas no son un sandbox del sistema operativo y no garantizan ausencia de carreras con cambios hostiles concurrentes.
- Los vectores se validan también durante las consultas, lo que añade una operación lineal por chunk/dimensión; medir su impacto real corresponde a G4.
- La calidad de recuperación con el modelo real es **NO EVALUADA EN G1**. Se medirá en G2.
- Este documento se incorporó tras el SHA funcional auditado: verificar el CI del commit final de documentación antes de solicitar el merge.

## Gate y autorización

**Implementación y criterios técnicos: PASS (7/7), condicionados a CI del head final.**

**El Issue #5 permanece ABIERTO** hasta que Ricardo revise y haga merge del PR #11, confirme que el último SHA tiene CI correcto y registre el cierre. No se inicia G2 antes de ese cierre. El Issue padre #2 permanece abierto.

Matriz de evidencia: [G1_TEST_MATRIX.md](G1_TEST_MATRIX.md).
