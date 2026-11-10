# Análisis de recuperación del corpus sintético

## Evidencia histórica

El checkpoint `f6fd8e2` conserva la corrida de `evaluate_semantic_results.json`, con dos consultas aprobadas de cuatro bajo el criterio original. El objetivo debe aparecer entre las tres primeras notas distintas y por encima del distractor designado.

| Consulta | Objetivo | Posición histórica | Distractor | Posición histórica |
| --- | --- | --- | --- | --- |
| Usar funciones de otras aplicaciones | `mcp.md` | 6 | `contenedores.md` | 1 |
| Encontrar algo escrito con otras palabras | `busqueda-semantica.md` | 1 | `busqueda.md` | 2 |
| Recuperar la parte final de una nota larga | `fragmentos.md` | 1 | `bitacora-de-incidente.md` | 2 |
| Restringir acceso fuera de una carpeta | `rutas-seguras.md` | 4 | `datos-y-privacidad.md` | 3 |

## Interpretación y revisión humana

La nota `mcp.md` es más breve que varias notas del corpus. Esa diferencia podría influir en los resultados, pero la corrida disponible no permite aislar su efecto. También puede influir la representación del modelo, la fragmentación y la superposición temática. El tamaño de las notas se registra como observación y su efecto sobre el ranking permanece como hipótesis.

Ricardo confirmó revisar `mcp.md` y `herramientas-mcp.md` como respuestas relevantes a la consulta 1. La evaluación conserva `mcp.md` como objetivo original para que los resultados se puedan comparar. Una revisión de etiquetas se registrará por separado.

Para la consulta 4 se mantiene `rutas-seguras.md` como objetivo. La pregunta trata de acceso a archivos fuera de una carpeta. `datos-y-privacidad.md` desarrolla principalmente la transmisión de fragmentos al proveedor del cliente. Que el distractor aparezca antes revela una limitación en este caso de recuperación, sin demostrar su causa.

## Correcciones del checkpoint

Las correcciones de huella y posición de líneas cambian la implementación. Las correcciones factuales sobre MCP, embeddings y división de notas cambian la versión del corpus. Se mantienen las doce notas y las cuatro consultas originales.

La nueva corrida se guarda en `evaluate_semantic_results_checkpoint_fixes.json`. El reporte registra la revisión exacta del modelo, las versiones de ejecución y las huellas del código y del corpus. Los archivos de corridas anteriores conservan sus resultados históricos.

| Consulta | Posición nueva del objetivo | Posición nueva del distractor | Resultado |
| --- | --- | --- | --- |
| Usar funciones de otras aplicaciones | 5 | 1 | Falla |
| Encontrar algo escrito con otras palabras | 1 | 3 | Pasa |
| Recuperar la parte final de una nota larga | 1 | 2 | Pasa |
| Restringir acceso fuera de una carpeta | 3 | 2 | Falla |

La corrida nueva mantiene 2/4 con las etiquetas originales. Estos cambios de posición corresponden a las correcciones del código y del texto. La corrida disponible no aísla la contribución individual de cada cambio.

La expansión del corpus queda pendiente de revisión humana. La evaluación sobre doce notas describe este conjunto de ejemplos. Se conservarán también los casos fallidos al redactar el tutorial.
