# Freqtrade — Integración (CLI + REST API)

> Comandos y endpoints verificados de la documentación oficial de freqtrade (`stable`).
> Este es el "mapa de la maquinaria" que los agentes controlan. Fase "Idea".

## Superficies de control

Freqtrade ofrece dos formas de manejarlo. Para multi-agente conviene repartirlas:

| Superficie | Naturaleza | Dominios que actúan |
|---|---|---|
| **CLI** | Discontinua, procesos pesados | `data-download`, `strategy*`, `backtesting*`, `hyperopt*`, `stoploss`/`leverage` |
| **REST API** `/api/v1` | Continua, en vivo | `rest-api`, `freq-ui`, `stoploss`, `data-*`, `configuration` |

---

## CLI (Taller)

### Descargar datos
```bash
freqtrade download-data -c user_data/config.json -t 5m --timerange 20240101-20240801
```

### Backtest
```bash
freqtrade backtesting -s AwesomeStrategy --strategy-list Strategy001 Strategy002 \
  --timerange 20180401-20180410 --timeframe 5m --export trades
```
- Mide: trades, avg profit %, tot profit (BTC/%), avg duration, wins/draws/losses, drawdown %.
- Requiere datos históricos (`download-data`).
- Para reproducibilidad con pairlist dinámico: `freqtrade test-pairlist` → pairlist estático.

### Hiperoptimización (ML / optuna)
```bash
freqtrade hyperopt -s AwesomeStrategy --spaces buy sell roi stoploss trailing protection \
  -e 100 --min-trades 30 --job-workers -1
```
- Paquetes: `requirements-hyperopt.txt` (en Docker ya está).
- Spaces: `default, all, buy, sell, enter, exit, roi, stoploss, trailing, protection, trades`.
- Loss functions: `SharpeHyperOptLoss`, `SortinoHyperOptLoss`, `CalmarHyperOptLoss`,
  `MaxDrawDownHyperOptLoss`, `ProfitDrawDownHyperOptLoss`, etc.
- Ver resultados: `freqtrade hyperopt-show -n <id>` (best) y `hyperopt-list`.
- **Cuidado**: corrobora que backtest == hyperopt con los mismos params/config (stoploss,
  max_open_trades y trailing suelen venir en config y pisan a la estrategia).

### Config
```bash
freqtrade new-config --config user_data/config.json   # generar base
freqtrade show-config -c <cfg>                        # ver config combinada final
```
- Env vars: prefijo `FREQTRADE__{seccion}__{key}`, p.ej. `FREQTRADE__EXCHANGE__KEY`.
- Multi-config con `add_config_files` (útil para `config-private.json` de secretos).
- JSON: permite comentarios `//` y trailing commas.

### Pairlist
```bash
freqtrade test-pairlist -c <cfg>   # genera pairlist para reproducir backtest con parlist dinámico
```
- Pairlist handlers: Static, VolumePairList, PriceFilter, ShuffleFilter, etc.

---

## REST API `/api/v1` (Despacho)

### Habilitar / autenticar
```json
{ "api_server": { "enabled": true, "listen_ip_address": "127.0.0.1", "listen_port": 8080,
   "username": "Freqtrader", "password": "SuperSecret1!", "jwt_secret_key": "..." } }
```
```bash
# login → access token (15 min)
curl -X POST --user Freqtrader http://localhost:8080/api/v1/token/login
# refresh
curl -X POST --header "Authorization: Bearer ${refresh_token}" http://localhost:8080/api/v1/token/refresh
```
> No exponer a internet. En VPS usar ssh tunnel o VPN. Cliente liviano: `pip install freqtrade-client`.

### Endpoints operativos (lista verificada)
`ping, count, status, trade, trades, balance, profit, daily, weekly, monthly, stats,
performance, entries, exits, mix_tags, whitelist, blacklist, locks, lock_add, delete_lock,
forcebuy, forceenter, forceexit, delete_trade, cancel_open_order, available_pairs,
pair_candles, pair_history, pairlists_available, start, stop, stopbuy, reload_config,
show_config, health, logs, sysinfo, version, strategies, strategy`.

### Uso programático
```python
from freqtrade_client import FtRestClient
client = FtRestClient(server_url, username, password)

client.ping()                       # {'status':'pong'}
client.blacklist("BTC/USDT")        # añadir a blacklist
client.forceenter("LDO/USDT", side="long", leverage=3.0, enter_tag="momentum")
client.stopbuy()
```

---

## Futuros (leverage)

- Exchanges soportados: **Binance, Bitget, Bybit, Gate, Hyperliquid, Kraken, OKX**.
- `stoploss_price_type`: solo futuros. Valores `"last"`, `"mark"`, `"index"`.
- Stoploss con leverage = riesgo en el trade. `stoploss=-0.10` a 10x → gatilla con -1% de precio.
- Orden stoplos en exchange: `stoploss_on_exchange`, `stoploss_on_exchange_interval`,
  `stoploss_on_exchange_limit_ratio`, `emergency_exit`. Preferir `market` en crash.
- Modos stoploss: estático, trailing, trailing con offset (`trailing_only_offset_is_reached`),
  custom stoploss function (callback).

## Config minimalista de arranque (dry-run)

```json
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": 100,
  "tradable_balance_ratio": 0.99,
  "dry_run": true,
  "dry_run_wallet": 1000,
  "timeframe": "5m",
  "exchange": { "name": "binance", "key": "", "secret": "" },
  "strategy": "SampleStrategy",
  "user_data_dir": "./user_data/"
}
```
