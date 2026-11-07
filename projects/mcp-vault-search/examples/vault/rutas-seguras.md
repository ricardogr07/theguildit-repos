# Validación de rutas

El servidor acepta solo rutas relativas con extensión `.md`. Las rutas absolutas y las que apunten fuera del vault son rechazadas. Esto evita que un cliente malintencionado lea archivos del sistema.

Los enlaces simbólicos y puntos de reanálisis de Windows son excluidos, incluso si apuntan a contenido dentro del vault. Esta restricción impide que archivos duplicados o accesos alternativos sean indexados.

La validación ocurre antes de abrir cualquier archivo. Si la ruta falla la validación, el servidor registra un diagnóstico en stderr y devuelve un error al cliente sin cargar el contenido.
