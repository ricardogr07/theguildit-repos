# Índice local e instantáneas

El índice almacena vectores y fragmentos en memoria durante la sesión. No se guarda en disco; cada consulta usa los datos del índice actual. Para incorporar nuevas notas o cambios, el servidor debe reconstruir el índice desde los archivos.

Una instantánea criptográfica de cada nota permite detectar cuándo cambió su contenido. Antes de devolver un fragmento en los resultados, el servidor calcula una huella SHA-256 del contenido actual y la compara con la almacenada. Si no coinciden, el fragmento se descarta.

El índice se reconstruye automáticamente cuando se reinicia el servidor. Esta estrategia simple pero efectiva permite trabajar con vaults que cambian entre sesiones sin incurrir en persistencia en disco.
