# Ejemplo: bitácora de incidente

Se reportó un aumento en la latencia de búsqueda desde las 14:30. El servidor comenzó a responder lentamente tras recibir tres mil consultas consecutivas. Se recompilaron los índices y los tiempos regresaron a lo normal después del reinicio.

El patrón sugiere que el índice en memoria creció más allá de lo esperado. Se verificó que el vault contenía notas nuevas que no habían sido reindexadas. Tras borrar datos obsoletos y reconstruir el índice, el rendimiento se estabilizó.

Para futuras sesiones, se configuró un alerta si la construcción del índice excede cinco segundos. Esta bitácora documenta el procedimiento de diagnóstico que el operador puede repetir si el problema vuelve a ocurrir.
