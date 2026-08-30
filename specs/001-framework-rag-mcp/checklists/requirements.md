# Requirements Checklist — Framework RAG-por-bloque + MCP por bloque

Feature: `001-framework-rag-mcp`

## Functional Requirements

- [ ] **FR-001** — Indexar los 12 bloques desde ambos mirrors (fuente develop + web stable)
- [ ] **FR-002** — Vector store aislado por bloque (sin embeddings compartidos)
- [ ] **FR-003** — RAG responde solo desde el corpus del bloque; no-hits explícito, sin alucinar ni cruzar bloques
- [ ] **FR-004** — MCP server FastMCP por bloque con `consultar_docs(query, top_k)` y `health()`
- [ ] **FR-005** — Embedding configurable vía env (`EMBED_BASE_URL`, `EMBED_MODEL`, `EMBED_API_KEY`); LiteLLM/Bifrost `:4000` default + fallback local
- [ ] **FR-006** — Reindexación idempotente (upsert por hash determinista)
- [ ] **FR-007** — Servers MCP usan `mcp>=1.27,<2.0`, import desde `mcp.server.fastmcp`
- [ ] **FR-008** — Parametrizado por bloque; escalar = añadir corpus/servers, no rediseñar

## Success Criteria

- [ ] **SC-001** — Consultas al bloque piloto devuelven pasajes citados (fuente+mirror) con score, 100% de pruebas
- [ ] **SC-002** — No-hits explícitos, 0% respuestas inventadas fuera de corpus
- [ ] **SC-003** — Reindexar 2x = mismo conteo de chunks (sin duplicados)
- [ ] **SC-004** — MCP del bloque registrado en Hermes; `tools/list` + consulta real (smoke)
- [ ] **SC-005** — Con embeddings endpoint caído, degrada a local y responde

## Alcance (decidido)

- Bloque piloto: `02-configuracion` (`configuration.md` 58K fuente / 64K web)
- MVP del patrón end-to-end; escalar a los 12 por repetición (FR-008)
- Embeddings: LiteLLM/Bifrost `:4000` vía env + fallback sentence-transformers local
