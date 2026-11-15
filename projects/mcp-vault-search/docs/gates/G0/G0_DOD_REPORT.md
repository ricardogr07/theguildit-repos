# G0 — Cierre de procedencia, trazabilidad y Definition of Done

**Estado del gate: PASS (4/4)**  
**Fecha:** 2026-11-14  
**Rama de evidencia:** `codex/g0-baseline-evidence`  
**Commit base auditado:** `4a0ceb46a5ae2a6daa8f15939bca44d6198272c4`  
**Manifiesto:** [BASELINE_MANIFEST.json](BASELINE_MANIFEST.json)

## Confirmación de los tutoriales publicados

El responsable del proyecto proporcionó fragmentos textuales de los comandos de instalación publicados en ambas partes. Ambos commits se comprobaron independientemente en el repositorio GitHub.

| Tutorial | Comando literal de selección | Commit GitHub |
| --- | --- | --- |
| Parte 1 | `git checkout 6fcf21268799c2280b7174e3427ac0438a7e50a8` | [6fcf212](https://github.com/ricardogr07/theguildit-repos/commit/6fcf21268799c2280b7174e3427ac0438a7e50a8) |
| Parte 2 | `git switch --detach eb62f5d69b42a069bb4fde4c32fe918ac37a28ca` | [eb62f5d](https://github.com/ricardogr07/theguildit-repos/commit/eb62f5d69b42a069bb4fde4c32fe918ac37a28ca) |

Artículo de la parte 2: https://theguildit.io/tutoriales/b%C3%BAsqueda-sem%C3%A1ntica-local-para-tu-servidor-mcp

**Alcance de verificación:** la página pública no se pudo recuperar automáticamente, pero sí se cotejaron los comandos exactos aportados por el autor contra commits y archivos reales. No se afirma haber verificado el HTML público independiente de esa evidencia.

## Hallazgos de trazabilidad

- El checkout de Parte 1 referencia el merge de hardening en `master`.
- La Parte 2 fija `eb62f5d` y utiliza `uv sync --locked --extra semantic --python 3.11`.
- `codex/mcp-vault-colab` agrega un commit al checkpoint semántico y aporta notebook/README.
- `codex/sprint-1-semantic-evaluation` agrega tres commits sobre Colab, referenciados en PR #3.
- Los 12 archivos Markdown sintéticos coinciden por SHA-256 con el reporte histórico.
- Los hashes del código actual de `semantic.py` y `evaluate_semantic.py` no coinciden con los registrados en el benchmark histórico. Por ello se necesita una nueva corrida en G2.
- Histórico: 4 consultas, 2/4 según criterio heredado, Recall@3=0.75 y MRR@10≈0.6333 con una sola etiqueta relevante.

## Definition of Done: dictamen formal

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| G0-1. Commits y estructura de ramas reconciliados | **PASS** | Comparaciones de master, checkpoint parte 2, Colab y PR #3 |
| G0-2. Dependencias, modelo y hashes de corpus registrados | **PASS** | Lockfile, revisión de modelo y 12/12 SHA-256 en el manifiesto |
| G0-3. Resultados históricos diferenciados de datos actuales | **PASS** | Metadata histórica y divergencias de código anotadas |
| G0-4. Artículo publicado enlazado a commit real | **PASS** | Fragmentos literales aportados por el autor y commits comprobados en GitHub |

**Resultado G0: 4/4 criterios satisfechos. Etapa aprobada.**

## Etiquetas de publicación propuestas

Se proponen etiquetas **anotadas** que no alteran los commits:

- `tutorial-1` → `6fcf21268799c2280b7174e3427ac0438a7e50a8`
- `tutorial-2` → `eb62f5d69b42a069bb4fde4c32fe918ac37a28ca`

**Estado: NO CREADAS.** La conexión GitHub de esta sesión no expone una operación para crear refs de etiquetas. Se deben comprobar refs existentes antes de publicar etiquetas. No mover una etiqueta publicada sin decisión explícita.

```bash
git fetch origin --tags
git ls-remote --tags origin 'refs/tags/tutorial-1' 'refs/tags/tutorial-2'
# Ejecutar solo si los nombres están libres:
git tag -a tutorial-1 6fcf21268799c2280b7174e3427ac0438a7e50a8 -m "MCP Vault Search: tutorial 1 published checkpoint"
git tag -a tutorial-2 eb62f5d69b42a069bb4fde4c32fe918ac37a28ca -m "MCP Vault Search: tutorial 2 published checkpoint"
git push origin refs/tags/tutorial-1 refs/tags/tutorial-2
```

## Límites de la aprobación

- El **PASS de G0** no implica aprobar PR #3, cerrar Sprint 1, hacer merge ni ejecutar G1.
- No se ha vuelto a ejecutar el modelo real; es trabajo de G2.
- Los tags no se crearon.
- G1 se debe iniciar como una etapa distinta, siguiendo la secuencia y sin mezclar modificaciones funcionales con G0.

## Referencias

- [G0 PR #4](https://github.com/ricardogr07/theguildit-repos/pull/4)
- [Sprint Issue #2](https://github.com/ricardogr07/theguildit-repos/issues/2)
- [Métricas PR #3](https://github.com/ricardogr07/theguildit-repos/pull/3)
