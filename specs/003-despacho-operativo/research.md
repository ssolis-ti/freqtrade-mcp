# Research — Fase 0: Despacho operativo

**Feature**: `003-despacho-operativo` | **Fecha**: 2026-08-30

## Hallazgos verificados

### Wrapper REST (prototype/freqtrade-mcp/mcp_server.py) — REUTILIZABLE

- **19 tools** FastMCP: 11 lectura (ping, status, balance, profit, performance,
  available_pairs, pair_candles, whitelist, blacklist, logs, count) + 8 ejecución
  (forceenter, forceexit, blacklist_add, lock_pair, stopbuy, start, stop, show_config).
- Auth JWT: `_auth()` (login + refresh, access ~15 min), `_call()` con relogin en 401.
- **Patrón actual**: decoradores `@mcp.tool()` sobre funciones planas → para reutilizar
  como librería hay que importar las funciones subyacentes o refactorizar ligeramente
  (extraer las funciones a `despacho/wrapper.py` y decorarlas ahí). Decisión: extraer
  las 19 funciones a `despacho/wrapper.py` (lógica pura, retorna dict/str) y que el MCP
  las decore — el wrapper del prototype queda como referencia/legado.
- Dependencias: httpx + mcp (ya en requirements).

### Entorno de pruebas — freqtrade en Docker (dry-run)

- Imagen oficial: `freqtradeorg/freqtrade:stable`. Comando típico dry-run con REST:
  `docker run -d -p 8080:8080 -v <cfg>:/freqtrade/config.json freqtradeorg/freqtrade:stable trade --config config.json` + `api_server.enabled=true` en config.
- **No hay instancia corriendo hoy** — se necesita levantar para SC-001/SC-004 (requiere
  OK del usuario y config mínima de API). Los tests unitarios usan mocks.
- Config mínima REST (freqtrade config.json):
  ```json
  {"api_server": {"enabled": true, "listen_ip_address": "0.0.0.0",
    "listen_port": 8080, "username": "Freqtrader", "password": "..."},
   "dry_run": true}
  ```

### Gate de permisos

- Regla dura constitution III → `despacho/permisos.py` con lista explícita de tools de
  ejecución; se llama en el agente Y en el Manager (doble capa) antes de cualquier
  llamada de escritura.

### Riesgos

| Riesgo | Mitigación |
|---|---|
| Wrapper con decoradores difíciles de importar | Extraer lógica a `despacho/wrapper.py`; el MCP decora |
| Sin freqtrade corriendo | Tests con mock (FR-007/SC-005); integración real manual con Docker |
| forceenter en dry-run sigue siendo real en exchange si mal config | Forzar `FREQTRADE_DRY_RUN=true`; verificar con `show_config` antes de operar |
| Docker no disponible en la máquina | Verificar antes; alternativa: freqtrade nativo (pip install freqtrade) |

## Decisiones técnicas

1. **`despacho/wrapper.py`**: las 19 funciones del wrapper como lógica pura (httpx,
   auth JWT, relogin 401) — importables y testeables con mock (patch de httpx).
2. **`despacho/permisos.py`**: gate de OK (lista de tools de ejecución + `autorizar()`).
3. **`despacho/manager.py`**: `plan_mision(mision)` → LLM gateway → plan JSON con pasos
   por dominio; `decidir_dry_run` solo si backtest+riesgo OK.
4. **`despacho/cadena.py`**: subprocess CLI de freqtrade (download-data, backtesting,
   hyperopt) con umbrales PF/drawdown por env.
5. **Tests con mock** de httpx/wrapper: sin freqtrade, todo verificable (FR-007/SC-005).
