# Búsqueda semántica

La búsqueda semántica recupera notas que expresan una idea con palabras distintas, no solo coincidencias exactas. Un vector de números representa el significado del texto, y la similitud entre vectores mide qué tan parecidas son dos ideas.

Si buscas "¿cómo hallo algo que escribí con otra redacción?", la búsqueda semántica puede encontrar notas sobre fragmentación o archivos aunque no contengan esas palabras exactas. El servidor calcula un puntaje de similitud entre 0 y 1.

Mantener una similitud razonable evita resultados demasiado generales. Un puntaje cercano a 1 indica que el significado del fragmento coincide estrechamente con la consulta. Un puntaje cercano a 0 sugiere que la asociación es débil.
