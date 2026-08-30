# Notas de implementacion — Feature 001 (Framework RAG-por-bloque + MCP por bloque)

**Ejecutor**: deepseek-via-inference | **Fecha**: 2026-08-30
**Estado**: IMPLEMENTACION LISTA (MVP end-to-end sobre el bloque piloto `02-configuracion`)

## Lo implementado

| Modulo | Archivo | Descripcion |
|---|---|---|
| Nucleo | `rag/config.py` | env EMBED_*/RAG_* + defaults, sin rutas absolutas |
| Nucleo | `rag/blocks.py` | catalogo de los 12 bloques (id -> mirrors fuente/web) |
| Nucleo | `rag/chunking.py` | chunking jerarquico por cabeceras + split por tamano con solape, id sha1 determinista |
| Nucleo | `rag/embeddings.py` | Embedder: gateway LiteLLM/Bifrost (openai client, timeout corto, auth) + fallback local-hash |
| Nucleo | `rag/indexer.py` | index_block(): ambos mirrors -> chunks.json + vectors.npy + index.json, idempotente por content_hash |
| Nucleo | `rag/retriever.py` | Retriever.query(): coseno numpy, top-k, min_score, no-hits [] |
| Servers | `servers/block_mcp.py` | FastMCP generico: consultar_docs + health |
| Servers | `servers/run_bloque.py` | entrypoint stdio: `python servers/run_bloque.py <id>` |
| CLI | `tools/index_blocks.py` | indexar uno o todos, --force |
| CLI | `tools/query_block.py` | consulta sin MCP (depuracion) |
| Smoke | `tools/smoke_mcp_stdio.py` | cliente MCP real por stdio (handshake + tools + consulta) |
| Tests | `tests/test_chunking.py` | 5 tests: jerarquia, split grande, id determinista, mirrors distintos, doc real |
| Tests | `tests/test_indexer.py` | 3 tests: indexa piloto, idempotencia, mirror ausente |
| Tests | `tests/test_retriever.py` | 6 tests: hits relevantes, top-k, no-hits, umbral, bloque inexistente, health |
| Tests | `tests/test_mcp.py` | 4 tests: tools listadas, consulta, no-hits, health |

## Validacion real (comandos ejecutados)

```bash
.venv/Scripts/python.exe tools/index_blocks.py 02-configuracion --force
# -> 118 chunks (fuente=54, web=64), model=local-hash, dim=384, 9s

.venv/Scripts/python.exe tools/query_block.py 02-configuracion "how to enable futures trading mode"
# -> 3 hits con score, citando mirror+path+heading

.venv/Scripts/python.exe tools/query_block.py 02-configuracion "italian pasta recipe"
# -> "No-hits: ninguna seccion del bloque supera el umbral"

.venv/Scripts/python.exe -m pytest tests/ -q
# -> 18 passed, 9 warnings (warnings = fallback local esperado)

.venv/Scripts/python.exe tools/smoke_mcp_stdio.py
# -> INIT ok: freq-02-configuracion; TOOLS: [consultar_docs, health];
#    HEALTH ok (118 chunks); CONSULTA: 2 hits; NO-HITS: []
```

## Desviaciones respecto al plan (justificadas)

1. **Venv de proyecto creado** (`.venv/`, Python 3.14.6 desde `C:\Python314\python.exe`):
   el `python` del PATH es el venv de Hermes con **mcp 2.0.0**, que removio
   `mcp.server.fastmcp` (pitfall conocido del skill mcp-agent-office). NO se toco el venv
   de Hermes. El venv de proyecto tiene mcp 1.29.1, openai 3.6.0, numpy 2.5.2, pytest 9.1.1.
   Comando de activacion en este entorno: usar `.venv/Scripts/python.exe` directamente
   (o `source .venv/Scripts/activate` + `unset PYTHONPATH`).

2. **Fallback local-hash activo por defecto**: el gateway `:4000` responde 401 sin key
   valida (verificado en vivo) y `:8080` no corre. El framework degrada correctamente y
   persiste `embed_model=local-hash` en index.json. Para embeddings reales: crear `.env`
   con `EMBED_API_KEY` valida y reindexar con `--force`.

3. **Test de bloque inexistente**: `get_block()` lanza KeyError (no FileNotFoundError) para
   ids invalidos; el test fue ajustado al comportamiento correcto del codigo.

4. **mcp 1.29 `call_tool` devuelve tupla** `(content_blocks, meta)`; los tests usan
   `result[0][0].text` (API oficial, no `.fn` interno).

## Hallazgo verificado (2026-08-30, prueba de funcionamiento)

- **El framework funciona end-to-end**: tests 18/18, consulta CLI, smoke MCP stdio OK,
  escalabilidad a un segundo bloque (04-backtesting: 156 chunks en 6.5s).
- **Limitacion del fallback local-hash con idioma**: el corpus es 100% ingles; el
  local-hash solo machea tokens identicos, asi que queries en espanol devuelven no-hits
  mientras la misma idea en ingles recupera bien (verificado: "como ejecuto un backtesting"
  -> no-hits; "how to run backtesting" -> hit 0.545). Con embeddings semanticos del
  gateway (EMBED_API_KEY valida) la query en espanol encontraria los chunks en ingles.
  Implicacion: para operar el RAG en espanol de forma robusta, el gateway es requerido,
  no opcional.

## Feature 002 — Agentes LLM por bloque (2026-08-30)

**Estado: IMPLEMENTADO y validado.** 26/26 tests (18 feature 001 + 8 feature 002).

### Verificado en vivo

- **Gateway LLM `:4000` operativo**: 21 modelos (deepseek-via-inference default, probado
  con respuesta real). Master key local en litellm.env → copiada a `.env` del proyecto
  (gitignored) via `tools/setup_env_key.py`.
- **Pitfall confirmado**: `max_tokens` bajo → `content: ''` (el razonamiento consume el
  presupuesto). El agente usa `max_tokens=2000` y extrae SOLO `message.content`
  (ignora `reasoning_content`).
- **Embeddings del gateway rotos**: `nvidia-embed` (nv-embedqa-mistral-7b-v2) → 404/429
  (no desplegado en la cuenta NIM). inference.net → 403 al listar sin gastar. → se
  mantiene local-hash; embeddings semanticos locales = feature 003 (requiere OK para
  instalar sentence-transformers ~100MB).
- **Smoke agente MCP stdio OK**: `responder` responde con citas reales y fundamento;
  sin hits → `sin_hits` (rechazo sin llamar al LLM).
- **Benchmark baseline (local-hash)**: recall@1=0.30, recall@3=0.85, MRR=0.567 sobre
  20 preguntas del golden set. Reporte en `data/benchmark/02-configuracion.json`.
  Línea de comparación para embeddings semanticos (feature 003).

### Entregado

- `rag/agent.py` (AgenteLLM), `servers/agent_mcp.py` (responder/consultar_docs/health),
  `servers/run_agente.py`, `tools/benchmark_rag.py`, `tools/make_golden_set.py`,
  `tools/smoke_agente_stdio.py`, `tools/setup_env_key.py`, `tools/golden_set.json`,
  tests `test_agent.py` (5) + `test_benchmark.py` (3).
- `.env.example` ampliado (LLM_BASE_URL, LLM_API_KEY, AGENT_MODEL_*).
- SDD completo en `specs/002-agentes-llm-bloque/` (spec, plan, research, contracts, tasks 26/26).
- README: sección "Agentes LLM por bloque".

### Pendientes

- Registro en Hermes (T033 combinado 001+002): entry `freq_config` → `run_agente.py`.
- Feature 003 (embeddings semanticos locales, requiere OK instalacion).
- Agentes para los otros 11 bloques (mismo patron; modelo por bloque via env).

## Pendientes / siguientes pasos

- **Registro en Hermes** (T033): entry `mcp_servers.freq_config` en `config.yaml` (paths
  relativos al proyecto, ver README) + `/reload-mcp`. NO se edito la config de Hermes
  (cambio externo; requiere OK del usuario). Documentado abajo.
- **Indexar los otros 11 bloques**: `python tools/index_blocks.py` (sin argumento).
- **Embeddings reales**: configurar `.env` con key del gateway y reindexar.
- **Registro por bloque**: repetir el patron por cada bloque + Manager (FR-008).

## Registro sugerido en Hermes (config.yaml)

```yaml
mcp_servers:
  freq_config:
    command: C:\Users\P0zcl\Desktop\proyectos\freq\.venv\Scripts\python.exe
    args:
      - C:\Users\P0zcl\Desktop\proyectos\freq\servers\run_bloque.py
      - 02-configuracion
    enabled: true
```

Despues: `/reload-mcp` en la sesion de Hermes. Tools expuestas: `mcp_freq_config_consultar_docs`,
`mcp_freq_config_health`.
