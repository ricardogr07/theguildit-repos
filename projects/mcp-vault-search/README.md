# MCP Vault Search

Servidor MCP local para construir una búsqueda controlable y reutilizable sobre notas Markdown.

Proyecto compañero de una serie de tutoriales en español para The Guild IT.

## Estado

Parte 1: búsqueda literal y lectura con validación de rutas. Las utilidades semánticas y el Dockerfile son preliminares; no hay una herramienta MCP semántica ni checkpoints publicados de las partes 2 y 3.

## Requisitos

- Python 3.11 o posterior. El lockfile fija MCP SDK 2.3.0; el paquete admite la serie 2 desde esa versión.
- `uv`.
- Claude Desktop o Codex, si quieres conectar el servidor a un cliente real.

## Ejecutar

```powershell
uv sync --locked
$env:VAULT_PATH = "examples/vault"
uv run --locked mcp-vault-search
```

`stdout` queda reservado para mensajes MCP. Usa `logging`, que escribe en `stderr`, para diagnóstico.

## Probar

```powershell
uv run --locked python -m unittest discover -s tests -v
uv build
```

Las pruebas incluyen un proceso real lanzado con el ejecutable instalado, inicialización MCP, listado, búsqueda, lectura y errores de herramientas. No requieren un modelo ni credenciales. Los casos de enlaces informan un `skip` si Windows no permite crearlos; Linux exige que funcionen. Las junctions se prueban solo en Windows.

Para comprobar el wheel sin la instalación editable:

```powershell
uv run --no-cache --isolated --no-project --with ./dist/mcp_vault_search-0.1.0-py3-none-any.whl python -m unittest discover -s tests -v
```

CI vive en `.github/workflows/mcp-vault-search.yml` en la raíz del monorepo. Ejecuta pruebas en Windows y Linux con Python 3.11 y 3.12, y comprueba el wheel por separado.

Opcionalmente, MCP Inspector permite una revisión interactiva:

```powershell
uv run --locked mcp dev src/mcp_vault_search/server.py
```

Requiere Node.js y `npx`; su interfaz usa puertos locales. La suite automática no necesita Inspector. No ejecutes `server.py` directamente: usa el ejecutable instalado.

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
        "--locked",
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

## Codex

Copia y adapta `examples/codex.config.toml.example` en tu `~/.codex/config.toml`. Usa rutas absolutas tanto para el proyecto como para `VAULT_PATH`. Si el cliente no encuentra `uv`, configura su ejecutable con ruta absoluta.

1. Empieza con `examples/vault`, que solo contiene notas sintéticas.
2. Comprueba el registro con `codex mcp list` y `codex mcp get vault_search`.
3. Abre una sesión nueva o recarga los servidores en tu cliente; verifica que aparezcan `search_notes` y `read_note`.
4. Pide buscar `MCP`, leer `mcp.md` y rechazar `../secret.md`.
5. Para uso editorial, cambia `VAULT_PATH` a la carpeta revisada del tutorial y repite una búsqueda y lectura conocidas. No apuntes a todo tu perfil ni a un vault privado por defecto.

Registrar la configuración no prueba que una conversación activa haya recargado las herramientas. Comprueba una llamada desde el cliente después de reconectar. La configuración personal queda fuera de Git.

Referencia: [configuración MCP de Codex](https://developers.openai.com/codex/mcp).

## Límites de acceso y datos

- El servidor acepta solo rutas relativas con extensión `.md`.
- La ruta resuelta debe permanecer dentro del vault.
- Se excluyen enlaces simbólicos y puntos de reanálisis de Windows, incluidas junctions, aunque apunten dentro del vault. La búsqueda y la indexación comparten esta exclusión.
- Solo se admiten notas UTF-8 con extensión `.md`, sin distinguir mayúsculas. La búsqueda omite archivos ilegibles y escribe el diagnóstico en `stderr`; una lectura solicitada devuelve un error explícito.
- La búsqueda devuelve de 1 a 50 coincidencias de línea, con fragmentos de hasta 500 caracteres. El límite predeterminado es 10; no cuenta documentos únicos.
- La lectura devuelve hasta 20.000 caracteres más un indicador de truncamiento, sin cargar la nota completa. La búsqueda enumera las rutas y después lee por líneas; detiene la lectura al alcanzar el límite de resultados.
- Una línea individual muy grande todavía consume memoria. El recorrido de archivos y el tamaño de la colección tampoco tienen un límite duro. Este ejemplo está pensado para vaults pequeños.
- Usa un vault sintético para pruebas. No publiques notas privadas.

Estas comprobaciones no son un aislamiento del sistema operativo: el proceso conserva los permisos del usuario. Suponen un vault controlado, sin modificaciones hostiles concurrentes. No impiden carreras entre validación y apertura ni detectan hard links. No uses este ejemplo para aislar contenido controlado por un atacante.

`stdio` mantiene local la comunicación entre cliente y servidor, pero no garantiza inferencia local. Los fragmentos entregados al cliente pueden enviarse al proveedor del modelo. Revisa qué carpeta expones y las políticas del cliente antes de utilizar notas reales.

Las notas son datos, no instrucciones confiables para el agente. La validación de rutas no elimina el riesgo de instrucciones maliciosas dentro de su contenido.

## Pendientes de la parte 2

La prueba con `FakeEmbedder` comprueba ranking y serialización, no calidad semántica real. Antes de publicar la parte 2 faltan corte estricto de párrafos largos, posiciones de chunks, política para archivos ilegibles en indexación, evaluación con el modelo real e integración como herramienta MCP. El notebook no se presenta como un servidor MCP remoto.

## Cuándo no usarlo

No es un servidor remoto ni multiusuario. Tampoco reemplaza un motor de búsqueda para colecciones grandes. Para un vault personal pequeño, prioriza código local y revisable.

## Distribución

El código vive en `projects/mcp-vault-search` dentro de [theguildit-repos](https://github.com/ricardogr07/theguildit-repos). Usa el commit del PR para reproducir este cambio; los tags por tutorial se definirán al cerrar cada pieza. PyPI y GHCR quedan fuera de este alcance.
