# Implementation Plan: Agentes LLM por bloque

**Branch**: `002-agentes-llm-bloque` | **Date**: 2026-08-30 | **Spec**: `specs/002-agentes-llm-bloque/spec.md`

## Summary

Construir la capa de **agentes LLM por bloque** sobre el RAG del feature 001: cada bloque
se expone como un MCP server que combina su Retriever (única fuente) + un LLM del gateway
LiteLLM `:4000` para responder preguntas del dominio con **citas estructuradas**. Sin
hits → rechazo explícito; LLM caído → degrada a hits crudos. Modelo configurable por
bloque vía env. Benchmark golden set para medir recall@1/@3 y groundedness.

## Technical Context

**Language/Version**: Python 3.14 (`.venv/` del proyecto), mcp 1.29.1, openai 3.6.0.

**Primary Dependencies**:
- `openai` (ya instalado) — cliente chat del gateway (`base_url=http://localhost:4000/v1`)
- `mcp>=1.27,<2.0` (ya), `numpy` (ya), `python-dotenv` (ya)
- `pytest` (ya)
- NO nuevas dependencias para el MVP (embedding semántico local = feature 003)

**Storage**: ninguno nuevo (usa `data/rag/<bloque>/` del feature 001).

**Testing**: pytest. Tests: respuesta con citas, rechazo sin hits, degradación LLM caído
(mock), health con modelo, benchmark.

**Target Platform**: Windows (dev), portable (Linux/Docker).

**Project Type**: MCP servers (agentes persistentes) sobre framework existente.

**Performance Goals**: Respuesta agente < 15s (LLM incluido); benchmark < 5 min.

**Constraints**:
- El agente es SOLO cliente del gateway: no modifica litellm config, no crea keys.
- Master key local se lee desde env del proyecto (`.env`, gitignored) — nunca hardcodeada.
- LLM timeout corto (connect 5s, read 60s); retry 1 vez.
- Sin hits bajo min_score → rechazo explícito (no llama al LLM: ahorra crédito).
- Llamadas al LLM SOLO con hits suficientes (no gastar crédito en no-hits).

**Scale/Scope**: 12 agentes posibles; MVP = bloque piloto `02-configuracion` + framework
parametrizado (FR-008 del feature 001). Benchmark incluido.

## Constitution Check

*GATE: debe pasar antes de la investigación.*

- ✅ **I. Documentation-as-Org-Chart** — el agente responde SOLO desde el RAG de su bloque.
- ✅ **II. RAG-Block Isolation** — rechazo explícito fuera de dominio; sin cruces.
- ✅ **III. Safe-Operation Gate** — SOLO consulta docs; NO toca superficie live ni gasta
  crédito sin hits. Llamadas LLM acotadas (timeout, retry 1).
- ✅ **IV. Portability** — config por env, sin rutas absolutas; degradación elegante.
- ✅ **V. Spec-Driven** — spec 002 aprobado; tests antes de implementar.

Sin violaciones. **PASA.**

## Project Structure

### Documentation (this feature)

```text
specs/002-agentes-llm-bloque/
├── spec.md
├── plan.md              # este archivo
├── research.md
├── data-model.md
├── contracts/agent-mcp.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
freq/
├── rag/
│   └── agent.py             # NUEVO: AgenteLLM(block_id): responder() + citas + rechazo + degradación
├── servers/
│   ├── agent_mcp.py         # NUEVO: FastMCP del agente (responder + health ampliado)
│   └── run_agente.py        # NUEVO: entrypoint stdio: python servers/run_agente.py <bloque>
├── tools/
│   ├── benchmark_rag.py     # NUEVO: golden set + recall@1/@3 + MRR + groundedness
│   └── golden_set.json      # NUEVO: ~20 preguntas con chunk esperado
├── tests/
│   ├── test_agent.py        # NUEVO
│   └── test_benchmark.py    # NUEVO
├── .env.example             # + AGENT_MODEL_<BLOQUE>, LLM_BASE_URL, LLM_API_KEY
└── IMPLEMENTACION_NOTAS.md  # + sección feature 002
```

**Structure Decision**: el agente vive en `rag/agent.py` (lógica) + `servers/agent_mcp.py`
(interface MCP), siguiendo el patrón retriever/mcp del feature 001. Un solo server por
bloque, parametrizado por id. El benchmark es una tool CLI, no un server.

## Complexity Tracking

Sin violaciones. **N/A.**

## Fases

- **Fase 0**: research — verificar modelo default responde en gateway (una llamada de
  prueba), formato de citas, golden set base.
- **Fase 1**: diseño — data-model (respuesta, cita, golden set), contracts (tool
  `responder`), quickstart.
- **Fase 2**: tareas (tasks.md).
- **Fase 3**: implementación + tests + benchmark + registro Hermes.
