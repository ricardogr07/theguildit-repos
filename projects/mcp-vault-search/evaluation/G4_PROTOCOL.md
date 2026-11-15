# Protocolo G4: prueba de rendimiento y comparación reproducible

**Preinscrito antes de leer las cifras:** experimento A/B descrito en `G4_DOD_REPORT.md`. No ajustar este protocolo a posteriori para justificar B.

### Comandos
```bash
cd projects/mcp-vault-search
uv sync --locked --extra semantic --python 3.11
uv run --locked --extra semantic --python 3.11 python -m evaluation.experiment_g4 --warm-repetitions 32 --scale-counts 100 1000
uv run --locked --extra semantic --python 3.11 python -m evaluation.verify_g4
```

El runner carga una sola vez el modelo CPU fijado por revisión. Mide el tiempo de construir el índice de referencia y una batería de consultas warm. Para capacidad, genera copias UTF-8 deterministas de las 12 notas en un `TemporaryDirectory`, sin persistir datos ni cambiar el corpus de evaluación.

### Interpretación
- 32 muestras warm: adecuadas como diagnóstico, pero p95 tiene alta incertidumbre; no son SLA.
- La memoria máxima `ru_maxrss` es marca de máximo proceso desde inicio. Las tres mediciones de capacidad no separan memoria de modelo, caché y heap.
- Los 100/1000 documentos son duplicados artificiales: útil para throughput, inválido como estudio de calidad.
- No comparar carga fría con el modelo descargado vs cacheado sin documentarlo.
- Relevancias humanas pendientes: ninguna mejora puede fusionarse a `semantic.py` con estos resultados por sí sola.
- Las ocho consultas holdout permanecen reservadas; el script solo importa `development_queries.json`.
