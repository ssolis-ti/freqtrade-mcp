# Tasks: Framework RAG-por-bloque + MCP por bloque

**Input**: Design docs de `/specs/001-framework-rag-mcp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp.md

## Test-Driven: escribir tests ANTES de implementar (Red) ⚠️

- [X] T001 [P] [foundation] Escribir tests que FALLAN en tests/test_chunking.py (chunking por cabeceras + hash id determinista)
- [X] T002 [P] [foundation] Escribir tests que FALLAN en tests/test_indexer.py (indexa bloque piloto, sin duplicados en reindex)
- [X] T003 [P] [foundation] Escribir tests que FALLAN en tests/test_retriever.py (top-k, umbral min_score, no-hits explícito)
- [X] T004 [P] [foundation] Escribir tests que FALLAN en tests/test_mcp.py (tools/list → consultar_docs + health; smoke end-to-end)

---

## Phase 1: Setup (Shared Infrastructure)

**Propósito**: estructura del proyecto + dependencias.

- [X] T005 Crear estructura `rag/`, `servers/`, `data/`, `tests/` en la raíz del proyecto
- [X] T006 Actualizar `requirements.txt` con `mcp>=1.27,<2.0`, `openai`, `numpy`
- [X] T007 [P] Actualizar `.gitignore` para excluir `data/rag/` y `.env`
- [X] T008 [P] Crear `.env.example` con `EMBED_BASE_URL`, `EMBED_MODEL`, `EMBED_API_KEY` (sin valores reales)

---

## Phase 2: Foundational (Bloquea todas las user stories)

**⚠️ Nada de user stories hasta que esta fase esté lista.**

- [X] T009 Crear `rag/blocks.py` — catálogo de 12 bloques documentales (id → rutas mirrors fuente+web + rag_dir)
- [X] T010 [P] Crear `rag/config.py` — leer env (EMBED_*) con defaults; `RAG_DATA_DIR`; helper de carga sin PYTHONPATH contaminado
- [X] T011 [P] Crear `rag/chunking.py` — `chunk_markdown(text, path, mirror)` → lista de chunk con id `sha1(mirror|path|heading_index)` (T001 lo verifica)
- [X] T012 Crear `rag/embeddings.py` — clase `Embedder` con backend env (LiteLLM/Bifrost :4000 vía openai) + fallback `local-hash` determinista
- [X] T013 Implementar `rag/indexer.py` — `index_block(block, force=False)` lee ambos mirrors, chunking + embedding, escribe `data/rag/<id>/{chunks.json,vectors.npy,index.json}`
- [X] T014 Implementar `rag/retriever.py` — clase `Retriever(block)`, `query(q, top_k, min_score)` por coseno sobre numpy, no-hits `[]`
- [X] T015 [P] Crear `tools/index_blocks.py` — CLI: indexar `--force` uno o todos los bloques
- [X] T016 [P] Crear `tools/query_block.py` — CLI de consulta sin MCP para depuración

**Checkpoint**: Fundación lista → escribir GREEN tests (ver T001-T004) → implementaciones.

---

## Phase 3: User Story 1 — Consultar docs de un bloque con RAG (P1) 🎯 MVP

**Goal**: El RAG del bloque responde desde su propio corpus, no alucina ni cruza bloques.
**Independent Test**: `python tools/query_block.py 02-configuracion "¿cómo activo trading de futuros?"` devuelve chunks citados (fuente+mirror) con score; fuera de corpus devuelve `[]`.

- [X] T017 Implementar `rag/chunking.py` heredando `heading_path` de cabeceras padre (US1: contexto jerárquico)
- [X] T018 Implementar retriever con `min_score` de umbral; no-hits explícito
- [X] T019 Verificar GREEN en tests/test_chunking.py, test_indexer.py, test_retriever.py

**Checkpoint**: US1 funcional y testeable independientemente.

---

## Phase 4: User Story 2 — Indexar un bloque desde ambos mirrors (P1)

**Goal**: Ingesta de `docs-freqtrade/` + `docs-freqtrade-web/` en chunks embebidos idempotentes.
**Independent Test**: indexar 2x → mismo `chunk_count` y `mirror_counts`; manifest con hash.

- [X] T020 [P] [US2] Completar `rag/indexer.py` con conteos por mirror (`mirror_counts`) y `content_hash` en manifiesto
- [X] T021 [US2] Upstream/upsert por id determinista: reindexar no duplica (verificar en test_indexer.py GREEN)
- [X] T022 [US2] Manejar mirror ausente (solo fuente): indexa el otro, marca origin en metadatos

**Checkpoint**: US1 + US2 operan juntas.

---

## Phase 5: User Story 3 — Exponer el bloque como MCP server FastMCP (P2)

**Goal**: Cada bloque es un MCP server stdio con `consultar_docs` + `health`.
**Independent Test**: handshake `initialize` → `tools/list` lista ambas tools → llamada real responde.

- [X] T023 Crear `servers/block_mcp.py` — FastMCP genérico con `consultar_docs(query, top_k)` y `health()`
- [X] T024 Crear `servers/run_bloque.py` — entrypoint `python run_bloque.py <id>` levanta FastMCP stdio para ese bloque
- [X] T025 [US3] Mapear errores: `EMBED_FAIL`, `INDEX_MISSING` (contrato mcp.md)
- [X] T026 Completar tests/test_mcp.py GREEN (smoke: tools/list + consulta real)

**Checkpoint**: US3 lista → server del bloque piloto registrable en Hermes.

---

## Phase 6: User Story 4 — Embeddings por env con fallback local (P3)

**Goal**: Portabilidad; sin gateway de embeddings, degrada a local.
**Independent Test**: sin `EMBED_*`, el índice usa `local-hash`; consulta sigue respondiendo.

- [X] T027 [P] [US4] Implementar fallback `local-hash` determinista en `rag/embeddings.py` (dimensión fija)
- [X] T028 [US4] Batching en `embed_texts` (≤16) con timeout corto y auth por `EMBED_API_KEY`
- [X] T029 [US4] Warning + `model_name()=="local-hash"` en manifiesto cuando el gateway falla

**Checkpoint**: framework portable.

---

## Phase N: Polish & Validación

- [X] T030 Indexar el bloque piloto y correr `python tools/query_block.py` (validar quickstart.md)
- [X] T031 [P] Actualizar `README.md` con la sección RAG-por-bloque + registro MCP (sin datos reales, sin emojis)
- [X] T032 Correr `requirements.txt` desde cero en venv limpio (`unset PYTHONPATH`) y validar todos los GREEN tests
- [ ] T033 Verificar registro en Hermes de `freq_config` con paths relativos (contracts/mcp.md)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (f1)**: sin dependencias; empieza ya
- **Foundational (f2)**: depende de Setup; BLOQUEA todas las user stories
- **US1 (f3)**: depende de Foundational
- **US2 (f4)**: depende de Foundational (integra con US1)
- **US3 (f5)**: depende de US1/US2 (necesita índice)
- **US4 (f6)**: depende de Foundational (subsistema embeddings)
- **Polish (fN)**: depende de todas las stories

### MVP First
1. f1 Setup → 2. f2 Foundational → 3. f3 US1 → **STOP & VALIDATE** → deploy/demo
   → 4. f4 US2 → 5. f5 US3 → 6. f6 US4 → 7. fN Polish

### In Each User Story
- Tests (T001-T004) deben FALLAR antes de implementar; GREEN tras implementar
- models before services before endpoints; núcleo antes de integración

### Parallel Opportunities
- [P] tasks marcan archivos independientes: T001-T004, T007-T008, T010-T011, T015-T016,
  T020, T027 pueden correr en paralelo
- Tests de un mismo story en paralelo

## Notas
- Ejecutar tests con `unset PYTHONPATH` y como archivo (nunca `python -c`: bloqueado).
- Commit tras cada tarea o grupo lógico.
- Verificar GREEN = mismo conteo de chunks en reindex (SC-003).
