# Módulo de Riesgo — Freqtrade Multi-Agent

> Cuadro de control de riesgo (fase "Idea"). Lo gobierna el **dominio documental
> `stoploss`/`leverage`/`exchanges`** de freqtrade. Sus dos caras ejecutoras (roles): **Risk
> Governor** (refuerzo del dominio en diseño) y **Risk Sentinel** (refuerzo en vivo). Es la
> capa que ninguna ejecución bypassa.

## Mapa de riesgo

| Dimensión | Parámetro freqtrade | Agente |
|---|---|---|
| Stop loss estático | `stoploss` (ratio, ej -0.10) | Risk Governor |
| Trailing stop | `trailing_stop`, `trailing_stop_positive`, `trailing_stop_positive_offset`, `trailing_only_offset_is_reached` | Risk Governor |
| Stop on exchange | `stoploss_on_exchange`, `stoploss_on_exchange_interval`, `stoploss_on_exchange_limit_ratio`, `emergency_exit` | Risk Governor |
| Price type (futuros) | `stoploss_price_type`: `last`/`mark`/`index` | Risk Governor |
| Protections | `protections` (cooldowns, pares con pérdida, etc.) | Risk Governor |
| Límite de trades | `max_open_trades`, `stake_amount`, `tradable_balance_ratio`, `available_capital` | Risk Governor / Manager |
| Leverage | por trade (futuros) | Position Manager (validado por Governor) |
| Veto de pares | `blacklist`, `lock_pair` | Risk Sentinel |
| Frenado en vivo | `stopbuy`, `start`/`stop` | Risk Sentinel |

## Reglas duras (no negociables)

1. **Nunca Live sin dry-run positivo.** El paso Dry→Live lo aprueba el Manager y exige **OK
   explícito del usuario**. (Regla del usuario para todo riesgo/acción irreversible.)
2. **Stoploss siempre presente.** No hay trade sin stoploss. Config y estrategia deben definir
   `stoploss` (config pisa estrategia → `show-config` para verificar).
3. **Correlacionar stoploss y leverage.** `stoploss` = riesgo RELATIVO del trade. Con 10x, un
   stoploss -10% gatilla con -1% de precio. No usar stoploss ajustado a alto leverage sin margen.
4. **Preferir stoploss-market** en mercados que caen (un limit puede no llenarse → pérdida mayor).
5. **Volar del overfitting.** Backtest reproducible con `test-pairlist` + train/val/test separados.
6. **Funding en futuros.** Revisar funding rates; stoploss_price_type según exchange y estrategia.

## Delists / shutdown (regla de la lección aprendida)

El screening de "precio barato ≠ oportunidad" (skill `crypto-token-analysis`, paso 8) mostró
que las señales de riesgo más peligrosas NO se ven en mcap/precio sino en **noticias**:
- Protocolo bajando (ej. Goldfinch wind-down) → backing a16z/Coinbase irrelevante, ATL = señal de muerte.
- Delist de exchange top (ej. Storj en Binance) → colapso a ATL, drenado de liquidez.

**Acción:** Risk Sentinel consulta noticias/status de cada par nuevo (web_search + The Graph
on-chain) y aplica `blacklist`/`lock_pair` ante eventos de cierre/delist/regulatorio, sin
importar cuán barato o bien respaldado se vea en papel.

## Umbrales de aceptación propuestos (para Backtester/Hyperopt)

Indicativos — se calibran en SDD. Sugerencia inicial:
- Profit factor > 1.3 (objetivo), rechazo < 1.0.
- Max drawdown < 30%.
- Wins >= 30 trades (mín para no sobreajustar).
- Sortino/Sharpe positivos en data out-of-sample.

## Fuentes de riesgo externas que alimentan la capa

- **The Graph (subgraphs)**: whale inflows, holders creciendo, TVL on-chain, liquidaciones DeFi.
- **CoinGecko sparkline**: momentum 7d/24h y volumen (scanner ya probado).
- **Noticias / delists / shutdown**: web_search + Scrapling.
