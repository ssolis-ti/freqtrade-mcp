# Research — Fase 0: Framework RAG-por-bloque + MCP por bloque

**Feature**: `001-framework-rag-mcp` | **Fecha**: 2026-08-30 | **Plan**: `plan.md`

## Hallazgos del entorno (verificado en vivo)

### Python del proyecto (3.11.15)

| Dependencia | Estado | Uso |
|---|---|---|
| `openai` 2.24.0 | ✅ | Cliente de embeddings compat con LiteLLM/Bifrost |
| `mcp` | ✅ | SDK MCP (FastMCP `mcp.server.fastmcp`) |
| `markdownify`, `bs4` 4.15.0 | ✅ | Mirror web + parsing |
| `fastapi` 0.133.1, `uvicorn` 0.41.0 | ✅ | (opcional, para servers HTTP) |
| `chromadb` | ❌ no instalado | — |
| `sqlite_vec` | ❌ no instalado | — |
| `faiss` | ❌ no instalado | — |
| `sentence_transformers` | ❌ no instalado | — |

### Endpoint de embeddings (probe en vivo)

| Endpoint | Resultado |
|---|---|
| `http://localhost:4000/v1/embeddings` (text-embedding-3-small / ada-002) | **401 Unauthorized** → requiere `EMBED_API_KEY`/auth header |
| `http://localhost:8080/v1/models` (Bifrost) | **conexión denegada** (WinError 10061) → Bifrost no corriendo ahora |

**Lectura**: el cliente de embeddings debe soportar auth por API key (default para
LiteLLM/Bifrost), degradar con fallback local, y no asumir que el gateway está up.

## Decisiones técnicas (basadas en los hallazgos)

### 1. Vector store sin chromadb (ligero y portable)
Para el MVP no hace falta chromadb. Cada bloque tiene ~50-80 chunks; la búsqueda de
similitud de coseno sobre los embeddings con `numpy` es O(n) y corre en microsegundos.
**Diseño**: cada bloque guarda un **manifesto plano** en `data/rag/<bloque>/`:
- `chunks.json` — lista de chunks `{id, bloque, mirror, path, text, heading}`
- `vectors.npy` (o `vectors.json`) — 2D array float de embeddings (fila i ↔ chunk i)
- `index.json` — metadatos: modelo de embeddings, dim, contadores por mirror, hash

Recuperación: coseno(query, vector) → top-k por score descendente. Reindexación:
reemplazo idempotente (hash determinista por chunk; si el hash no cambia, se reusa).

> Si en el futuro el corpus crece mucho, migrar a chromadb/faiss es un cambio interno del
> módulo `retriever`, no del contrato MCP. YAGNI ahora.

### 2. Embeddings por env con fallback local (constitution IV)
- `.env`: `EMBED_BASE_URL=http://localhost:4000`, `EMBED_MODEL=text-embedding-3-small`,
  `EMBED_API_KEY=mi-key`. **Todo configurable por env**; el default es solo sugerencia.
- `embeddings.py`: intenta el endpoint (timeout corto ~10s, auth por `EMBED_API_KEY`).
  Verificado en vivo: `:4000` responde pero devuelve **401** sin key, y `:8080` (Bifrost)
  **no está corriendo** → el fallback local es obligatorio, no opcional.
- Si el gateway falla (401/red/timeout), **degrada a `local-hash`**: embedding
  determinista bag-of-words hasheado (md5 de tokens → índices, L2-normalizado), dim fija
  (ej. 384). Cero dependencias. Documentar la limitación (recuperación aproximada, no
  semántica real) en el docstring.

> Alternativa futura si se quieren embeddings de calidad local: instalación opcional de
> `sentence-transformers` (dependencia pesada ~100MB+). No para el MVP.

### 3. Chunking por cabeceras markdown
`configuration.md` (58K) → dividir por `##` / `###` (top-level H2 heading). Cada chunk
heredan el heading como contexto y se referencia al heading padre. Hash id =
`sha1(mirror|path|heading_index)`.

### 4. MCP server genérico por bloque
`servers/run_bloque.py <bloque_id>` levanta un FastMCP con tools:
- `consultar_docs(query: str, top_k: int=3) -> list[{chunk_id, blocque, mirror, path,
  heading, score, text}]`
- `health() -> {bloque, chunks, mirror_counts, embed_model, indexed_ok}`

Registro Hermes: un entry `mcp_servers.<bloque>` por bloque (12 bloques + Manager),
siguiendo el patrón del wrapper REST existente.

## Riesgos / mitigaciones

| Riesgo | Mitigación |
|---|---|
| Gateway embeddings down | Fallback hash-embedding local determinista (siempre disponible) |
| Auth en LiteLLM | `EMBED_API_KEY` obligatoria; timeout corto; no asumir "no-need" |
| Config bloque piloto desactualizado | Reindexación manual idempotente vía `tools/index_blocks.py` |
| RAG alucinando fuera de corpus | No-hits explícito por umbral de score mínimo (`MIN_SCORE`) |

## Resultado

El framework es **realizable sin dependencias pesadas nuevas**: numpy (ya en openai deps)
+ openai client + MCP SDK + hashing. El MVP del bloque piloto `02-configuracion` se
implementa end-to-end y se registra en Hermes.

Pendiente de revisión por el usuario: Aceptación del enfoque vector-ligero (sin chromadb
ni sentence-transformers en el MVP).
