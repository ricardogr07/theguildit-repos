# Parte 1: Tu primer servidor MCP para buscar notas

**Estado:** Borrador pendiente de revisión de Ricardo  
**Versión:** 1.0  
**Checkpoint de código:** https://github.com/ricardogr07/mcp-vault-search (rama main)  
**Tiempo estimado:** 20 a 25 minutos

---

## Lo que construirás

Al terminar esta primera parte, tendrás:

1. Un servidor MCP local.
2. Dos herramientas disponibles:
   - **`search_notes`**: busca texto literal en tus notas Markdown.
   - **`read_note`**: lee una nota completa de forma segura, sin permitir acceso fuera de tu vault.
3. Conexión configurada en Claude Desktop o VS Code para usar esas herramientas automáticamente.
4. Un conjunto de pruebas que verifican que la búsqueda funciona correctamente y que las rutas están protegidas contra acceso no autorizado.

---

## El problema: conocimiento atrapado en archivos

Tienes notas útiles en Markdown o txt. Están en tu laptop, privadas, organizadas como quieres. Pero Claude (o cualquier otro LLM o agente) no puede leerlas directamente sin acceder a tu computadora y archivos personales.

Hoy tienes tres opciones que son subóptimas:
- **Copiar y pegar en cada conversación.** Tedioso, no escala, pierdes contexto entre sesiones.
- **Subirlas a un servicio.** Pierdes privacidad, depende de terceros, datos en la nube.
- **Esperar una integración oficial.** No existe todavía, y es lenta.

**La mejor opción:** construir tu propia herramienta en 20 minutos. Datos privados, bajo tu control, lista hoy mismo.

---

## MCP: el USB-C de los agentes

**MCP = Model Context Protocol**. Es un estándar abierto que define cómo un cliente (Claude, otro agente, tu aplicación) se conecta y comunica con herramientas externas.

Piensa en USB-C: sin él, cada dispositivo necesitaba su propio cable y protocolo de comunicación para enviar información. Con USB-C, un solo conector funciona con cualquier dispositivo que lo entienda.

**Sin MCP:**
- Deberías escribir código distinto para cada cliente: uno para Claude Desktop, otro para la API de Anthropic, otro para OpenAI o Grok, otro para tu bot en Slack.
- Cada cliente hablaría un idioma distinto.
- Duplicarías herramientas y lógica en múltiples lugares.

**Con MCP:**
- Defines tus herramientas una sola vez, en MCP.
- Cualquier cliente que entienda MCP (Claude Desktop, VS Code, API de Anthropic, futuros clientes) las usa automáticamente.
- Mantienes una única fuente de verdad.

---

## REST vs CLI vs MCP: tres formas de conectar herramientas

Hay tres maneras de que Claude u otros LLMs accedan a tus notas en este ejemplo. Cada una tiene ventajas y desventajas.

### Opción 1: CLI

El enfoque tradicional: escribes un script ejecutable.

```bash
search_notes --query "MCP" --limit 10
```

**Cómo funcionaría:**
- Claude genera comandos shell o grep y los ejecuta.
- Lee el output de texto y lo parsea.

**Problemas graves:**
- **Seguridad:** Claude necesita permisos shell.
- **Parsing frágil:** Si cambias el formato de salida, todo se rompe.
- **Sin estructura:** El output es texto plano. Errores son difíciles de detectar automáticamente.
- **Inconsistencia:** Cada herramienta define su propia interfaz (argumentos, formato, errores).

### Opción 2: REST HTTP

Expones herramientas en un servidor web.

```
Cliente: POST http://localhost:8000/api/search
Body: { "query": "MCP", "limit": 10 }

Servidor: HTTP 200 OK
Body: [{ "path": "intro.md", "line": 1, "text": "..." }]
```

**Ventajas:**
- Protocolo estándar, bien documentado (OpenAPI/Swagger).
- Funciona remotamente (puedes compartir con otros).
- Separación clara cliente-servidor.

**Problemas:**
- **Setup más complejo:** necesitas abrir puertos, manejar CORS, agregar autenticación.
- **Seguridad adicional:** si expones remotamente, necesitas TLS, autenticación, rate limiting.
- **Overhead de red:** HTTP añade headers, handshakes, latencia.
- **Overkill para local:** es como tomar un taxi para llegar al Oxxo de la esquina. Para herramientas locales, es demasiado.

REST es excelente para APIs públicas. Para conectar herramientas locales con un LLM en tu máquina, es excesivo.

### Opción 3: MCP (Model Context Protocol)

El enfoque nativo para LLMs.

```
TÚ: "Busca MCP en mis notas"
       ↓
CLAUDE: "Necesito la herramienta search_notes"
       ↓
SERVIDOR: "Tengo search_notes(query: string, limit: int)"
       ↓
CLAUDE: "Llamo search_notes con query='MCP', limit=5"
       ↓
SERVIDOR: Retorna JSON estructurado
       ↓
CLAUDE: "Encontré 3 notas"
```

**Ventajas de MCP:**
1. **Seguro por defecto.** Usa `stdio` (pipe local entre procesos). Sin puertos abiertos, sin red, sin shell.
2. **Introspección automática.** El servidor declara: "Tengo estas herramientas con estos parámetros (esquemas JSON)". Claude entiende sin documentación manual.
3. **Una definición, múltiples clientes.** Defines herramientas una sola vez. Funcionan en Claude Desktop, VS Code, la API de Anthropic, y cualquier cliente MCP futuro.
4. **Tipado y estructurado.** JSON-RPC incluye tipos. Errores son claros, no ambigüos.
5. **Diseñado para local-first.** Pensado para máquinas del usuario, no servidores públicos.

**Comparación rápida:**

| Aspecto | CLI | REST | MCP |
|---------|-----|------|-----|
| **Seguridad** | Baja (shell) | Media (red) | Alta (stdio local) |
| **Setup** | Trivial | Moderado (puerto, CORS) | Simple (config JSON) |
| **Documentación** | Manual | Automática (OpenAPI) | Automática (schemas JSON) |
| **Remoto** | No | Sí | No (local-first) |
| **Para LLMs** | Frágil | Posible | Nativo |
| **Típico use case** | Usuario → máquina | App → API pública | LLM → herramientas locales |

**Para este tutorial:** MCP es ideal. Seguro, simple, diseñado exactamente para conectar LLMs con herramientas locales.

---

## El protocolo MCP en 5 minutos

MCP usa **JSON-RPC 2.0** (Remote Procedure Call en JSON) para comunicación bidireccional. El cliente (Claude) y el servidor (tu máquina) intercambian mensajes JSON. Cada mensaje tiene:
- `jsonrpc`: siempre `"2.0"`
- `id`: número único para rastrear respuestas
- `method`: qué hacer (`initialize`, `tools/list`, `tools/call`)
- `params`: argumentos
- `result` o `error`: respuesta

Así funciona paso a paso:

### 1. Inicialización (Handshake)

Cliente conecta y pregunta: "¿Qué sabes hacer?"

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": { "name": "Claude Desktop", "version": "1.0" }
  }
}
```

Servidor responde: "Tengo estas herramientas"

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {
        "listChanged": true
      }
    },
    "serverInfo": { "name": "mcp-vault-search", "version": "0.1.0" }
  }
}
```

### 2. Listado de herramientas

Cliente pide: "Dame la lista de herramientas"

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

Servidor responde:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "search_notes",
        "description": "Busca texto literal en notas Markdown del vault configurado.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string", "description": "Término a buscar" },
            "limit": { "type": "integer", "default": 10 }
          },
          "required": ["query"]
        }
      },
      {
        "name": "read_note",
        "description": "Lee una nota Markdown usando una ruta relativa al vault configurado.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "Ruta relativa al vault, p.ej. intro.md" }
          },
          "required": ["path"]
        }
      }
    ]
  }
}
```

Claude ve las dos herramientas y entiende qué parámetros necesitan.

### 3. Llamada a herramienta

Claude decide usar `search_notes`:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_notes",
    "arguments": { "query": "MCP", "limit": 5 }
  }
}
```

Servidor ejecuta la función Python y retorna:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"path\": \"intro.md\", \"line\": 1, \"text\": \"# Introducción a MCP\"}, ...]"
      }
    ]
  }
}
```

### 4. Fin de sesión

Cuando Claude termina:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": { "role": "user", "content": "Listo, encontré 3 notas sobre MCP" }
}
```

**En resumen:** MCP es un conversación JSON-RPC entre cliente y servidor. El cliente dice qué quiere, el servidor lista qué puede hacer, y luego ejecutan juntos.

---

## Arquitectura en capas

El código está organizado en **tres capas independientes**. Cada una hace una cosa bien, y no necesita saber de las otras.

```
┌─────────────────────────────────┐
│   Capa 3: Configuración Cliente │  claude_desktop_config.json
│   (descubrimiento e integración)│
└────────────────────┬────────────┘
                     │
┌────────────────────┴────────────┐
│   Capa 2: Servidor MCP          │  server.py
│   (adaptador, serialización)    │
└────────────────────┬────────────┘
                     │
┌────────────────────┴────────────┐
│   Capa 1: Lógica Pura           │  vault.py
│   (búsqueda, seguridad, I/O)    │
└─────────────────────────────────┘
```

### Capa 1: Lógica pura (vault.py)

**Responsabilidad única:** buscar y leer notas. Nada de MCP, JSON, o redes.

Dos funciones, ambas deterministas:

```python
def search_notes(root: Path, query: str, limit: int = 10) -> list[dict]:
    """Retorna lista de diccionarios con path, línea, texto."""
    # Valida entrada
    # Busca archivos .md
    # Retorna matches (hasta limit)

def read_note(root: Path, relative_path: str, max_chars: int = 20_000) -> str:
    """Retorna contenido de nota (hasta max_chars)."""
    # Valida ruta (no absoluta, no fuera del vault)
    # Bloquea path traversal
    # Trunca si es muy grande
```

**Por qué:**
- Testeable sin servidor (solo Python puro).
- Reutilizable desde CLI, HTTP, Slack, MCP, scripts, cualquier lado.
- Si cambias el protocolo mañana, esta capa no se toca.

Prueba directa:

```bash
python -c "
from src.mcp_vault_search.vault import search_notes, vault_root
root = vault_root('examples/vault')
results = search_notes(root, 'MCP', limit=3)
print(results)  # Lista de dicts, sin JSON
"
```

**Validaciones:**
- Entrada: query no vacía, limit entre 1 y 50.
- Seguridad: path traversal bloqueado (no `./../..`), solo .md, máximo 20k chars.

### Capa 2: Servidor MCP (server.py)

**Responsabilidad única:** exponer Capa 1 como herramientas MCP.

```python
from mcp.server import MCPServer
from .vault import search_notes as search_vault

mcp = MCPServer("mcp-vault-search")

@mcp.tool()
def search_notes(query: str, limit: int = 10) -> str:
    """Busca texto literal en notas Markdown del vault configurado."""
    matches = search_vault(configured_root(), query, limit)
    return json.dumps(matches, ensure_ascii=False, indent=2)  # JSON strings

def main() -> None:
    mcp.run(transport="stdio")  # Pipe local, no red
```

**Qué hace:**
1. Importa funciones de Capa 1 (las funciones puras).
2. Envuelve con `@mcp.tool()` (declara "esto es una herramienta MCP").
3. Serializa salida a JSON (MCP requiere strings JSON).
4. Corre servidor en `stdio` (pipe local).

**Similar a REST, pero más simple:**
- REST: `@app.post("/api/search")` + puerto + HTTP overhead.
- MCP: `@mcp.tool()` + `stdio` local + JSON-RPC.

El adaptador es transparente: Claude Desktop ve las herramientas automáticamente.

### Capa 3: Configuración del cliente (claude_desktop_config.json)

**Responsabilidad única:** decirle a Claude Desktop dónde encontrar el servidor y cómo lanzarlo.

```json
{
  "mcpServers": {
    "vault-search": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/absoluta/a/mcp-vault-search",
        "run",
        "src/mcp_vault_search/server.py"
      ]
    }
  }
}
```

**Qué hace:**
- Al iniciar Claude Desktop, lee este JSON.
- Ejecuta el comando especificado (`uv run ...`).
- Se conecta al servidor vía `stdio`.
- Las herramientas de Capa 2 aparecen en la interfaz.

**Flujo:**
```
Claude Desktop inicia
  ↓
Lee claude_desktop_config.json
  ↓
Ve "vault-search": { "command": "uv", "args": [...] }
  ↓
Ejecuta: uv run src/mcp_vault_search/server.py
  ↓
Se conecta al proceso vía stdio
  ↓
Obtiene lista de herramientas (search_notes, read_note)
  ↓
Muestra en interfaz
```

---

## Cómo fluye un pedido end-to-end

Tú escribes: "Busca MCP en mis notas"

```
1. TÚ (usuario)
   ↓
   "Busca MCP en mis notas"

2. CLAUDE DESKTOP (Capa 3)
   Lee solicitud. Pregunta al servidor: "¿Qué herramientas tienes?"
   ↓
   Envía: { "method": "tools/list", "params": {} }

3. SERVIDOR (Capa 2)
   Lee petición. Ve que necesitas herramientas.
   Responde: "Tengo search_notes y read_note"
   ↓
   Envía: { "result": { "tools": [ { "name": "search_notes", ... } ] } }

4. CLAUDE DESKTOP
   Recibe lista. Entiende que search_notes es relevante para "Busca MCP".
   ↓
   Llama: { "method": "tools/call", "params": { "name": "search_notes", "arguments": { "query": "MCP", "limit": 10 } } }

5. SERVIDOR (Capa 2)
   Recibe solicitud. Extrae argumentos: query="MCP", limit=10
   Llama Capa 1: search_vault(root, "MCP", 10)
   ↓
   La función pura ejecuta la lógica

6. CAPA 1 (vault.py)
   Busca en archivos. Encuentra matches.
   Retorna: [ { "path": "intro.md", "line": 1, "text": "# Introducción a MCP" }, ... ]

7. SERVIDOR (Capa 2)
   Serializa resultado a JSON
   ↓
   Envía: { "result": { "content": [ { "type": "text", "text": "[{\"path\": \"intro.md\", ...}]" } ] } }

8. CLAUDE DESKTOP (Capa 3)
   Recibe respuesta. Formatea para mostrar.

9. CLAUDE
   Procesa respuesta. Genera resumen en lenguaje natural.
   ↓
   "Encontré 3 notas sobre MCP: intro.md (línea 1), protocolos.md (línea 5), ..."
```

Cada capa hace su trabajo. Ninguna conoce detalles de las otras. Si Capa 1 cambia (ej: agregar búsqueda semántica), Capa 2 y 3 no se tocan.

---

## Por qué esta arquitectura importa

**Escenario 1: Mañana quieres usar estas herramientas desde un script local**

```bash
python -c "
from src.mcp_vault_search.vault import search_notes, vault_root
root = vault_root('/ruta/a/mis/notas')
for match in search_notes(root, 'TODO'):
    print(f'{match[\"path\"]}:{match[\"line\"]}: {match[\"text\"]}')
"
```

Usas **Capa 1 directamente**. MCP ni existe. Dos líneas de código. Listo.

**Escenario 2: Quieres exponer como API HTTP para tu equipo (sin privacidad)**

```python
from fastapi import FastAPI
from src.mcp_vault_search.vault import search_notes

app = FastAPI()

@app.post("/search")
def search_api(query: str, limit: int = 10):
    return search_notes(vault_root("/ruta"), query, limit)
```

Importas **Capa 1** como antes. **Capa 2 no existe** (FastAPI reemplaza). Una semana de trabajo en lugar de reescribir.

**Escenario 3: Quieres integrar con tu bot de Slack**

```python
@app.event("app_mention")
def handle_mention(event):
    text = event["text"]
    results = search_notes(vault_root("/ruta"), text)  # Capa 1
    return format_slack_message(results)
```

De nuevo, **Capa 1** reutilizable. Capa 2 y 3 no importan.

**La clave:** Capa 1 es el motor. Capa 2 es la caja de cambios. Capa 3 es el volante. Cambias Capa 2 y 3 sin tocar el motor.

---

## Por qué crear herramientas propias

Tres razones:

1. **Control de datos.** Tus notas quedan en tu máquina. Ningún servidor externo ve su contenido.
2. **Límites claros.** Decides qué máximo 10 resultados de búsqueda, máximo 20.000 caracteres por nota.
3. **Cero espera.** Una integración oficial de "buscar en mis notas" no existe. Tú la tienes en 20 minutos.

---

## Requisitos previos

Necesitas:
- **Python 3.11 o superior.** (Verifica con `python --version`.)
- **`uv`** como gestor de dependencias. (Instala desde https://docs.astral.sh/uv/)
- **Claude Desktop** actualizado. (Descargalo desde https://claude.ai/download)

---

## Paso 1: Descargar el código y dependencias

Clona el repositorio y entra en la carpeta:

```bash
git clone https://github.com/ricardogr07/mcp-vault-search.git
cd mcp-vault-search
```

Sincroniza dependencias con `uv`:

```bash
uv sync
```

Resultado esperado:
```
Resolved 15 packages in XXms
Installed 15 packages in XXms
```

---

## Paso 2: Conoce el vault sintético

El repositorio incluye ejemplos en `examples/vault/`:

```bash
ls examples/vault/
```

Resultado esperado:
```
intro.md
protocolos.md
python.md
seguridad.md
```

Abre uno para ver el contenido:

```bash
cat examples/vault/intro.md
```

Resultado esperado (extracto):
```markdown
# Introducción a MCP

MCP es un protocolo abierto para conectar clientes con herramientas.

Ver también: protocolos para agentes, búsqueda semántica.
```

Estos ejemplos son el "vault" que el servidor buscará. Puedes reemplazarlos con tus notas reales después.

---

## Paso 3: Inicia el servidor en modo desarrollo

Ejecuta el inspector interactivo de MCP:

```bash
uv run mcp dev src/mcp_vault_search/server.py
```

Resultado esperado (terminal interactiva):
```
MCP Inspector
Starting server mcp-vault-search with stdio...
Listening on stdio
{"jsonrpc": "2.0", "method": "initialize", ...}
```

El inspector ahora expone las herramientas. Prueba una búsqueda literal:

En el inspector, envía:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_notes",
    "arguments": {
      "query": "MCP",
      "limit": 5
    }
  }
}
```

Resultado esperado:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"path\": \"intro.md\", \"line\": 1, \"text\": \"# Introducción a MCP\"}, ...]"
      }
    ]
  }
}
```

Salir del inspector: `Ctrl+C` o `exit`.

---

## Paso 4: Cómo funciona la búsqueda (sin magia)

Abre `src/mcp_vault_search/vault.py`:

La función `search_notes()`:

```python
def search_notes(root: Path, query: str, limit: int = 10) -> list[dict[str, object]]:
    term = query.strip().casefold()  # Busca sin importar mayúsculas
    if not term:
        raise ValueError("La consulta no puede estar vacía")
    if limit < 1 or limit > 50:  # Máximo 50 para no saturar
        raise ValueError("limit debe estar entre 1 y 50")

    matches: list[dict[str, object]] = []
    for path in markdown_files(root):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if term in line.casefold():  # Búsqueda literal
                matches.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip()[:500],  # Primeros 500 caracteres
                    }
                )
                if len(matches) == limit:
                    return matches
    return matches
```

Lo que hace:
1. Normaliza la consulta (espacios, mayúsculas).
2. Valida que no esté vacía y el límite sea razonable.
3. Recorre cada `.md` en el vault.
4. Busca líneas que contengan el término (búsqueda literal, case-insensitive).
5. Retorna hasta `limit` resultados con contexto (número de línea, preview de 500 caracteres).

---

## Paso 5: Cómo funciona la lectura segura

La función `read_note()` en el mismo archivo:

```python
def read_note(root: Path, relative_path: str, max_chars: int = 20_000) -> str:
    requested = Path(relative_path)
    if requested.is_absolute() or requested.suffix.lower() != ".md":
        raise ValueError("La ruta debe ser relativa y apuntar a un archivo Markdown")

    target = (root / requested).resolve()
    if not target.is_relative_to(root):  # Path traversal check
        raise ValueError("La ruta sale del vault permitido")
    if not target.is_file():
        raise FileNotFoundError(relative_path)

    content = target.read_text(encoding="utf-8")
    return content if len(content) <= max_chars else content[:max_chars] + "\n\n[contenido truncado]"
```

Validaciones críticas:
1. **No rutas absolutas.** Solo rutas relativas (`intro.md`, no `/etc/passwd`).
2. **Solo Markdown.** La ruta debe terminar en `.md`.
3. **Path traversal bloqueado.** Si intentas `../../../etc/passwd`, falla.
4. **Máximo 20.000 caracteres.** Notas gigantes se truncan.

Prueba intentando romperla:
```bash
uv run python -c "
from pathlib import Path
from src.mcp_vault_search.vault import read_note, vault_root

root = vault_root('examples/vault')
try:
    read_note(root, '../../../etc/passwd')
except ValueError as e:
    print(f'Bloqueado correctamente: {e}')
"
```

Resultado esperado:
```
Bloqueado correctamente: La ruta sale del vault permitido
```

---

## Paso 6: Conectar con Claude Desktop o VS Code

El servidor MCP funciona con cualquier cliente que lo entienda. Aquí cubrimos Claude Desktop; VS Code requiere un setup similar.

### Claude Desktop

Abre el archivo de configuración:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Añade o actualiza la sección `mcpServers`:

```json
{
  "mcpServers": {
    "vault-search": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/absoluta/a/mcp-vault-search",
        "run",
        "src/mcp_vault_search/server.py"
      ]
    }
  }
}
```

**Pasos:**
1. Copia el JSON arriba.
2. Reemplaza `/ruta/absoluta/a/mcp-vault-search` con la ruta real de tu carpeta. 
   - En Windows, usa: `C:\\Users\\TuNombre\\mcp-vault-search` (con dobles backslashes).
   - En macOS/Linux, usa: `/Users/tunombre/mcp-vault-search` (ruta absoluta).
3. Guarda el archivo.
4. Reinicia Claude Desktop.

### VS Code (avanzado)

VS Code con la extensión de Claude también soporta MCP. Usa la misma configuración, pero en la extensión (clic en el engranaje → Configuración de extensión). Para esta parte, enfócate en Claude Desktop.

Si ya tienes VS Code configurado y quieres intentarlo, repite el setup de configuración en tu terminal y VS Code debería descubrirlo automáticamente.

---

## Paso 7: Valida en Claude Desktop

Abre una conversación nueva en Claude Desktop.

Busca el ícono de herramientas (abajo a la izquierda). Verás "vault-search" listado.

**Prueba 1: búsqueda literal**

Escribe:
```
Busca "MCP" en mis notas.
```

Claude debería llamar a `search_notes` automáticamente. Verás:
```
Herramienta: search_notes
Argumentos: { "query": "MCP", "limit": 10 }

Resultado:
[
  {
    "path": "intro.md",
    "line": 1,
    "text": "# Introducción a MCP"
  },
  ...
]
```

**Prueba 2: lectura de nota**

Escribe:
```
Léeme la nota intro.md completa.
```

Claude llama a `read_note` y retorna el contenido completo (hasta 20.000 caracteres).

---

## Paso 8: Ejecuta las pruebas automatizadas

Vuelve a la terminal. Ejecuta:

```bash
uv sync
uv run python -m pytest tests/ -v
```

Resultado esperado:
```
tests/test_vault.py::VaultTest::test_empty_query_is_rejected PASSED
tests/test_vault.py::VaultTest::test_read_note_rejects_path_traversal PASSED
tests/test_vault.py::VaultTest::test_read_note_returns_markdown PASSED
tests/test_vault.py::VaultTest::test_search_is_case_insensitive_and_bounded PASSED
tests/test_semantic.py::SemanticTest::test_index_is_json_and_query_ranks_related_note_first PASSED

====== 5 passed in 0.10s ======
```

Todas verdes = servidor listo.

---

## Paso 9: Usa tus propias notas, no el ejemplo

De verdad, el vault de ejemplo es solo para probar. Ahora monta tus notas reales.

**Opción A: Copia tus notas al vault de ejemplo**

```bash
cp /ruta/a/tus/notas/*.md examples/vault/
```

Reinicia Claude Desktop. Las nuevas notas aparecerán automáticamente.

**Opción B: Apunta a otra carpeta (recomendado)**

Si tus notas están en `/Users/juan/Notas` o `C:\Users\Juan\Documentos\Notas`, dile al servidor dónde encontrarlas. Edita la configuración de Claude Desktop y añade `env`:

```json
{
  "mcpServers": {
    "vault-search": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/absoluta/a/mcp-vault-search",
        "run",
        "src/mcp_vault_search/server.py"
      ],
      "env": {
        "VAULT_PATH": "/Users/juan/Notas"
      }
    }
  }
}
```

En Windows:

```json
"env": {
  "VAULT_PATH": "C:\\Users\\Juan\\Documentos\\Notas"
}
```

Guarda y reinicia Claude Desktop.

---

## Lo que no hace (y por qué)

### Búsqueda semántica

Este servidor busca palabras exactas. Si buscas "protocolos para agentes", no encuentra una nota que solo dice "MCP", aunque sean sinónimos.

**Razon:** Búsqueda semántica requiere modelos de embeddings (transformers). Parte 2 lo añade.

### Acceso remoto

El servidor corre localmente en `stdio`. Solo Claude Desktop (en la misma máquina) puede usarlo.

**Razón:** Protege privacidad. Si quieres compartir, Parte 3 mete el servidor en Docker.

### Sincronización automática

Si cambias una nota mientras Claude Desktop está abierto, los cambios se ven en el siguiente acceso (sin reload).

**Razón:** YAGNI (You Aren't Gonna Need It). Agrega complejidad sin valor real hoy.

---

## Límites conocidos

| Límite | Razón | Solución |
|--------|-------|----------|
| Búsqueda literal solo. | Los embeddings cuestan tokens y tiempo. | Parte 2: búsqueda semántica. |
| Máximo 50 resultados. | Evita saturar contexto. | Aumenta en `vault.py:22` si necesitas. |
| Máximo 20.000 caracteres/nota. | Contexto de Claude es finito. | Parte 1 + Part 2 pueden cachear. |
| Solo Markdown. | Formato simple, seguro de parsear. | Ext a otros formatos en Parte 2. |
| Sin autenticación. | Server corre localmente en `stdio`. | Parte 3: Docker + reverse proxy si es remoto. |

---

## Próximo paso: Parte 2

Parte 2 conserva estas herramientas y añade:
- Búsqueda **semántica** (por significado, no palabras clave).
- Indexación offline local.
- Demostración en Google Colab sin tocar el servidor.

Hasta entonces, tienes un servidor funcional, seguro y privado.

---

## Referencias

- **Repositorio:** https://github.com/ricardogr07/mcp-vault-search
- **MCP Specification:** https://modelcontextprotocol.io/
- **MCP Python SDK:** https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop:** https://claude.ai/download
- **`uv` (gestor de paquetes):** https://docs.astral.sh/uv/

---

## Código verificado contra

- **pyproject.toml:** mcp[cli]>=2.0.0, requires-python >=3.10 (nota: repositorio actual dice >=3.10, pero MCP SDK oficial requiere >=3.11; revisar antes de publicar)
- **Pruebas:** todos los tests en `tests/` pasan (5/5)
- **Docker:** imagen se construye sin errores (verificado 2026-10-27)

---

**Borrador pendiente de revisión. No publicado. No contiene imágenes. Esperando aprobación de Ricardo.**

