# Contracts — Despacho operativo

**Feature**: `003-despacho-operativo`

## Tools MCP del despacho (`servers/run_despacho.py`)

### Lectura (sin OK, sin riesgo)

- `bot_status() -> str` — trades abiertos (wrapper `status`)
- `bot_profit() -> str` — resumen P/L (wrapper `profit`)
- `bot_balance() -> str` — balance (wrapper `balance`)
- `bot_whitelist() / bot_blacklist() -> str` — listas de pares
- `bot_count() / bot_logs(limit) -> str` — conteo y logs

### Ejecución (REQUIEREN OK explícito del usuario — gate en `despacho/permisos.py`)

- `entrar(pair, side, stake_amount, leverage, enter_tag) -> str` — forceenter
- `salir(trade_id, ordertype) -> str` — forceexit
- `vetar(pairs) -> str` — blacklist_add
- `bloquear(pair, until, reason) -> str` — lock_pair
- `detener_compras() -> str` — stopbuy
- `arrancar() / detener() -> str` — start/stop

### Manager

- `plan_mision(mision: str) -> str` — descompone la misión en pasos {dominio, tool,
  params, estado}; usa el LLM del gateway; cada paso mapeado al bloque que lo habilita.
- `estado_plan() -> str` — estado del plan actual.

## Gate de permisos (`despacho/permisos.py`)

```python
def requiere_ok(tool_name: str) -> bool:
    """True para tools de ejecución (FR-002)."""
    return tool_name in {"entrar", "salir", "vetar", "bloquear",
                         "detener_compras", "arrancar", "detener"}

def autorizar(tool_name: str, ok_usuario: bool) -> None:
    """Lanza PermissionError si la tool exige OK y no lo hay. Doble capa:
    se llama en el agente Y en el Manager antes de delegar."""
    if requiere_ok(tool_name) and not ok_usuario:
        raise PermissionError(
            f"{tool_name} exige OK explícito del usuario (constitution III).")
```

## Plan del Manager (`despacho/manager.py`)

```json
{
  "mision": "cazar alts momentum 7d en futuros",
  "pasos": [
    {"orden": 1, "dominio": "09-datos", "tool": "download-data",
     "params": {"pairs": ["X/USDT"], "timeframe": "1h"}, "estado": "pendiente"},
    {"orden": 2, "dominio": "03-estrategia", "tool": "escribir_estrategia",
     "params": {"momentum": "RSI+volumen"}, "estado": "pendiente"},
    {"orden": 3, "dominio": "04-backtesting", "tool": "backtesting",
     "params": {"timeframe": "1h"}, "estado": "pendiente"},
    {"orden": 4, "dominio": "07-riesgo-futuros", "tool": "revisar_riesgo",
     "params": {"leverage_max": 3}, "estado": "pendiente"}
  ],
  "decidir_dry_run": false,
  "bloqueos": []
}
```

- `decidir_dry_run = true` SOLO si backtesting + riesgo dan OK (FR-004).
- `bloqueos`: lista de {dominio, motivo} cuando un paso falla.

## Cadena dry-run (`despacho/cadena.py`)

Flujo CLI (Taller) en orden, cada paso = subprocess de freqtrade:

1. `download-data` (pares, timeframe) → `data/`
2. `backtesting` (estrategia + datos) → métricas {profit_factor, drawdown}
3. `hyperopt` (si PF/drawdown dentro de umbral) → config optimizada
4. `revisar_riesgo` (leverage/stoploss de la config) → OK/rechazo

Umbrales default: PF ≥ 1.3, drawdown ≤ 30%. Configurables por env.

## Config env (.env, adicional)

```bash
FREQTRADE_URL=http://127.0.0.1:8080
FREQTRADE_USER=Freqtrader
FREQTRADE_PASS=...
FREQTRADE_DRY_RUN=true        # forzado; false se ignora (regla dura)
CADENA_PF_MIN=1.3
CADENA_DRAWDOWN_MAX=30
```

## Registro Hermes

```yaml
mcp_servers:
  freq_despacho:
    command: <proyecto>/.venv/Scripts/python.exe
    args: [<proyecto>/servers/run_despacho.py]
    enabled: true
```
