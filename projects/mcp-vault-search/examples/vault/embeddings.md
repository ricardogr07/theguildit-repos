# Vectores y embeddings

Un embedding transforma texto en un vector, una lista ordenada de números. Textos con significado parecido tienen vectores cercanos en el espacio matemático. El modelo que crea embeddings debe ser el mismo al crear el índice y al procesar la consulta.

La normalización lleva cada vector no nulo a longitud 1. Dos vectores normalizados pueden compararse multiplicando cada componente y sumando los resultados, operación llamada producto punto. El resultado equivale a la similitud coseno y puede variar entre -1 y 1. El puntaje sirve para ordenar candidatos y no expresa una probabilidad.

El servidor descarga un modelo preentrenado que entiende varios idiomas, incluido español. El mismo modelo resuelve todas las consultas hasta que se reconstruye el índice o se reinicia el servidor.
