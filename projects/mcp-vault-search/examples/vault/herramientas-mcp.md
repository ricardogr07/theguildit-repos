# Herramientas en MCP

El servidor MCP expone herramientas que el cliente puede descubrir y llamar. Cada herramienta tiene un nombre, descripción y parámetros tipados. El cliente enumera las herramientas disponibles sin activarlas; activa solo las que necesita.

El servidor de búsqueda ofrece `search_notes` para encontrar coincidencias literales y `read_note` para abrir una nota especificando su ruta relativa. Una herramienta adicional `search_semantic` recupera fragmentos por similitud cuando está habilitada mediante una variable de entorno.

Los parámetros de entrada son validados por el cliente antes de enviar la llamada. El servidor puede rechazar una llamada con un mensaje de error si los datos de entrada violan las restricciones.
