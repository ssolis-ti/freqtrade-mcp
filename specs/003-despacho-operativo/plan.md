# Implementation Plan: Despacho operativo

**Branch**: `003-despacho-operativo` | **Date**: 2026-08-30 | **Spec**: `specs/003-despacho-operativo/spec.md`

## Summary

Unir el cerebro (RAG + agentes, features 001-002) con las manos (wrapper REST de
freqtrade, 19 tools) para que un LLM pueda OPERAR freqtrade en dry-run. Componentes:
(1) integración agente control/riesgo ↔ wrapper, (2) Manager orquestador que descompone
misiones y delega por dominio, (3) cadena datos→estrategia→backtest→hyperopt→riesgo en
dry-run contra freqtrade real (Docker), (4) registro en Hermes. Live queda fuera de
alcance (regla dura constitution III).

## Technical Context

**Language/Version**: Python 3.14 (`.venv/`), mcp 1.29.1, httpx.

**Primary Dependencies**:
- `httpx` (ya en requirements del wrapper)
- `mcp>=1.27,<2.0` (ya)
- `openai` (Manager, ya)
- freqtrade Docker (imagen `freqtradeorg/freqtrade:stable`) para el entorno de pruebas

**Storage**: ninguno nuevo (usa `data/` para resultados de backtest si aplica).

**Testing**: pytest con mocks del wrapper (sin freqtrade real en CI): FR-007/SC-005.
Integración real (SC-001/SC-004) requiere Docker freqtrade dry-run (manual, con OK).

**Target Platform**: Windows (dev), Docker para freqtrade.

**Project Type**: integración de capas (agentes + wrapper REST + Manager).

**Performance Goals**: llamadas REST < 2s; plan del Manager < 30s.

**Constraints**:
- Regla dura: tools de ejecución SOLO con OK del usuario (gate en el agente Y en el
  Manager; doble capa).
- El wrapper se integra tal cual; si falta un endpoint, extender sin romper las 19 tools.
- Credenciales freqtrade en `.env` (FREQTRADE_URL/USER/PASS).
- Sin freqtrade: degradación elegante con error claro (tests con mock).
- El flujo de Taller (download-data, backtesting, hyperopt) corre como CLI subprocess;
  el de Despacho (operación) como REST.

**Scale/Scope**: MVP = agente control con manos + Manager + cadena dry-run sobre 1-3
pares de prueba. Live fuera de alcance.

## Constitution Check

*GATE: debe pasar antes de la investigación.*

- ✅ **I. Documentation-as-Org-Chart** — cada paso del flujo lo ejecuta el agente cuyo
  bloque documental lo habilita (control→rest-api, riesgo→stoploss/leverage, etc.).
- ✅ **II. RAG-Block Isolation** — los agentes siguen consultando SOLO su bloque.
- ✅ **III. Safe-Operation Gate** — tools de ejecución exigen OK del usuario (doble capa:
  agente + Manager); dry-run obligatorio; live fuera de alcance.
- ✅ **IV. Portability** — credenciales por env; sin freqtrade degrada con error claro.
- ✅ **V. Spec-Driven** — spec 003 aprobado; tests con mock antes de integración real.

Sin violaciones. **PASA.**

## Project Structure

### Documentation (this feature)

```text
specs/003-despacho-operativo/
├── spec.md, plan.md, research.md, contracts/despacho.md, tasks.md
```

### Source Code

```text
freq/
├── despacho/                    # NUEVO: capa de operación
│   ├── __init__.py
│   ├── wrapper.py               # cliente del wrapper REST (19 tools, reutiliza prototype)
│   ├── permisos.py              # gate de OK del usuario (regla dura, doble capa)
│   ├── manager.py               # Manager orquestador: misión → plan → delega → decide
│   └── cadena.py                # flujo datos→estrategia→backtest→hyperopt→riesgo (CLI)
├── servers/
│   ├── despacho_mcp.py          # NUEVO: MCP del despacho (tools de control + Manager)
│   └── run_despacho.py          # NUEVO: entrypoint stdio
├── tools/
│   ├── levantar_freqtrade.sh    # NUEVO: docker run freqtrade dry-run (dev)
│   └── probar_despacho.py       # NUEVO: smoke del despacho contra freqtrade real
├── tests/
│   ├── test_wrapper.py          # mocks del wrapper (FR-007/SC-005)
│   ├── test_permisos.py         # gate de OK (SC-002)
│   ├── test_manager.py          # descomposición de misión (SC-003)
│   └── test_cadena.py           # cadena con mocks (SC-004 parcial)
├── .env.example                 # + FREQTRADE_URL/USER/PASS
└── prototype/freqtrade-mcp/     # intacto (base del wrapper)
```

**Structure Decision**: nueva carpeta `despacho/` (capa de operación) que reutiliza el
wrapper existente (`prototype/freqtrade-mcp/mcp_server.py` → funciones importables) sin
duplicarlo. El Manager y la cadena viven aquí; el MCP del despacho en `servers/`.

## Complexity Tracking

Sin violaciones. **N/A.**

## Fases

- **Fase 0**: research — verificar que el wrapper es importable (funciones, no solo
  decoradores), diseño del gate de permisos, comando Docker para freqtrade dry-run.
- **Fase 1**: diseño — contracts (tools del despacho, gate, plan del Manager), data-model.
- **Fase 2**: tareas (tasks.md).
- **Fase 3**: implementación con mocks → integración real en Docker dry-run → Hermes.
