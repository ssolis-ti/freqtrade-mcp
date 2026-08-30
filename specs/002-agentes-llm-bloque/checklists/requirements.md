# Requirements Checklist — Agentes LLM por bloque

Feature: `002-agentes-llm-bloque`

## Functional Requirements

- [ ] **FR-001** — Agente LLM por bloque (tool `responder`) usando RAG como única fuente
- [ ] **FR-002** — Respuestas con citas estructuradas JSON (chunk_id, mirror, path, heading, score)
- [ ] **FR-003** — Sin hits suficientes → rechazo explícito; nunca inventa ni cruza bloques
- [ ] **FR-004** — Modelo configurable por bloque vía env (`AGENT_MODEL_<BLOQUE>`), default + fallback
- [ ] **FR-005** — LLM caído → degrada a hits crudos del RAG (nunca falla)
- [ ] **FR-006** — MCP server stdio por bloque: `responder` + `health` ampliado (modelo activo)
- [ ] **FR-007** — Benchmark golden set (~20 preguntas): recall@1/@3, MRR, groundedness; reporte JSON
- [ ] **FR-008** — No toca config del gateway externo; el agente es solo cliente

## Success Criteria

- [ ] **SC-001** — Respuestas con citas válidas (mirror/path/heading existentes) 100% con hits
- [ ] **SC-002** — Preguntas fuera de dominio → rechazo explícito 100% (sin alucinación)
- [ ] **SC-003** — LLM caído simulado → degrada a hits crudos sin fallar
- [ ] **SC-004** — health reporta modelo configurado y activo
- [ ] **SC-005** — Benchmark genera reporte JSON reutilizable

## Alcance (decidido)

- Bloque piloto: `02-configuracion`; framework parametrizado por bloque
- Modelo default: `deepseek-via-inference` (gateway :4000, master key local)
- Embeddings: local-hash por defecto (semánticos locales = feature 003, requiere OK)
- Registro en Hermes junto con feature 001 (T033) — un solo edit de config.yaml
