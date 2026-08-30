# Diseño de la Oficina de Agentes — Freqtrade Multi-Agent

> Artefacto de diseño (fase "Idea"). Documenta la concepción de la oficina de agentes.

## Principio rector: la documentación es la estructura organizacional

Freqtrade tiene una documentación enorme y densa en parámetros (~45 capítulos en `stable`).
Ningún agente general puede dominarla entera sin reventar su contexto (lección validada en el
entorno: meter ~15 items con detalle ya satura un LLM). La solución es **repartir la
documentación como el organigrama**: cada agente se apropia de **un capítulo (o bloque afín)
como su dominio de referencia**, y la **densidad** de cada capítulo dicta cuántos agentes se le
asignan.

Tres reglas de derivación del organigrama desde la doc:
1. **El capítulo es la fuente de verdad del agente.** Cuando el agente decide, "consulta su
   documentación" (que vive en su `memoria/`/prompt) en vez de alucinar. La doc es el punto
   referencial, no el código.
2. **Densidad determinante.** Un capítulo de baja densidad (ej. `installation`, `faq`) puede
   fusionarse en un agente ligero. Un tema denso con varios subcapítulos (ej. **FreqAI = 7
   subcapítulos**) genera **un agente por subcapítulo** (1 agente por `freqai-configuration`,
   otro por `freqai-feature-engineering`, etc.).
3. **El rol es secundario; el dominio documental es primario.** El organigrama se deriva del
   árbol de la documentación, no de funciones inventadas. Las funciones (acción sobre
   freqtrade) quedan como *tools que el capítulo habilita*.

### Mapa de densidad → agentes (desde sitemap `stable`)

| Bloque de doc | Capítulos | Densidad | Asignación de agentes |
|---|---|---|---|
| **FreqAI** | freqai + freqai-configuration, -feature-engineering, -parameter-table, -running, -reinforcement-learning, -developers | 🔴🔴 máxima (7) | **1 agente por subcapítulo = 7 agentes** |
| **Estrategia** | strategy-101, strategy-advanced, strategy-customization, strategy-callbacks | 🔴 muy alta (4) | 1 agente por capítulo = 4 |
| **Backtest/Análisis** | backtesting, advanced-backtesting, lookahead-analysis, recursive-analysis | 🔴 muy alta (4) | 1 por capítulo = 4 |
| **Config** | configuration | 🔴 alta (1 gigante) | 1 agente dedicado (el más denso en parámetros) |
| **Hyperopt** | hyperopt, advanced-hyperopt | 🔴 alta (2) | 1 por capítulo = 2 |
| **Riesgo/Futuros** | stoploss, leverage, exchanges | 🟡 media-alta (3) | 1 agente de riesgo (fusiona) |
| **Control/UI** | rest-api, freq-ui, telegram-usage, webhook-config | 🟡 media (4) | 2 agentes (REST/UI + notificaciones) |
| **Datos/Utils** | data-download, data-analysis, trade-object, utils, sql_cheatsheet | 🟡 media (5) | 2 agentes (datos + análisis) |
| **Extensiones** | plugins, producer-consumer | 🟡 media (2) | 1 agente |
| **Infra/Operativo** | installation, docker_quickstart, advanced-setup, bot-basics, bot-usage, updating, faq, deprecated, developer | 🟢 baja (9) | 1-2 agentes ligeros (manager/ops) |

> La asignación exacta (qué capítulo → qué agente, cuánta capacidad de LLM por agente) es
> parte de la **depuración de la idea**; este mapa es un borrador para discutir, no una decisión final.

## Principios operativos de control por módulos

1. **Un dominio por agente.** Cada empleado es dueño de su capítulo/capítulos de la doc y de las
   acciones que ese capítulo habilita; no toca el dominio del vecino.
2. **Separación config/estrategia/protección.** Freqtrade ya separa `config` (JSON/env,
   precedencia CLI > env > config > estrategia) de `strategy` (Python/pandas) de `protections`
   de `stoploss`. Coincide con los dominios documentales: `configuration/`, `strategy*`, `stoploss/`.
3. **Validación antes de ejecución.** Ningún dominio pasea a Live sin pasar Validación →
   Optimización → Riesgo → Dry-run → OK explícito del usuario.
4. **Persistencia.** Empleados persistentes (MCP servers), no crews que se disuelven (patrón
   MCP Agent Office, no CrewAI). Cada uno guarda su doc de referencia y memoria en `memoria/`.
5. **LLM fuera del loop crítico.** Las acciones de trading (entradas, stoploss, cortes) NO
   dependen de un LLM en tiempo crítico. El LLM usa su capítulo para decidir estrategia/
   parámetros; la ejecución es determinista en freqtrade.

## Modelo LLM por dominio documental (vía Bifrost / LiteLLM :4000)

La capacidad del LLM se asigna según la **densidad y complejidad del capítulo** que domina
(criterio de la idea). Borrador para discutir — parte de la depuración.

| Dominio (capítulo) | Modelo sugerido | Por qué |
|---|---|---|
| `configuration` (Config) | DeepSeek V4 Pro | Parámetros y precedencias complejas |
| `strategy*` (Estrategia, 4) | DeepSeek V4 Pro | Lógica de indicadores y entry/exit |
| `freqai*` (ML, 7) | Llama 70B | Razonamiento profundo sobre modelos/features |
| `backtesting*` / `lookahead` / `recursive` | Llama 70B | Lectura de métricas y análisis de resultados |
| `hyperopt*` (Optimización) | DeepSeek V4 Flash | Barridos repetitivos, respuesta rápida |
| `stoploss`/`leverage`/`exchanges` (Riesgo) | DeepSeek V4 Pro | Juicio de riesgo importante |
| `rest-api`/`freq-ui` (Control) | DeepSeek V4 Flash | Acciones concretas y rápidas |
| `telegram-usage`/`webhook-config` (Notif) | Llama 8B | Rutinas, barato |
| `data-*`/`utils`/`sql` (Datos) | Llama 8B | Tareas repetitivas de datos |
| `plugins`/`producer-consumer` (Ext) | Llama 8B | Extensión modular |
| `installation`/`bot-basics`/`faq` (Ops) | Llama 8B | Operativo, baja carga |
| Manager (orquestador del todo) | DeepSeek V4 Pro | Agregar múltiples dominios, decidir dry→live |

> Nota: esto reemplaza la antigua tabla "por función" (Strategy Smith, Hyperoptimizer, etc.).
> Los roles siguen existiendo pero ahora son *consecuencia* del capítulo que dominan.

## Herramientas por dominio documental

Cada dominio (capítulo) habilita unas herramientas. Estas cruzan el capítulo con el comando
CLI o endpoint REST que ese dominio usa.

### Comandos CLI (Taller — procesos pesados)

| Dominio (capítulo) | Comando freqtrade |
|---|---|
| `data-download` | `freqtrade download-data -c <cfg> -t <tf> --timerange <rango>` |
| `strategy*` | (escribe `user_data/strategies/<name>.py`) |
| `backtesting*` | `freqtrade backtesting -s <strategy> --strategy-list <a b c> --timerange <r> -i <tf>` |
| `hyperopt*` | `freqtrade hyperopt -s <strategy> --spaces buy sell roi stoploss trailing protection -e <n>` + `hyperopt-show` |
| `stoploss`/`leverage` | edita `order_types`, `stoploss`, `trailing_*`, `protections`, `stoploss_price_type`, leverage |

### Endpoints REST (Despacho — en vivo `/api/v1`)

| Endpoint | Dominio (capítulo) | Uso |
|---|---|---|
| `available_pairs` | `data-*` | pares con datos disponibles |
| `pairlists` / `performance` / `pair_candles` | `data-*` | screening en vivo |
| `forceenter` / `forceexit` / `status` | `rest-api` / `freq-ui` | long/short, leverage, posiciones |
| `blacklist` / `lock_pair` / `stopbuy` / `start` / `stop` / `logs` | `stoploss` (Risk Sentinel) | protección y control en vivo |
| `profit` / `daily` / `weekly` / `monthly` / `stats` / `mix_tags` / `entries` / `exits` | `data-analysis` | reporte P/L |
| `reload_config` / `show_config` | `configuration` | aplicar/ver config (Manager) |

## Autenticación REST API

- Habilitar `api_server.enabled=true` en config (escucha `127.0.0.1:8080` por defecto).
- Endpoints sensibles requieren JWT: `POST /api/v1/token/login` → access token (15 min),
  refresh con `token/refresh`.
- No exponer la API a internet (solo localhost / túnel VPN para VPS).
- Usar `freqtrade-client` (`from freqtrade_client import FtRestClient`) como cliente liviano.

## El patrón de conexión (MCP tool-only)

El contenedor `freqtrade-mcp` usa el patrón **"Direct httpx"** (skill `mcp-agent-office`):
envuelve la REST API de freqtrade con FastMCP, cada endpoint = una tool MCP. Sin subprocess,
sin loop LLM en el medio. Los agentes por capítulo quedan como empleados persistentes que
llaman estas tools según su dominio.

```yaml
# config.yaml de Hermes (agente de ejemplo)
mcp_servers:
  freq_manager:
    command: C:\Python314\python.exe
    args:
      - C:\Users\P0zcl\Desktop\proyectos\freq\prototype\freqtrade-mcp\mcp_server.py
    env:
      FREQTRADE_URL: http://127.0.0.1:8080
      FREQTRADE_USER: Freqtrader
      FREQTRADE_PASS: '<secreto>'
      FREQTRADE_WORKER: manager
    enabled: true
```

## Riesgos / gobernanza

- **Capital real**: solo tras dry-run positivo + OK explícito del usuario. Regla del usuario.
- **Delists / shutdown**: Risk Sentinel aplica `blacklist`/`lock_pair` ante eventos de cierre.
- **Overfitting en backtest**: usar `test-pairlist` para reproducible, data exclusiva de train/val/test.
- **Leverage**: stoploss = riesgo del trade; stoploss -10% a 10x se gatilla con -1% de precio.
- **Funding**: el bot lo gestiona en futuros; revisar `stoploss_price_type` (`last`/`mark`/`index`).
