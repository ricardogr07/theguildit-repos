# Vectores y embeddings

Un embedding transforma texto en un vector, una lista ordenada de números. Textos con significado parecido tienen vectores cercanos en el espacio matemático. El modelo que crea embeddings debe ser el mismo al crear el índice y al procesar la consulta.

La normalización convierte un vector al rango de -1 a 1. Dos vectores normalizados pueden compararse rápidamente multiplicando cada componente y sumando los resultados, operación llamada producto punto. Este número entre 0 y 1 es el puntaje de similitud coseno.

El servidor descarga un modelo preentrenado que entiende varios idiomas, incluido español. El mismo modelo resuelve todas las consultas hasta que se reconstruye el índice o se reinicia el servidor.
