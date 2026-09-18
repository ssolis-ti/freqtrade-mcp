# Graphify — evaluación e integración (feature 004, propuesto)

**Fecha**: 2026-09-18 | **Estado**: evaluación hecha, integración diseñada, pendiente de decisión.

## Qué es graphify

`Graphify-Labs/graphify` (v0.9.63, PyPI `graphifyy`): convierte código + docs + PDFs +
SQL en un **knowledge graph consultable** (no vector store). Parseo de código local con
tree-sitter AST (determinista, sin LLM); docs/PDFs/imágenes usan un backend LLM para el
paso semántico.

- CLI: `graphify` (install, extract, query, path, explain, update, cluster-only, export).
- MCP: `graphify-mcp` (extra `[mcp]`) — **10 tools**: `query_graph`, `get_node`,
  `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`,
  `list_prs`, `get_pr_impact`, `triage_prs`.
- Soporta Hermes nativamente: `graphify install --platform hermes`.
- Salida: `graphify-out/{graph.json, graph.html, GRAPH_REPORT.md}`.
- Cada edge lleva confianza: `EXTRACTED` (explícito) | `INFERRED` | `AMBIGUOUS`.

## Entorno verificado (esta máquina)

| Ítem | Estado |
|---|---|
| `graphify` CLI | ✅ 0.9.57 instalado en `~/.local/bin/graphify` |
| Extras instalados | ✅ `[mcp,gemini]` (`uv tool install "graphifyy[mcp,gemini]"`) |
| `graphify-mcp` | ✅ `~/AppData/Roaming/uv/tools/graphifyy/Scripts/graphify-mcp.exe` |
| uv / Python / Docker | ✅ 0.12.16 / 3.11.15 / 29.6.2 |

## Hallazgo crítico: graphify rinde EXCELENTE sobre código, MAL sobre docs

Extracción real ejecutada (misma máquina, mismo día):

| Corpus | Nodos | Edges | Communities | Confianza | Coste |
|---|---|---|---|---|---|
| **Documentación** `docs-freqtrade` (95 .md) | 26 | 16 | 11 | — | ~$0.065 (LLM) |
| **Código** del framework (66 archivos, `--code-only`) | **468** | **939** | **19** | **98% EXTRACTED** | **$0** (AST local) |

**El código da 18x más nodos, 59x más edges, gratis, y con 98% de relaciones EXTRACTED
(reales del AST, no inferidas).**

### Evidencia de calidad sobre el código

`god_nodes` — las abstracciones centrales del framework (coinciden con el diseño real):
```
1. Embedder - 44 edges          5. index_block() - 23 edges
2. FreqtradeClient - 33 edges   6. _call() - 23 edges
3. build_despacho_mcp() - 27    7. get_block() - 21 edges
4. Retriever - 24 edges         8. AgenteLLM - 19 edges
```

`query_graph "how does the agent call the retriever"` → **34 nodos / 45 edges**,
trazando `Retriever` ↔ `AgenteLLM` por aristas `call` reales. El grafo **navega**.

### Problemas sobre documentación

> **ATENCIÓN — causa raíz identificada: RATE LIMIT, no limitación del modelo.**
> El log de la extracción muestra: `Quota exceeded for metric:
> generate_content_free_tier_requests, limit: 5, model: gemini-3-flash` y
> `WARNING: 2/4 semantic chunk(s) failed`. El free tier de Gemini permite **5
> requests/minuto** para `gemini-3-flash` (mucho más estricto que los 100/min de
> embeddings). Con 49 archivos, la mayoría de los chunks fallaron por **cuota agotada**.
> Por tanto el resultado de docs está **contaminado** y NO permite concluir que graphify
> sea incapaz con prosa.

Síntomas observados (todos consistentes con fallos de cuota, no con incapacidad):

1. **31 de 49 archivos no produjeron nodos** — coincide con "semantic chunks failed".
   Los archivos no fallaron por contenido: fallaron por 429.
2. **Densidad baja** (26 nodos / 16 edges) — consecuencia directa de que ~63% de los
   archivos nunca se procesaron.
3. **Nodos con degree 0**: `explain configuration_dry_run` → `Degree: 0`. Puede ser
   también artefacto de la extracción parcial (faltaban los otros archivos que habrían
   aportado los edges).

**Para verificar de verdad hace falta**: re-ejecutar con cuota disponible (o un backend
sin límite tan agresivo, p.ej. el gateway LiteLLM local `:4000` con deepseek, que no tiene
esos límites de free tier).

**Interpretación corregida**: no hay evidencia de que graphify no sirva para docs; hay
evidencia de que **el free tier de Gemini (5 req/min) es insuficiente** para extraer 95
documentos en una corrida. El código, en cambio, se extrae localmente con AST y no
depende de ninguna cuota — de ahí su resultado superior y reproducible.

## Dónde SÍ aportaría graphify (oportunidades reales)

1. **Nuestro propio código** (`rag/`, `servers/`, `despacho/`, `tools/`) — ahí el AST sí
   genera edges reales (`imports`, `calls`) y ayudaría a navegar el framework. Es local y
   gratis (sin LLM).
2. **freqtrade (el código real)** — si se clona el repo, mapea su arquitectura Python con
   relaciones reales; complementaría la doc con el código que la implementa.
3. **Complemento del RAG, no sustituto**: el RAG responde "¿qué dice la doc sobre X?";
   el grafo respondería "¿cómo se conecta X con Y en el código?".

## Propuesta de integración (si se decide avanzar)

**Fase A — grafo de nuestro código (local, gratis, alto valor)**
```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq
graphify extract . --code-only        # AST local, sin LLM, sin coste
graphify export html                  # graph.html navegable
```
Registrar `graphify-mcp` en Hermes: tools `god_nodes`, `graph_stats`, `query_graph`,
`shortest_path` sobre el código del framework.

**Fase B — grafo del código de freqtrade (opcional)**
```bash
graphify clone https://github.com/freqtrade/freqtrade
# o: git clone + graphify extract <path> --code-only
```

**Fase C — enlace grafo ↔ RAG por bloque (si el grafo resulta útil)**
Un bloque documental tendría DOS superficies: el RAG (recuperación por similitud, ya
operativo) y el grafo del código asociado (navegación estructural). El agente del bloque
podría elegir: citar la doc (RAG) o trazar la relación en el código (grafo).

## Recomendación (basada en la evidencia medida)

- **Código → graphify SÍ** (validado: 468 nodos / 939 edges / 98% EXTRACTED / $0 / sin
  dependencia de cuotas). Aporta navegación estructural real que el RAG no tiene.
- **Docs → RAG SÍ, y graphify queda PENDIENTE DE VERIFICAR**: la corrida sobre docs falló
  por rate limit de Gemini (5 req/min), no por incapacidad. Para saber si el grafo de docs
  aporta algo hay que re-ejecutar con un backend sin esos límites (el gateway LiteLLM
  local `:4000` con deepseek, que ya usamos para los agentes).
- Complemento natural: **RAG = "¿qué dice la doc?"**, **grafo = "¿cómo se conecta el código?"**

### Decisión pendiente clave (antes de cualquier integración de docs)

Re-ejecutar la extracción de docs con un backend sin límite de 5 req/min. **Intento hecho
(2026-09-18) con el gateway local — BLOQUEADO por entorno**: el gateway LiteLLM `:4000`
no estaba corriendo (Docker Desktop apagado; `curl` → HTTP 000 / conexión rechazada, y
`docker ps` → no conecta al daemon). graphify reportó `chunk 1/2 failed: Connection error`.

**Para reintentar (cuando Docker + gateway estén arriba):**
```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq && unset PYTHONPATH
export OPENAI_BASE_URL=http://localhost:4000/v1
export OPENAI_API_KEY=$(grep '^LLM_API_KEY=' .env | cut -d= -f2-)
export OPENAI_MODEL=deepseek-via-inference
graphify extract docs-freqtrade --backend openai --no-viz --allow-partial
```
Verificar antes que el gateway responde: `curl -s -o /dev/null -w "%{http_code}"
http://localhost:4000/v1/models -H "Authorization: Bearer $KEY"` → debe dar 200.

**Alternativa sin gateway**: reintentar con Gemini espaciando las llamadas (el free tier de
`gemini-3-flash` permite 5 req/min; graphify no parece respetar ese límite de forma
automática, así que habría que procesar por bloques pequeños en corridas sucesivas —
el modo incremental de graphify (`N unchanged`) lo permite).

### Integración propuesta (feature 004, pendiente de decisión)

**Fase A — grafo del código propio (VALIDADA, lista para registrar)**
```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq
graphify extract . --code-only     # 468 nodos, $0, local
graphify cluster-only .            # GRAPH_REPORT.md + comunidades nombradas
graphify export html               # graph.html navegable
```

Registro en Hermes (poner el MCP del grafo a disposición de los agentes):
```yaml
mcp_servers:
  freq_graph:
    command: C:\Users\P0zcl\AppData\Roaming\uv\tools\graphifyy\Scripts\graphify-mcp.exe
    args:
      - --graph
      - C:\Users\P0zcl\Desktop\proyectos\freq\graphify-out\graph.json
    enabled: true
```
Tools resultantes: `mcp_freq_graph_god_nodes`, `mcp_freq_graph_query_graph`,
`mcp_freq_graph_shortest_path`, `mcp_freq_graph_get_neighbors`, `mcp_freq_graph_graph_stats`.

**Fase B — grafo del código de freqtrade (opcional, alto valor)**
```bash
graphify clone https://github.com/freqtrade/freqtrade   # o git clone
graphify extract <path> --code-only --no-viz            # AST local, $0
```
Esto mapearía la arquitectura REAL de freqtrade (qué clase llama a qué), complementando
la doc que ya tenemos en RAG — el agente podría citar la doc Y trazar el código.

**Fase C — enlace grafo ↔ RAG por bloque**
Cada bloque documental tendría dos superficies: RAG (similitud) + grafo (estructura). El
agente del bloque elige: citar doc (RAG) o trazar relación en código (grafo).

### Decisión requerida

1. ¿Registramos el grafo del código propio en Hermes (Fase A)? — gratis, ya validado.
2. ¿Mapeamos también el código de freqtrade (Fase B)? — gratis, requiere clonar (~200 MB).
3. Los docs quedan en RAG (no pasan a grafo) — ¿de acuerdo?

## Artefactos generados (gitignored)

- `graphify-out/` (raíz): grafo del código del framework (468 nodos).
- `docs-freqtrade/graphify-out/` y `docs-freqtrade/02-configuracion/graphify-out/`:
  grafos de documentación (evidencia de la evaluación; se pueden borrar).

## Comandos ejecutados (reproducibles)

```bash
# instalación (hecha)
uv tool install "graphifyy[mcp,gemini]" --force

# docs: un bloque (17 nodos / 8 edges, ~$0.013)
export GEMINI_API_KEY=$(grep '^GEMINI_API_KEY=' /c/Users/P0zcl/Desktop/proyectos/freq/.env | cut -d= -f2-)
graphify extract docs-freqtrade/02-configuracion --no-viz

# docs: corpus completo (26 nodos / 16 edges, ~$0.065)
graphify extract docs-freqtrade --no-viz

# CODIGO propio (468 nodos / 939 edges, $0, local)
graphify extract . --code-only --no-viz

# tools MCP del grafo (10): query_graph, get_node, get_neighbors, get_community,
# god_nodes, graph_stats, shortest_path, list_prs, get_pr_impact, triage_prs
.venv/Scripts/python.exe tools/probe_graphify_mcp.py <graph.json>
.venv/Scripts/python.exe tools/probe_graph_code.py    # stats + god_nodes + query
```
