# Demo semántica en Colab

[Abrir el notebook en Colab](https://colab.research.google.com/github/ricardogr07/theguildit-repos/blob/codex/mcp-vault-colab/projects/mcp-vault-search/notebooks/semantic_search.ipynb)

El notebook descarga el código y las doce notas sintéticas del commit `eb62f5d69b42a069bb4fde4c32fe918ac37a28ca`. Utiliza el evaluador de ese checkout y el modelo multilingüe de revisión `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.

## Ejecutar

1. Abrir el enlace de Colab e iniciar sesión si el servicio lo solicita.
2. Seleccionar un runtime nuevo con CPU.
3. Ejecutar las celdas en orden desde el principio. La instalación prepara Python 3.11 y un entorno del proyecto mediante `uv==0.10.4` y `uv sync --locked --extra semantic`.
4. Revisar las cuatro consultas y la tabla que compara las posiciones actuales con la corrida de referencia.
5. Descargar `evaluate_semantic_results_colab.json` desde la carpeta temporal mostrada por el notebook.

La primera instalación necesita acceso a GitHub, PyPI y los pesos del modelo. El lockfile de Linux incluye bibliotecas CUDA aunque la inferencia se ejecute en CPU. La descarga puede ser grande. Las ejecuciones posteriores pueden reutilizar la caché del runtime.

## Qué comprobar

- El commit descargado debe ser exactamente `eb62f5d69b42a069bb4fde4c32fe918ac37a28ca`.
- El corpus contiene doce notas y el reporte registra la revisión fija del modelo.
- El máximo de tokens de los fragmentos debe respetar el límite de 128, incluidos los tokens especiales.
- La tabla conserva las cuatro consultas, los objetivos y los distractores originales, incluidos los fallos. La corrida de referencia incluida en el checkpoint logró 2/4.
- El fragmento inspeccionado debe encontrarse dentro de las líneas indicadas de la nota original.
- Las huellas del reporte deben coincidir con los archivos usados en la ejecución. Los finales de línea de un checkout en Windows pueden dar huellas distintas de las de Linux.

## Estado de verificación

El 2026-11-10 se publicó la rama del checkpoint. Se comprobó sin credenciales el acceso HTTP 200 al commit y a diecisiete archivos, incluidos el código, el lockfile y las doce notas. Los archivos descargados coinciden con los objetos Git del commit.

El notebook pasó la validación de formato y se ejecutaron sus siete celdas completas en un kernel temporal de Jupyter en Windows. Esa prueba descargó un checkout nuevo del commit público, preparó su entorno con el lockfile y utilizó los pesos fijados disponibles en caché. Se observaron 2/4 consultas aprobadas, 22 fragmentos y un máximo de 121 tokens. Las comprobaciones de líneas y huellas terminaron correctamente.

La ejecución completa en un runtime limpio de Colab queda pendiente de verificación. La vista de Colab disponible en esta sesión solicita iniciar sesión. El notebook utiliza el corpus público y explora indexación y ranking. La conexión MCP al cliente corresponde al recorrido local del tutorial.
