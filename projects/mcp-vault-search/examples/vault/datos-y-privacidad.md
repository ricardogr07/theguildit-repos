# Datos, privacidad y fragmentos

El servidor ejecuta el modelo de embeddings en el equipo local, sin enviar notas a internet. El cliente recibe fragmentos de texto, líneas indexadas o contenido completo según la herramienta, y puede decidir qué hacer con ellos.

El servidor no impide que el cliente envíe fragmentos a su proveedor de IA. Una nota privada almacenada localmente puede procesarse por un servicio remoto si el cliente lo elige. Revisa la política de privacidad de tu cliente antes de usar notas sensibles.

Los fragmentos devueltos están limitados a 500 caracteres en búsqueda semántica y 20 mil caracteres en lectura de nota completa. Estos límites aplican solo a lo que devuelve el servidor; no garantizan aislamiento de datos en la máquina del cliente.
