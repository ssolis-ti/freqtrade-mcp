# Arquitectura del Framework Freqtrade Multi-Agent (documento maestro)

> Documento de referencia para cualquier LLM o desarrollador que necesite entender
> este proyecto sin contexto previo. Cubre: qué es, cómo funciona, arquitectura,
> módulos, tools, formatos de datos, configuración y estado.
>
> Fuente de verdad de diseño: `.specify/memory/constitution.md` (principios) y
> `specs/` (specs SDD). Este documento es el mapa; aquellos son la ley.

---

## 1. Qué es esto

**Framework que convierte la documentación oficial de freqtrade en un sistema de
agentes LLM especializados.** La premisa central:

> **La documentación es la estructura organizacional.** Freqtrade tiene ~45 capítulos
> de documentación densa en parámetros (2 MB, ~467K tokens estimados — 3.7x un contexto
> de 128K). Ningún LLM general puede dominarla sin reventar su contexto. La solución:
> repartir la documentación en **12 bloques documentales**, y dar a cada bloque un
> **agente LLM con RAG** sobre su propio corpus.

Cada agente es dueño de su dominio documental: consulta SOLO su bloque, responde con
fundamento y citas, y nunca cruza a otro bloque ni inventa (no-hits explícito).

**Estado de la base**: la capa de *conocimiento* está completa y operativa (RAG +
agentes + MCP). La capa de *acción* (ejecutar órdenes sobre freqtrade vía REST/CLI)
está diseñada pero pendiente de integrar (ver sección 9).

---

## 2. Los 12 bloques documentales

La documentación oficial se descargó en dos mirrors (mismos 12 bloques):

| Bloque | Contenido |
|---|---|
| `00-index` | Índice general |
| `01-instalacion` | Instalación, Docker, actualización |
| `02-configuracion` | configuration.md (58K/64K, el más denso en parámetros) |
| `03-estrategia` | strategy-101, advanced, customization, callbacks, migration, trade-object |
| `04-backtesting` | backtesting, advanced, lookahead, recursive |
| `05-hyperopt` | hyperopt, advanced-hyperopt |
| `06-freqai` | FreqAI + 6 subcapítulos (el tema más denso: 7 agentes previstos) |
| `07-riesgo-futuros` | stoploss, leverage, exchanges |
| `08-control` | rest-api, freq-ui |
| `09-datos` | data-download, data-analysis, utils, sql_cheatsheet, plotting |
| `10-extensiones` | plugins (pairlists, protections), producer-consumer |
| `11-operativo` | telegram, webhook, bot-basics, faq, developer, etc. |

**Los dos mirrors** (corpus por bloque):
- `docs-freqtrade/<bloque>/` — markdown fuente del repo oficial (rama `develop`), texto limpio.
- `docs-freqtrade-web/<bloque>/` — versión estable renderizada de freqtrade.io (HTML→MD).

Ambos se indexan por bloque. Los chunks de cada mirror se etiquetan con `mirror:
"fuente" | "web"`.

---

## 3. Arquitectura en capas

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA 4: CONSUMIDORES                                       │
│  Hermes Agent (chat), MCP clients, cualquier LLM            │
│  ── habla por MCP stdio o CLI                               │
├─────────────────────────────────────────────────────────────┤
│  CAPA 3: SERVERS MCP (por bloque)                           │
│  servers/run_bloque.py  → RAG puro (consultar_docs, health) │
│  servers/run_agente.py  → Agente LLM (responder, + RAG)     │
├─────────────────────────────────────────────────────────────┤
│  CAPA 2: NÚCLEO (rag/)                                      │
│  blocks → chunking → embeddings → indexer → retriever → agent│
├─────────────────────────────────────────────────────────────┤
│  CAPA 1: DATOS                                              │
│  docs-freqtrade/ + docs-freqtrade-web/ (corpus)             │
│  data/rag/<bloque>/ (vector store + manifiesto, gitignored) │
└─────────────────────────────────────────────────────────────┘
```

**Flujo de una consulta** (agente del bloque `04-backtesting`):

```
LLM pregunta: "What does backtesting require to work?"
  → servers/run_agente.py 04-backtesting (MCP stdio)
  → rag/agent.py AgenteLLM.responder()
  → rag/retriever.py Retriever.query()  (solo corpus del bloque 04)
  → recupera top-k chunks por similitud de coseno (min_score 0.25)
  → si no hay hits: rechazo explícito (sin llamar al LLM)
  → si hay hits: prompt = fragmentos + pregunta → LLM del gateway (:4000)
  → respuesta con citas [fuente: web/backtesting.md - Backtesting]
```

---

## 4. Módulos (código)

### `rag/` — núcleo

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Config desde env (`.env`), sin rutas absolutas; raíz derivada del módulo |
| `blocks.py` | Catálogo de los 12 bloques: id → rutas a ambos mirrors + `rag_dir` |
| `chunking.py` | `chunk_markdown(text, path, mirror, block_id)` → chunks jerárquicos por cabeceras, con split por tamaño (MAX_CHARS ~2000 + solape ~200). Id determinista `sha1(mirror\|path\|idx)` |
| `embeddings.py` | Clase `Embedder`: 3 backends en cascada (Gemini → gateway → local-hash), batching, retry con backoff, validación de dimensión |
| `indexer.py` | `index_block(block, force)` → lee ambos mirrors, chunking + embeddings, escribe `chunks.json` + `vectors.npy` + `index.json`. Idempotente por `content_hash` |
| `retriever.py` | `Retriever(block_id)` → `query(q, top_k, min_score)` por coseno numpy; no-hits `[]`; auto-detección de backend según el índice; validación post-embed |
| `agent.py` | `AgenteLLM(block_id)` → `responder(query, top_k)` con citas; `health()`. Rechazo sin hits; degrada a hits crudos si el LLM falla; modelo por env |

### `servers/` — MCP (FastMCP, stdio)

| Archivo | Tools expuestas |
|---|---|
| `run_bloque.py <id>` → `block_mcp.build_mcp` | `consultar_docs(query, top_k)`, `health()` |
| `run_agente.py <id>` → `agent_mcp.build_agent_mcp` | `responder(query, top_k)`, `consultar_docs(query, top_k)`, `health()` |

### `tools/` — CLI y utilidades

| Tool | Función |
|---|---|
| `index_blocks.py [bloque] [--force]` | Indexar uno o todos los bloques |
| `query_block.py <bloque> "pregunta"` | Consulta RAG sin MCP (depuración) |
| `benchmark_rag.py <bloque>` | Golden set → recall@1/@3, MRR → `data/benchmark/` |
| `make_golden_set.py` | Genera `tools/golden_set.json` desde chunks reales |
| `medir_contexto.py` | Tokens por bloque (justifica el RAG) |
| `barrido_bloques.py` | Verifica que todos los bloques responden |
| `smoke_mcp_stdio.py` / `smoke_agente_stdio.py` | Smoke end-to-end del protocolo MCP (handshake real) |
| `fetch_docs.py` / `fetch_docs_web.py` | Descarga los mirrors (fuente develop / web stable) |
| `build_docs_index.py` | Regenera los README índice de los mirrors |
| `verificar_indices.py` | Diagnostica consistencia index.json vs vectors.npy |
| `setup_env_key.py` | Copia la master key del gateway local a `.env` (sin imprimirla) |
| `probe_*.py` | Diagnósticos del gateway/embeddings (no se necesitan en operación) |
| `demo_entender_doc.py` | Demo: agente responde con citas |

### `tests/` — 26 tests GREEN

| Archivo | Cubre |
|---|---|
| `conftest.py` | `pytest_configure`: redirige RAG_DATA_DIR a un dir temporal (los tests NUNCA tocan producción) |
| `test_chunking.py` (5) | Jerarquía, split de secciones grandes, id determinista, mirrors distintos |
| `test_indexer.py` (3) | Indexa piloto, idempotencia, mirror ausente |
| `test_retriever.py` (6) | Hits relevantes, top-k, no-hits, umbral, bloque inexistente, health |
| `test_mcp.py` (4) | Tools listadas, consulta, no-hits, health |
| `test_agent.py` (5) | responder con citas (mocks, sin gasto), sin_hits no llama al LLM, degradación, health, modelo por env |
| `test_benchmark.py` (3) | Golden set válido, métricas, reporte JSON |

### `prototype/` — wrapper REST de freqtrade (las "manos", aún no integrado)

`prototype/freqtrade-mcp/mcp_server.py`: 19 tools MCP sobre la REST API de freqtrade
(`/api/v1`, auth JWT): `forceenter`, `forceexit`, `blacklist`, `lock_pair`, `status`,
`profit`, `balance`, `start/stop/stopbuy`, `available_pairs`, `reload_config`,
`show_config`, etc. Es la capa que los agentes usarán para OPERAR (feature 003 pendiente).

---

## 5. Formato de datos

### Vector store por bloque (`data/rag/<id>/`, gitignored)

- **`chunks.json`**: `[{id, block, mirror, path, heading, heading_path, text, char_len}]`
  - `id` = `sha1(mirror|path|idx)` — determinista, clave de upsert
  - `mirror` = `"fuente"` | `"web"`
- **`vectors.npy`**: `np.float32` 2D `[n_chunks, dim]`, fila i ↔ chunk i
- **`index.json`** (manifiesto):
  ```json
  {"block": "02-configuracion", "embed_model": "gemini:gemini-embedding-001",
   "embed_base_url": null, "dim": 768, "chunk_count": 118,
   "mirror_counts": {"fuente": 54, "web": 64},
   "content_hash": "...", "min_score": 0.25, "built_at": "..."}
  ```

### Respuesta de `responder` (agente, JSON)

```json
{
  "respuesta": "texto del LLM fundamentado en los chunks...",
  "citas": [{"chunk_id": "...", "mirror": "web", "path": "backtesting.md",
             "heading": "Backtesting", "score": 0.4141}],
  "estado": "ok" | "sin_hits" | "degradado_llm"
}
```

- `sin_hits`: no se llamó al LLM; rechazo explícito (ahorro de crédito).
- `degradado_llm`: el LLM falló tras retry; se devuelven los hits crudos.

### Hit de `consultar_docs` (RAG puro, JSON list)

```json
[{"chunk_id": "...", "block": "04-backtesting", "mirror": "web",
  "path": "backtesting.md", "heading": "Backtesting",
  "heading_path": "Backtesting", "text": "...", "score": 0.41}]
```

---

## 6. Backends de embeddings (cascada)

| Prioridad | Backend | Condición | Dimensión |
|---|---|---|---|
| 1 | **Google Gemini** `gemini-embedding-001` | `GEMINI_API_KEY` en `.env` | 768 (configurable `GEMINI_EMBED_DIM`) |
| 2 | **Gateway LiteLLM/Bifrost** | `EMBED_BASE_URL` + `EMBED_MODEL` responden | la del modelo |
| 3 | **local-hash** (determinista, sin red) | siempre (fallback) | 384 |

- El **Retriever auto-detecta** el backend del índice (si el índice es gemini, usa
  Gemini; si es local-hash, usa local) — cada bloque se consulta con SU backend.
- Validación de dimensión: antes (constructor) y después (post-embed) de cada consulta;
  si el proveedor degrada a mitad de camino (p.ej. rate limit), error claro en vez de
  matmul críptico.
- **Rate limit del free tier de Gemini**: ~100 req/min, ~1000/h. El indexador usa batch
  32, sleep 3s entre batches y retry con backoff que lee el `retry in Ns` del error 429.

---

## 7. LLM de los agentes (gateway)

- **Gateway**: LiteLLM en `http://localhost:4000/v1` (compat OpenAI). 21 modelos
  disponibles (deepseek-v4-flash/pro, deepseek-via-inference(-pro), kimi-k3, grok-4.6,
  glm-5.3, gemini-3.7-flash, nvidia-nemotron, gpt-oss...).
- **Modelo por bloque**: env `AGENT_MODEL_<BLOQUE_ID_UPPER_SIN_GUION>` (ej.
  `AGENT_MODEL_02_CONFIGURACION`), default `AGENT_MODEL_DEFAULT=deepseek-via-inference`.
- **Pitfall conocido**: `max_tokens` bajo → el modelo devuelve `content: ""` (el
  razonamiento consume el presupuesto). El agente usa `max_tokens=2000` y extrae SOLO
  `message.content` (ignora `reasoning_content`).

---

## 8. Forma de uso (comandos)

```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq
unset PYTHONPATH   # OBLIGATORIO: el PYTHONPATH global de Hermes contamina

# --- Indexar ---
.venv/Scripts/python.exe tools/index_blocks.py                 # los 12 bloques
.venv/Scripts/python.exe tools/index_blocks.py 02-configuracion --force  # uno, forzado

# --- Consultar RAG puro (CLI) ---
.venv/Scripts/python.exe tools/query_block.py 04-backtesting "how to run backtesting"

# --- Agente LLM (CLI directo) ---
.venv/Scripts/python.exe tools/demo_entender_doc.py

# --- MCP servers (stdio; para Hermes u otro cliente MCP) ---
.venv/Scripts/python.exe servers/run_bloque.py 04-backtesting   # RAG puro
.venv/Scripts/python.exe servers/run_agente.py 04-backtesting   # agente LLM

# --- Benchmark ---
.venv/Scripts/python.exe tools/benchmark_rag.py 02-configuracion  # → data/benchmark/

# --- Tests ---
.venv/Scripts/python.exe -m pytest tests/ -q

# --- Smokes (protocolo MCP real) ---
.venv/Scripts/python.exe tools/smoke_mcp_stdio.py
.venv/Scripts/python.exe tools/smoke_agente_stdio.py
```

**Reglas de entorno (Windows/MSYS)**:
- Usar `.venv/Scripts/python.exe` (el `python` del PATH es el venv de Hermes con mcp 2.0.0,
  que rompió `mcp.server.fastmcp`).
- Nunca `python -c` inline (bloqueado por el approval gate) — scripts como archivo.
- `/tmp` de MSYS falla para curl → usar `$LOCALAPPDATA/Temp`.

### Registro en Hermes (MCP)

```yaml
mcp_servers:
  freq_config:
    command: C:\Users\P0zcl\Desktop\proyectos\freq\.venv\Scripts\python.exe
    args:
      - C:\Users\P0zcl\Desktop\proyectos\freq\servers\run_agente.py
      - 02-configuracion
    enabled: true
```

Luego `/reload-mcp` en Hermes. Tools: `mcp_freq_config_responder`,
`mcp_freq_config_consultar_docs`, `mcp_freq_config_health`. (Pendiente: requiere OK
del usuario para tocar `config.yaml` de Hermes.)

---

## 9. Configuración (`.env`, gitignored — ver `.env.example`)

```bash
# Embeddings
EMBED_BASE_URL=http://localhost:4000
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=            # key del gateway (opcional)
GEMINI_API_KEY=...        # key Google (free tier) — prioridad 1
GEMINI_EMBED_MODEL=gemini-embedding-001
GEMINI_EMBED_DIM=768

# Agente LLM
LLM_BASE_URL=http://localhost:4000/v1
LLM_API_KEY=...           # master key local del gateway
AGENT_MODEL_DEFAULT=deepseek-via-inference
# AGENT_MODEL_02_CONFIGURACION=deepseek-v4-pro   # por bloque, opcional

# RAG
RAG_DATA_DIR=data/rag
RAG_MIN_SCORE=0.25
CHUNK_MAX_CHARS=2000
CHUNK_OVERLAP_CHARS=200
```

---

## 10. Estado actual (2026-08-30)

| Componente | Estado |
|---|---|
| Corpus (2 mirrors, 95 .md, ~2 MB) | Operativo |
| Indexación 12 bloques | Operativa (00, 01, 02 en Gemini semántico; 03-11 en local-hash, pendientes de reindexar cuando la cuota horaria de Gemini se recupere) |
| RAG por bloque (consultar_docs, health) | Operativo, 26/26 tests |
| Agente LLM por bloque (responder + citas) | Operativo (patrón validado en piloto; replicable por bloque vía env) |
| MCP stdio | Operativo (smokes reales OK) |
| Benchmark | Baseline local-hash: recall@1=0.30, recall@3=0.85, MRR=0.567 (falta medir con Gemini) |
| Wrapper REST freqtrade (prototype/) | Construido, 19 tools, validado — NO integrado aún |
| Registro en Hermes | Pendiente (requiere OK del usuario) |
| **Operación de trading (feature 003)** | **Pendiente**: conectar agentes ↔ wrapper REST + Manager orquestador + cadena dry-run → live (solo con OK explícito del usuario) |

### Qué puede hacer un LLM HOY

- Consultar la documentación de cualquier bloque (RAG, con o sin citas del LLM).
- Preguntar en lenguaje natural y recibir respuestas fundamentadas con citas.
- Verificar el estado de los índices (health).
- Medir la calidad de recuperación (benchmark).

### Qué NO puede hacer todavía

- Ejecutar órdenes sobre freqtrade (forceenter/forceexit/blacklist...) — el wrapper
  existe pero no está conectado a los agentes.
- Orquestar el flujo completo (datos → estrategia → backtest → hyperopt → riesgo).
- Pasar de dry-run a live (regla dura: solo con OK explícito del usuario).

---

## 11. Gobernanza (Spec-Driven Development)

- **Constitution**: `.specify/memory/constitution.md` — 5 principios (doc-as-org-chart,
  aislamiento RAG, Safe-Operation Gate, portabilidad, spec-driven).
- **Specs**: `specs/001-framework-rag-mcp/` (RAG+MCP) y `specs/002-agentes-llm-bloque/`
  (agentes LLM) — cada una con spec, plan, research, data-model, contracts, tasks.
- **Flujo**: `/speckit.constitution → specify → plan → tasks → implement`.
- **Regla de seguridad dura**: nunca arriesgar capital real, publicar o gastar crédito
  sin OK explícito del usuario (constitution III).

---

## 12. Problemas conocidos y lecciones (para no repetir)

1. **`python` del PATH = venv de Hermes (mcp 2.0.0)** — rompe `mcp.server.fastmcp`.
   Usar SIEMPRE `.venv/Scripts/python.exe` del proyecto (mcp 1.29.1).
2. **Rate limit free tier de Gemini** (100/min, 1000/h) — reindexar con `--force` en
   lote puede agotarlo; los bloques quedan en local-hash (funcional, menos preciso).
   Esperar la ventana (~1 h) y reintentar.
3. **`max_tokens` bajo en deepseek-via-inference → `content: ""`** — usar ≥ 2000.
4. **mcp 1.29 `call_tool` devuelve tupla** `(content_blocks, meta)` → `result[0][0].text`.
5. **El corpus es 100% inglés** — con local-hash, queries en español dan no-hits;
   con Gemini (semántico, multilingüe) deberían recuperar. A medir en benchmark.
6. **Los tests usan un RAG_DATA_DIR temporal** (conftest.py) — nunca tocan producción.
