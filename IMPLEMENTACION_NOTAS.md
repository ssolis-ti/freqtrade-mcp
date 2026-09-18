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

## Seguridad (2026-08-30)

- La key real de Gemini se coló temporalmente en `.env.example` (archivo versionado)
  durante las pruebas y quedó en el historial de git. **Purgada**: historial reescrito
  con filter-branch (0 coincidencias de la key en todo el historial), refs originales
  eliminados, gc ejecutado. El repo no tiene remoto (la key nunca salió del equipo).
- `.env.example` usa placeholders; la key real vive SOLO en `.env` (gitignored).
- Recomendado: rotar la key en https://aistudio.google.com/apikey (gratis, 1 min).

## Feature 003 — Despacho operativo (2026-08-30)

**Estado: IMPLEMENTADO con mocks (48/48 tests; smoke MCP despacho OK).**
Integración real con freqtrade Docker dry-run pendiente (T326-T330, requiere OK).

### Entregado

- `despacho/wrapper.py` — FreqtradeClient (19 tools REST extraídas del prototype, auth
  JWT, relogin 401, verificar_dry_run).
- `despacho/permisos.py` — gate de OK (regla dura, doble capa agente+Manager).
- `despacho/manager.py` — plan_mision (LLM gateway + fallback heurístico),
  decidir_dry_run solo con backtesting+riesgo OK, bloqueos.
- `despacho/cadena.py` — cadena dry-run (download-data → backtesting con umbrales
  PF≥1.3/DD≤30% → hyperopt → revisar_riesgo; subprocess freqtrade).
- `servers/despacho_mcp.py` + `run_despacho.py` — MCP del despacho (19 tools).
- Tests: test_wrapper (6), test_permisos (4), test_manager (6), test_cadena (6).
- `tools/smoke_despacho.py` — smoke con mocks: TOOLS 19, gate OK verificado
  (entrar sin OK → ToolError), plan_mision 3 pasos.
- `.env.example` + FREQTRADE_*, CADENA_PF_MIN/DD_MAX.

### Pendiente (integración real, requiere OK del usuario)

- T326: `tools/levantar_freqtrade.sh` — docker run freqtrade dry-run con REST.
- T327: smoke real (bot_status/profit; forceenter con OK en par de prueba).
- T328: cadena real en dry-run.
- T329: registro Hermes (freq_despacho) + /reload-mcp.
- T330: suite completa + commit.

## Cierre de sesión — cómo retomar (2026-08-30)

**Estado: base completa y operativa** (features 001-003 con mocks, 48/48 tests, tree limpio).

### Para retomar en cualquier sesión (LLM o humano)

1. Leer `docs/ARQUITECTURA.md` (documento maestro) + `README.md` (mapa).
2. Entorno: `cd /c/Users/P0zcl/Desktop/proyectos/freq && unset PYTHONPATH` y usar
   `.venv/Scripts/python.exe` (nunca `python` del PATH: es el venv de Hermes con mcp 2.0).
3. Estado de índices: `tools/verificar_indices.py` (03-11 pueden estar en local-hash si
   la cuota de Gemini no se ha reindexado: `tools/index_blocks.py --force` cuando haya cuota).

### Próximos pasos pendientes (en orden)

| # | Pendiente | Cómo | Requiere |
|---|---|---|---|
| 1 | Reindexar 03-11 con Gemini | `tools/index_blocks.py --force` (esperar cuota horaria) | tiempo (~1h de espera) |
| 2 | Benchmark con Gemini | `tools/benchmark_rag.py 02-configuracion` (índice ya en gemini) | nada |
| 3 | Rotar key de Gemini (higiene) | aistudio.google.com/apikey + actualizar `.env` | usuario |
| 4 | Integración real freqtrade (T326-T330) | Docker dry-run + smoke + cadena + registro Hermes | OK usuario + Docker |
| 5 | Registro Hermes (T033 + T329) | entries en config.yaml + `/reload-mcp` | OK usuario |

### SDD

- Specs: `specs/001-framework-rag-mcp/`, `specs/002-agentes-llm-bloque/`,
  `specs/003-despacho-operativo/` (tasks T301-T325 hechas, T326-T330 pendientes).
- Constitution: `.specify/memory/constitution.md`.

### Graphify (evaluación, 2026-09-18)

Ver `docs/graphify-evaluacion.md`. Resumen:
- `graphify` 0.9.57 + extras `[mcp,gemini]` instalado; `graphify-mcp` expone 10 tools.
- **Código → SÍ** (validado: `graphify extract . --code-only` ⇒ 468 nodos / 939 edges /
  98% EXTRACTED / $0 local). El grafo del código ya está en `graphify-out/` (gitignored).
- **Docs → pendiente de verificar**: la 1ª corrida falló por rate limit de Gemini
  (5 req/min free tier), no por incapacidad. El reintento con el gateway local quedó
  **bloqueado por entorno** (Docker Desktop apagado ⇒ gateway LiteLLM `:4000` caído,
  `Connection error`). Reintentar con Docker + gateway arriba (comandos exactos en
  `docs/graphify-evaluacion.md`).
- Comandos clave:
  ```bash
  graphify extract . --code-only --no-viz     # código propio: 468 nodos, $0
  graphify cluster-only .                     # GRAPH_REPORT.md + comunidades
  graphify export html                        # graph.html navegable
  .venv/Scripts/python.exe tools/probe_graph_code.py   # stats + god_nodes + query
  ```

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

---

## Sesion 2026-09-18 — repo remoto + fase 1 de endurecimiento

### Contexto de uso (aclarado por el usuario)

El sistema se usa como **centro de conocimiento para IA**: RAG de los 12 bloques
documentales + grafo del codigo, con especialistas agenticos por area para cubrir
un proyecto tan extenso como freqtrade. La capa de EJECUCION (entrar/salir/vetar)
es secundaria: por defecto ni se registra (el gateway arranca solo-lectura).

### Hecho

1. **Repo remoto**: `github.com/ssolis-ti/freqtrade-mcp` (privado). Historial
   auditado antes de subir: sin `.env`, sin claves. README con seccion
   "Clonar en otra maquina" (los indices y el grafo no se versionan).
2. **Fase 1 de seguridad** (commit `834bb96`, 11 tests nuevos):
   - `cadena.backtesting` ahora falla CERRADO: metrica ausente = rechazo.
   - `permisos.exigir_dry_run()` nuevo y cableado en las 7 tools del despacho y
     las 4 del gateway. `verificar_dry_run` existia pero no lo llamaba nadie.
     Live exige `PERMITIR_LIVE=1` en el entorno del proceso (no via tool).
   - Gateway: auth Bearer real (antes el docstring la anunciaba y no existia),
     default loopback, aborta si se pide interfaz de red sin key.
3. **Bug del indexador**: si Gemini agota la cuota a mitad del corpus, los
   primeros lotes salen dim 768 y el resto 384 -> numpy fallaba con
   "inhomogeneous shape" y el bloque no se reindexaba. Ahora detecta la mezcla,
   re-embebe todo con el backend ya degradado y deja el indice homogeneo; si aun
   asi no cuadra, aborta sin tocar el indice anterior.
4. **`verificar_indices.py`** recorre los 12 bloques (antes 4 hardcodeados) y
   resume cuales siguen en local-hash.

### Pendiente inmediato

- **Reindexar 03-11 con Gemini**: intentado hoy, cuota agotada (429,
  `embed_content_free_tier_requests` limit 100). Los 9 bloques siguen en
  local-hash — funcional pero sin recuperacion semantica (y las preguntas en
  espanol rinden mal, el corpus es ingles). Reintentar con cuota:
  `tools/index_blocks.py --force`, y verificar con `tools/verificar_indices.py`.
- **Gate de OK por operacion** (F1.4): `ok_usuario` sigue siendo parametro de
  tool, asi que el LLM se autoriza solo. Contenido hoy por dry-run + flag de
  proceso. Si algun dia se opera de verdad, mover la aprobacion fuera de banda.
- Fases 2-6 del plan: benchmark de los 12 bloques, cadena real, instancia
  freqtrade Docker, auditoria + preflight, CI del repo.
