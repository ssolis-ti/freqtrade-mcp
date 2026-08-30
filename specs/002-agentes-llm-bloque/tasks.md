# Tasks: Agentes LLM por bloque

**Input**: Design docs de `/specs/002-agentes-llm-bloque/`
**Prerequisites**: plan.md, spec.md, research.md, contracts/agent-mcp.md

## Test-Driven: escribir tests ANTES de implementar (Red) ⚠️

- [X] T101 [P] [foundation] Escribir tests que FALLAN en tests/test_agent.py (responder con citas, sin_hits, degradado_llm con mock, health con modelo)
- [X] T102 [P] [foundation] Escribir tests que FALLAN en tests/test_benchmark.py (golden set carga, recall@1/@3, reporte JSON)

---

## Phase 1: Setup

- [X] T103 Actualizar `.env.example` con `LLM_BASE_URL`, `LLM_API_KEY`, `AGENT_MODEL_DEFAULT` (+ ej. por bloque)

---

## Phase 2: Foundational (bloquea las user stories)

- [X] T104 Crear `rag/agent.py` — clase `AgenteLLM(block_id)`: lee env (modelo por bloque), cliente openai gateway, `responder()` con prompt desde hits, citas, rechazo sin hits, degradación a hits crudos con retry 1
- [X] T105 Crear `servers/agent_mcp.py` — FastMCP del agente: tools `responder` + `consultar_docs` + `health` (ampliado con modelo)
- [X] T106 Crear `servers/run_agente.py` — entrypoint stdio: `python servers/run_agente.py <bloque_id>`

**Checkpoint**: agente construible y testeable con mock.

---

## Phase 3: User Story 1 — Responder con fundamento (P1)

**Goal**: El agente responde preguntas del dominio citando chunks del RAG.
**Independent Test**: `responder("como activo futuros")` sobre bloque piloto → estado `ok`, citas no vacías.

- [X] T107 [US1] Prompt del agente: instrucciones de dominio + fragmentos con score/fuente + pregunta (idioma de la pregunta)
- [X] T108 [US1] Parseo de respuesta: extraer SOLO `message.content`, ignorar `reasoning_content`; `max_tokens=2000`
- [X] T109 [US1] Verificar GREEN tests/test_agent.py (casos con mock del cliente)

**Checkpoint**: US1 funcional.

---

## Phase 4: User Story 2 — No alucinar fuera de dominio (P1)

**Goal**: Rechazo explícito sin hits; degradación si el LLM falla.
**Independent Test**: `responder("receta de cocina")` → `sin_hits` sin llamar al LLM (mock que fallaría si se llama).

- [X] T110 [US2] Sin hits (bajo min_score) → `estado=sin_hits`, respuesta de rechazo, NO llamar al LLM
- [X] T111 [US2] LLM falla (timeout/429/5xx tras retry 1) → `estado=degradado_llm`, hits crudos en respuesta
- [X] T112 [US2] Verificar GREEN (tests de rechazo y degradación con mocks)

**Checkpoint**: US1 + US2.

---

## Phase 5: User Story 3 — Modelo configurable por bloque (P2)

**Goal**: Mapa bloque→modelo vía env con fallback.
**Independent Test**: health reporta `modelo_configurado` y `modelo_activo`.

- [X] T113 [US3] Lectura de `AGENT_MODEL_<BLOQUE>` (normalizar id: `02-configuracion` → `AGENT_MODEL_02_CONFIGURACION`), default `AGENT_MODEL_DEFAULT`
- [X] T114 [US3] Fallback si el modelo no existe: degradar a default con warning
- [X] T115 [US3] health ampliado: `modelo_configurado`, `modelo_activo`
- [X] T116 [US3] Verificar GREEN

**Checkpoint**: US3.

---

## Phase 6: User Story 4 — Benchmark (P3)

**Goal**: Medir recall@1/@3, MRR y groundedness.
**Independent Test**: `python tools/benchmark_rag.py 02-configuracion` → reporte JSON.

- [X] T117 [P] [US4] Crear `tools/golden_set.json` — ~20 preguntas del bloque con `chunk_id` esperado (de chunks.json real)
- [X] T118 [US4] Crear `tools/benchmark_rag.py` — carga golden set, consulta RAG, calcula recall@1/@3, MRR
- [X] T119 [US4] Groundedness: % de respuestas del agente con citas válidas (mock de LLM o modo solo-retrieval)
- [X] T120 [US4] Reporte JSON en `data/benchmark/<bloque>.json` + stdout resumido
- [X] T121 [US4] Verificar GREEN tests/test_benchmark.py

**Checkpoint**: medición objetiva disponible.

---

## Phase N: Polish & Validación

- [X] T122 Indexar bloque piloto (si falta), correr `tools/benchmark_rag.py 02-configuracion` y `smoke` del agente por stdio
- [X] T123 [P] Actualizar README: sección "Agentes LLM por bloque" (uso, env, registro) — sin emojis/datos reales
- [X] T124 Correr toda la suite (feature 001 + 002) en `.venv` con `unset PYTHONPATH`
- [X] T125 Actualizar IMPLEMENTACION_NOTAS.md con feature 002 + registro Hermes sugerido (T033 combinado)
- [X] T126 Commit del feature 002

---

## Dependencies & Execution Order

### Phase Dependencies
- f1 Setup → f2 Foundational (bloquea todo) → US1 (f3) → US2 (f4) → US3 (f5) → US4 (f6) → Polish (fN)

### MVP First
1. f1 → 2. f2 → 3. US1 → **STOP & VALIDATE** → US2 → US3 → US4 → Polish

### Parallel
- T101-T102, T103, T117: archivos independientes

## Notas
- Tests con mock del cliente openai (no gastar crédito en tests; 1 llamada real de humo al final).
- `unset PYTHONPATH`, `.venv/Scripts/python.exe`, sin `python -c`.
- No-hits → nunca llamar al LLM (ahorro de crédito; regla del usuario).
