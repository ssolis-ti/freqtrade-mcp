# PROMPT EJECUTOR — Framework RAG-por-bloque + MCP por bloque

> **Para deepseek-v4-flash.** Este es tu briefing completo para implementar el feature
> `001-framework-rag-mcp`. Tienes todo aquí para ejecutar sin preguntar. Si algo choca
> con la realidad (una lib no está, un path no existe), **ajusta y documenta** el cambio
> en `IMPLEMENTACION_NOTAS.md`, no te detengas ni pidas aclaración salvo bloqueo total.

---

## 0. Quién eres y tu trabajo

Eres el **ejecutor de código** de un framework ya planificado. Tu misión: implementar las
tareas T001–T033 de `specs/001-framework-rag-mcp/tasks.md` **siguiendo el orden y las
dependencias**, validando cada una con ejecución real. Al terminar, reportas qué
implementaste y qué comando corriste para validar.

**NO cambies la arquitectura.** Implementa según plan/spec/contracts. Si una decisión del
plan es inviable en la práctica, marca el cambio en `IMPLEMENTACION_NOTAS.md` (justifica)
y sigue adelante con la alternativa más cercana.

---

## 1. Entorno y reglas duras (no las rompas)

- **Working dir**: `C:\Users\P0zcl\Desktop\proyectos\freq` (desde MSYS bash:
  `cd /c/Users/P0zcl/Desktop/proyectos/freq`).
- **SIEMPRE** `unset PYTHONPATH` antes de correr Python de proyecto (el venv global de
  Hermes contamina imports).
- **Python**: `python` = 3.11.15 (el ejecutable del proyecto). NO `python -c` inline
  (bloqueado por approval gate) → todo script se ejecuta como archivo `python tools/x.py`.
- **`pytest` y `sklearn` NO están instalados.** Instala pytest en el venv del proyecto
  (NO global): `python -m pip install pytest`. Si el approval gate bloquea el install,
  haz los tests con un runner manual propio (`tests/run_tests.py` que importa y llama
  funciones de test) — documenta la elección.
- **`numpy` SÍ está instalado.** Úsalo para el vector store. NO instales chromadb,
  faiss, sentence-transformers (pesado, YAGNI para MVP).
- **`mcp` SDK**: versión compatible con FastMCP (`mcp>=1.27,<2.0`); importa
  `from mcp.server.fastmcp import FastMCP`.
- **Windows**: rutas con `/` forward-slash en Python. No uses `/tmp` (falla) →
  `$LOCALAPPDATA/Temp` si necesitas scratch.
- **Secretos**: nunca hardcodeados; `.env` (gitignored). `.env.example` sin valores reales.
- **Estilo del repo**: documentos sin emojis, sin datos reales, sin links internos.

## 2. Qué construyes (arquitectura ya fijada)

Framework que indexa los **12 bloques documentales** de freqtrade (ambos mirrors:
`docs-freqtrade/` fuente develop + `docs-freqtrade-web/` web stable) y expone cada bloque
como un **MCP server FastMCP** con RAG. **MVP end-to-end sobre el bloque piloto
`02-configuracion`**, parametrizado para escalar a los 12 (FR-008).

### Estructura a crear

```text
rag/
  __init__.py
  config.py        # env EMBED_* + RAG_DATA_DIR, sin rutas absolutas hardcodeadas
  blocks.py        # catálogo de 12 bloques: id -> {name, fuente_dir, web_dir}
  chunking.py      # chunk_markdown() jerárquico CON split por tamaño máx
  embeddings.py    # Embedder: gateway LiteLLM/Bifrost vía openai client + fallback local
  indexer.py       # index_block(): ambos mirrors -> chunks.json + vectors.npy + index.json
  retriever.py     # Retriever.query(): top-k por coseno numpy, min_score, no-hits []
servers/
  __init__.py
  block_mcp.py     # FastMCP genérico: consultar_docs(query, top_k) + health()
  run_bloque.py    # entrypoint: python servers/run_bloque.py 02-configuracion
tools/
  index_blocks.py  # CLI indexar (uno o todos, --force)
  query_block.py   # CLI consulta sin MCP (depuración)
tests/
  test_chunking.py, test_indexer.py, test_retriever.py, test_mcp.py
  run_tests.py     # runner manual si pytest no instalable
data/rag/<bloque>/ # gitignored; lo crea el indexador
requirements.txt   # actualizar
.env.example
.gitignore         # añadir data/ y .env
IMPLEMENTACION_NOTAS.md
```

### Datos clave del piloto (verificados)

- `docs-freqtrade/02-configuracion/configuration.md`: **57,961 chars, 26 cabeceras**;
  la sección `### Parameters table` tiene **24,626 chars** → demasiado grande para un
  chunk. `docs-freqtrade-web/02-configuracion/configuration.md`: 65,564 chars.
- Por eso el chunking DEBE: (a) dividir por cabeceras `##`/`###`, (b) **subdividir
  recursivamente cualquier chunk > MAX_CHARS (~2000)** en párrafos/ventanas con solape
  (~200 chars), heredando `heading_path`.

### Vector store (ligero, sin chromadb)

Por bloque en `data/rag/<id>/`:
- `chunks.json`: `[{id, block, mirror, path, heading, heading_path, text, char_len}]`
- `vectors.npy`: `np.float32` 2D `[n_chunks, dim]`, fila i ↔ chunk i
- `index.json`: `{block, embed_model, embed_base_url, dim, chunk_count, mirror_counts
  {fuente, web}, content_hash, built_at, min_score}`

Recuperación: coseno(query_vec, vectors) → top-k descendente; filtra `score >= min_score`
(default 0.25 aprox; config). **No-hits → devuelve `[]`** (nunca inventa).

### Embeddings (`rag/embeddings.py`)

Clase `Embedder`:
- `embed_texts(texts) -> list[list[float]]` (batch ≤16, timeout corto)
- `embed_query(q) -> list[float]`; `model_name()`; `dim()`
- **Backend primario**: `openai.OpenAI(base_url=EMBED_BASE_URL, api_key=EMBED_API_KEY)`
  → `client.embeddings.create(model=EMBED_MODEL, input=texts)`. Timeout (5,30).
- **Fallback local determinista** `local-hash` (dim fija, ej. 384): bag-of-words hasheado
  (md5 de tokens → índices) normalizado L2. Suficiente para recuperación aproximada MVP.
  Documenta su limitación en el docstring.
- Si gateway falla (401/red/timeout): log warning, activa fallback, `model_name()` =
  `"local-hash"`, y así se persiste en `index.json`.

### MCP server (`servers/`)

`block_mcp.py`: FastMCP con tools:
- `consultar_docs(query: str, top_k: int = 3) -> str` (JSON list de hits: chunk_id, block,
  mirror, path, heading, text, score). Devuelve `[]` JSON si no-hits.
- `health() -> str` (JSON: `{block, ok, chunk_count, mirror_counts, embed_model, dim}`).

`run_bloque.py`: parsea `sys.argv[1]` = block id, construye Retriever, levanta
`mcp.run(transport="stdio")`. Handshake: cliente debe `initialize` antes de `tools/list`.

### Catálogo de bloques (`rag/blocks.py`)

12 ids: `00-index, 01-instalacion, 02-configuracion, 03-estrategia, 04-backtesting,
05-hyperopt, 06-freqai, 07-riesgo-futuros, 08-control, 09-datos, 10-extensiones,
11-operativo`. Cada uno mapea a `docs-freqtrade/<id>/` y `docs-freqtrade-web/<id>/`
(recorrer recursivamente `.md`, incl. `includes/`).

## 3. Cómo ejecutas (orden y validación)

1. **T005–T008**: estructura + requirements + .gitignore + .env.example.
2. **Instala pytest** en venv (o runner manual si se bloquea).
3. **T009–T016 (Foundational)**: blocks, config, chunking, embeddings, indexer, retriever,
   CLIs. Ejecuta los CLIs para validar: `python tools/index_blocks.py 02-configuracion`
   debe crear `data/rag/02-configuracion/` con conteos > 0.
4. **Tests T001–T004** (escríbelos y hazlos pasar). Casos mínimos:
   - chunking: `Parameters table` se subdivide (ningún chunk > MAX_CHARS + solape); id
     determinista (mismo input → mismo id).
   - indexer: indexar 2x → mismo `chunk_count` (idempotente); `mirror_counts` suma.
   - retriever: una query con término real (ej. "futures trading mode") devuelve ≥1 hit
     con score; una query sin relación devuelve `[]` (o bajo min_score).
   - mcp: `health()` ok y `consultar_docs("stoploss")` devuelve lista JSON.
5. **T017–T029**: completa US1–US4 (no-hits explícito, upsert por hash, mirror ausente,
   errores `EMBED_FAIL`/`INDEX_MISSING`, fallback local).
6. **T030–T033 (Polish)**: valida quickstart end-to-end; indexa piloto; actualiza README
   con sección RAG-por-bloque (sin emojis/datos reales); verifica `.env` no se sube.

## 4. Validación final (debes correrla y reportarla)

```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq && unset PYTHONPATH
python tools/index_blocks.py 02-configuracion
python tools/query_block.py 02-configuracion "¿cómo activo trading de futuros?"
python tools/query_block.py 02-configuracion "receta de cocina italiana"   # esperado: []
python tests/run_tests.py    # o: python -m pytest -q  (si pytest instalado)
```

Reporta en tu resumen final: número de chunks indexados (fuente vs web), modelo de
embedding usado, resultado de cada comando de validación, y cualquier desviación
documentada en `IMPLEMENTACION_NOTAS.md`.

## 5. Restricciones de entrega

- NO subas nada a git remoto ni publiques; trabajo local solamente.
- NO ejecutes nada contra superficie live de trading (este feature es solo docs/RAG).
- Deja el bloque piloto indexado y `IMPLEMENTACION_NOTAS.md` con lo hecho + pendientes.
- Al terminar: reporta claramente "IMPLEMENTACION LISTA" + resumen para que el usuario
  cambie de modelo si quiere revisión.
