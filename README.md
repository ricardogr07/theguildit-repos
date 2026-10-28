# Guild IT Repositories

Colección de proyectos open source y tutoriales de Guild IT.

## Proyectos

### mcp-vault-search

Servidor MCP local para buscar y leer notas Markdown con límites explícitos de acceso y salida. Los resultados pueden enviarse al proveedor del modelo que use el cliente.

- **Estado:** En desarrollo
- **Código y configuración:** [projects/mcp-vault-search](projects/mcp-vault-search/)
- **Tutorial:** `../theguildit-content/tutoriales/mcp-servidor-busqueda-vault/`

## Setup

```bash
git clone https://github.com/ricardogr07/theguildit-repos.git
cd theguildit-repos
cd projects/mcp-vault-search
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

## Licencia

MIT
