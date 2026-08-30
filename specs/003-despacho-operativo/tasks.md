# Tasks: Despacho operativo

**Input**: Design docs de `/specs/003-despacho-operativo/`
**Prerequisites**: plan.md, spec.md, research.md, contracts/despacho.md

## Test-Driven (Red antes de implementar) ⚠️

- [X] T301 [P] [foundation] Tests que FALLAN en tests/test_wrapper.py (mocks httpx: auth JWT, relogin 401, 19 tools responden)
- [X] T302 [P] [foundation] Tests que FALLAN en tests/test_permisos.py (gate: tools de ejecución exigen OK; sin OK → PermissionError)
- [X] T303 [P] [foundation] Tests que FALLAN en tests/test_manager.py (plan_mision descompone; decidir_dry_run solo con backtest+riesgo OK)
- [X] T304 [P] [foundation] Tests que FALLAN en tests/test_cadena.py (cadena con subprocess mock; umbrales PF/drawdown)

---

## Phase 1: Setup

- [X] T305 Actualizar `.env.example` con FREQTRADE_URL/USER/PASS/DRY_RUN + umbrales cadena

---

## Phase 2: Foundational (bloquea las user stories)

- [X] T306 Crear `despacho/wrapper.py` — extraer las 19 funciones del wrapper REST (lógica pura, httpx, auth JWT, relogin 401), importables y mockeables
- [X] T307 Crear `despacho/permisos.py` — `requiere_ok(tool)` + `autorizar(tool, ok_usuario)` (doble capa: agente + Manager)
- [X] T308 Crear `despacho/manager.py` — `plan_mision(mision)` → plan JSON {pasos por dominio, decidir_dry_run, bloqueos}
- [X] T309 Crear `despacho/cadena.py` — flujo CLI: download-data → backtesting → hyperopt → revisar_riesgo (subprocess freqtrade, umbrales env)

**Checkpoint**: despacho construible y testeable con mocks.

---

## Phase 3: User Story 1 — Agente control/riesgo con manos (P1)

**Goal**: El agente invoca las tools del wrapper contra freqtrade (dry-run).
**Independent Test**: tests/test_wrapper.py GREEN con mocks; smoke real cuando haya freqtrade.

- [X] T310 [US1] `despacho/wrapper.py` completo: 11 lectura + 8 ejecución, con relogin en 401 y timeout
- [X] T311 [US1] `despacho/permisos.py` integrado: tools de ejecución pasan por `autorizar()`
- [X] T312 [US1] Verificar GREEN tests/test_wrapper.py + test_permisos.py

**Checkpoint**: US1 con mocks.

---

## Phase 4: User Story 2 — Manager orquestador (P1)

**Goal**: Manager descompone misiones y decide dry-run con OK de dominios.
**Independent Test**: tests/test_manager.py GREEN.

- [X] T313 [US2] `plan_mision(mision)`: LLM gateway → pasos {dominio, tool, params}; mapeo dominio→bloque documental
- [X] T314 [US2] `decidir_dry_run`: SOLO si backtest + riesgo OK; bloqueos con motivo
- [X] T315 [US2] `estado_plan()`: consulta de estado del plan
- [X] T316 [US2] Verificar GREEN tests/test_manager.py

**Checkpoint**: US2.

---

## Phase 5: User Story 3 — Cadena dry-run (P2)

**Goal**: Flujo completo datos→estrategia→backtest→hyperopt→riesgo en dry-run.
**Independent Test**: tests/test_cadena.py GREEN con subprocess mock.

- [X] T317 [US3] `cadena.py`: download-data (subprocess freqtrade) → data/
- [X] T318 [US3] backtesting → métricas {profit_factor, drawdown}; umbrales env (PF≥1.3, DD≤30)
- [X] T319 [US3] hyperopt si métricas OK → config optimizada
- [X] T320 [US3] revisar_riesgo (leverage/stoploss) → OK/rechazo
- [X] T321 [US3] Verificar GREEN tests/test_cadena.py

**Checkpoint**: US3 con mocks.

---

## Phase 6: User Story 4 — MCP del despacho + Hermes (P3)

**Goal**: Despacho expuesto como MCP y registrable en Hermes.
**Independent Test**: smoke stdio del despacho (tools listadas).

- [X] T322 Crear `servers/despacho_mcp.py` — FastMCP: tools lectura + ejecución (gate) + plan_mision + estado_plan
- [X] T323 Crear `servers/run_despacho.py` — entrypoint stdio
- [X] T324 Smoke stdio: `tools/list` → tools del despacho; llamadas con mocks
- [X] T325 Documentar registro Hermes (freq_despacho) en README + notas

**Checkpoint**: US4.

---

## Phase N: Integración real (requiere OK del usuario + Docker) ⚠️

- [ ] T326 `tools/levantar_freqtrade.sh` — docker run freqtrade dry-run con REST habilitada (config mínima)
- [ ] T327 Smoke real: bot_status/profit contra freqtrade levantado; forceenter con OK en par de prueba
- [ ] T328 Cadena real en dry-run: descargar datos → backtest → métricas; reportar resultado
- [ ] T329 Registrar en Hermes (freq_despacho) con OK del usuario + `/reload-mcp`
- [ ] T330 Suite completa 001+002+003 GREEN; commit

---

## Dependencies & Execution Order

### Phase Dependencies
- f1 Setup → f2 Foundational (bloquea todo) → US1 (f3) → US2 (f4) → US3 (f5) → US4 (f6) → Integración real (fN)

### MVP First
1. f1 → 2. f2 → 3. US1 → **STOP & VALIDATE (mocks)** → US2 → US3 → US4 → fN (integración real, con OK)

### Parallel
- T301-T304 (tests), T305: independientes
- T306-T309: secuenciales (wrapper → permisos → manager → cadena)

## Notas
- Tests con mocks de httpx/subprocess (sin freqtrade, sin gasto).
- Integración real (T326-T330) SOLO con OK del usuario (Docker + dry-run).
- Regla dura: ninguna tool de ejecución sin OK; verificar `FREQTRADE_DRY_RUN=true` con
  `show_config` antes de operar.
- `unset PYTHONPATH`, `.venv/Scripts/python.exe`, sin `python -c`.
