# División en fragmentos

Dividir una nota larga en fragmentos menores mejora la búsqueda semántica. El modelo procesa cada fragmento como una unidad independiente, permitiendo que un párrafo al final de una nota larga aparezca en los resultados sin indexar la nota completa.

Un párrafo largo se divide para respetar los límites de caracteres y de tokens del modelo, incluidos los tokens especiales. El servidor registra la ruta relativa y las líneas de inicio y fin de cada fragmento. El cliente puede abrir la nota con la herramienta de lectura y ubicar el fragmento en esas líneas.

Los cortes aprovechan los espacios entre palabras cuando es posible. Si una sola palabra excede el presupuesto disponible, también se divide para que el modelo pueda procesar el texto completo en varios fragmentos.
