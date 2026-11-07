# División en fragmentos

Dividir una nota larga en fragmentos menores mejora la búsqueda semántica. El modelo procesa cada fragmento como una unidad independiente, permitiendo que un párrafo al final de una nota larga aparezca en los resultados sin indexar la nota completa.

Un fragmento puede exceder el límite de caracteres si un párrafo individual es muy largo. El servidor registra la ruta relativa y el rango de líneas de cada fragmento, permitiendo que el cliente abra el fragmento exacto con la herramienta de lectura.

Para evitar truncar contenido valioso, el servidor respeta los límites de párrafos. Un párrafo de mil caracteres permanece intacto aunque el fragmento exceda el límite establecido.
