# Transporte por entrada y salida estándar

MCP sobre stdio permite que el cliente inicie el servidor como un proceso independiente. La comunicación ocurre exclusivamente por entrada y salida estándar, usando mensajes JSON codificados con longitud.

El servidor preserva stdout para mensajes MCP. Los diagnósticos y advertencias se escriben en stderr, permitiendo que herramientas de monitoreo o el operador los inspeccionen sin interferir en la comunicación con el cliente.

El servidor mantiene una conexión activa durante toda la sesión. Si el proceso termina de manera inesperada, el cliente lo reintenta según su configuración. Los mensajes en tránsito no se persisten; una desconexión inesperada puede perder datos de consultas en vuelo.
