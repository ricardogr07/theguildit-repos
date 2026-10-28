# MCP Vault Search

Servidor MCP local para buscar y leer notas Markdown sin dar acceso fuera del directorio configurado.

Proyecto compañero de una serie de tutoriales en español para The Guild IT.

## Estado

Checkpoint de la parte 1: búsqueda literal y lectura segura. Búsqueda semántica y Docker llegan en checkpoints posteriores.

## Requisitos

- Python 3.10 o posterior.
- `uv`.
- Claude Desktop actualizado, si quieres conectar el servidor a un host real.

## Ejecutar

```powershell
uv sync
$env:VAULT_PATH = "examples/vault"
uv run mcp-vault-search
```

`stdout` queda reservado para mensajes MCP. Usa `logging`, que escribe en `stderr`, para diagnóstico.

## Probar

```powershell
uv run python -m unittest discover -s tests
uv run mcp dev src/mcp_vault_search/server.py
```

Herramientas:

- `search_notes(query, limit)`: busca texto literal y devuelve ruta, línea y fragmento.
- `read_note(path)`: lee un archivo Markdown usando una ruta relativa al vault.

## Claude Desktop

Ejemplo para Windows:

```json
{
  "mcpServers": {
    "vault-search": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/RUTA/ABSOLUTA/mcp-vault-search",
        "run",
        "mcp-vault-search"
      ],
      "env": {
        "VAULT_PATH": "C:/RUTA/ABSOLUTA/tu-vault"
      }
    }
  }
}
```

En Windows, la configuración vive en `%APPDATA%/Claude/claude_desktop_config.json`. Algunas instalaciones requieren la ruta absoluta de `uv`.

## Seguridad

- El servidor acepta solo rutas relativas con extensión `.md`.
- La ruta resuelta debe permanecer dentro del vault.
- La salida y cantidad de resultados están acotadas.
- Usa un vault sintético para pruebas. No publiques notas privadas.

## Cuándo no usarlo

No es un servidor remoto ni multiusuario. Tampoco reemplaza un motor de búsqueda para colecciones grandes. Para un vault personal pequeño, prioriza código local y revisable.

## Distribución

GitHub source y tags por tutorial son suficientes por ahora. PyPI y GHCR se agregarán solo si el uso real muestra esa necesidad.
