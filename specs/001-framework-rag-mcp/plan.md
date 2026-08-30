# Implementation Plan: Framework RAG-por-bloque + MCP por bloque

**Branch**: `001-framework-rag-mcp` | **Date**: 2026-08-30 | **Spec**: `specs/001-framework-rag-mcp/spec.md`

**Input**: Feature specification from `/specs/001-framework-rag-mcp/spec.md`

## Summary

Construir el framework que convierte la documentación oficial de freqtrade (12 bloques,
ambos mirrors) en la base de un sistema multi-agente: cada bloque se indexa (chunks +
embeddings) en un vector store aislado y se expone como un **MCP server FastMCP**
independiente con tools de RAG (`consultar_docs`, `health`). MVP del patrón end-to-end
sobre el bloque piloto `02-configuracion`, parametrizado por bloque para escalar a los 12
(FR-008). Embeddings vía LiteLLM/Bifrost `:4000` configurable por env, con fallback local
determinista. Al final, el MCP queda registrable en Hermes como empleado persistente.

## Technical Context

**Language/Version**: Python 3.11 (y 3.14 disponible); import desde `mcp.server.fastmcp`.

**Primary Dependencies**:
- `mcp>=1.27,<2.0` (2.x rompió `mcp.server.fastmcp`)
- `numpy` (vector store ligero — coseno, sin chromadb/faiss) — **ya instalado**
- `openai` 2.24.0 (cliente compat con LiteLLM/Bifrost para embeddings) — **ya instalado**
- `python-dotenv` (cargar `.env`; **instalar si falta**)
- `pytest` (tests; **NO instalado** — instalar en venv de proyecto, o runner manual)
- NO `chromadb`/`faiss`/`sentence-transformers`/`sklearn` (pesados, YAGNI para MVP)
- stdlib (`pathlib`, `hashlib`, `json`)

**Storage**: Vector store por bloque, **ligero sin chromadb**: `numpy` + coseno. Cada
bloque en `data/rag/<bloque>/`: `chunks.json` (metadatos + texto), `vectors.npy`
(float32 2D), `index.json` (manifiesto con mirror_counts, content_hash, min_score).

**Testing**: `pytest`. Test de humeo por server MCP (tools/list + consulta). Test de
reindexación (idempotencia). No usamos `python -c` inline (bloqueado por approval gate) —
los tests corren como archivos.

**Target Platform**: Windows (desarrollo), esquema portable para Linux (Docker).

**Project Type**: framework/library + MCP servers (servicios persistibles).

**Performance Goals**: Recuperación top-k < 1s en corpus de un bloque (~10-60 chunks).
Indexación de un bloque < 30s.

**Constraints**:
- Bloque piloto `02-configuracion` (`configuration.md` 58K / 64K web). Verificado: 26
  cabeceras; la sección `### Parameters table` tiene **24,626 chars** → el chunking DEBE
  subdividir recursivamente cualquier chunk > MAX_CHARS (~2000) en párrafos con solape
  (~200). Estimación: ~80-140 chunks entre ambos mirrors.
- `unset PYTHONPATH` antes de correr cualquier Python de proyecto (venv Hermes global
  contamina).
- Ejecutar scripts como archivo (`python tools/x.py`), jamás `python -c`.
- `/tmp` de MSYS falla para curl → usar `$LOCALAPPDATA/Temp`.
- MCP servers corren `transport="stdio"` para Hermes.

**Scale/Scope**: MVP = 1 bloque piloto end-to-end; arquitectura lista para 12 bloques y
13 MCP servers (12 bloques + Manager) por repetición del patrón.

## Constitution Check

*GATE: debe pasar antes de la investigación (Fase 0).*

- ✅ **I. Documentation-as-Org-Chart** — el RAG indexa exactamente los bloques doc; cada
  bloque = fuente de verdad. Sin desviación.
- ✅ **II. RAG-Block Isolation** — vector store aislado por bloque, nunca compartido;
  no-hits explícito.
- ✅ **III. Safe-Operation Gate** — este feature solo INDEXA y CONSULTA docs; NO toca
  superficie live ni riesga capital. Sin conflicto.
- ✅ **IV. Portability** — embeddings por env con fallback local; sin rutas absolutas.
- ✅ **V. Spec-Driven** — desarrollo desde spec; tests antes de implementar.

Sin violaciones. **PASA.**

## Project Structure

### Documentation (this feature)

```text
specs/001-framework-rag-mcp/
├── plan.md              # este archivo
├── research.md          # (Fase 0)
├── data-model.md        # (Fase 1)
├── quickstart.md        # (Fase 1)
├── contracts/           # (Fase 1)
├── checklists/requirements.md
└── tasks.md             # (/speckit-tasks, Fase 2)
```

### Source Code (repository root)

```text
freq/
├── rag/                         # núcleo del framework
│   ├── __init__.py
│   ├── config.py                # constante por bloque + env (EMBED_*, RAG_DATA_DIR)
│   ├── chunking.py              # dividir .md en chunks (por cabeceras ##/###) con hash id
│   ├── embeddings.py            # cliente embeddings env-config + fallback local
│   ├── indexer.py               # indexar un bloque (ambos mirrors) → vector store
│   ├── retriever.py             # consulta top-k sobre un vector store
│   └── blocks.py                # catálogo de 12 bloques (id → rutas mirrors)
├── servers/                     # un MCP server por bloque
│   ├── __init__.py
│   ├── block_mcp.py             # FastMCP genérico: consultar_docs + health
│   └── run_bloque.py            # entrypoint: python run_bloque.py 02-configuracion
├── data/rag/                    # vector stores por bloque (gitignored)
│   └── 02-configuracion/
├── tools/                       # utilidades de CLI
│   ├── index_blocks.py          # indexar bloc(es) desde CLI
│   └── query_block.py           # probar consulta sin MCP
├── prototype/freqtrade-mcp/     # (existente, intacto)
├── docs-freqtrade/              # (existente)
├── docs-freqtrade-web/          # (existente)
├── tests/
│   ├── test_chunking.py
│   ├── test_indexer.py
│   └── test_retriever.py
├── requirements.txt
└── .env.example
```

**Structure Decision**: Se elige el patrón de **un solo proyecto** con subpaquetes
`rag/` (núcleo) y `servers/` (MCP por bloque). Estructura plana y portable; un bloque =
un directorio de corpus + un vector store + un server. El `freqtrade-mcp` wrapper
existente (tool-only REST) se mantiene intacto y convive como el "despacho" de los
agentes; este feature añade el "cerebro" (RAG por bloque).

## Complexity Tracking

> Solo si la Constitution Check tiene violaciones que justificar.

Sin violaciones. **N/A.**

## Fases (boilerplate del workflow)

- **Fase 0**: research — confirmar librería de embeddings disponible, chromadb, y el
  chunking por cabeceras sobre `configuration.md`.
- **Fase 1**: diseño — data-model (chunk/vector/metadatos), contracts (interfaces MCP),
  quickstart.
- **Fase 2**: tareas (ver `tasks.md`, /speckit-tasks).
- **Fase 3**: implementación (ver `plan.md` fases de código en `tasks.md`).
