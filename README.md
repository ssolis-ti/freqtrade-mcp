# Freqtrade Multi-Agent Framework

> **Idea + Prototipo** — diseño de cómo operar freqtrade con múltiples agentes LLM
> especializados. El `prototype/` es una prueba funcional mínima de la premisa.

## ¿Qué es esto?

Operar **freqtrade** (bot de trading crypto open source) como una **maquinaria controlada por
múltiples agentes LLM especializados**, donde cada agente se apropia de **un capítulo (o
bloque afín) de la documentación de freqtrade como su dominio de referencia**. Todos cohabitan
como empleados persistentes (patrón MCP Agent Office), sin pisarse entre sí.

**Principio rector: la documentación es la estructura organizacional.** Freqtrade tiene ~45
capítulos en `stable`, densos en parámetros; ningún agente general los domina sin reventar su
contexto. Se reparte la documentación como organigrama: **densidad del capítulo → cuántos
agentes**. Un capítulo ligero (ej. `installation`) se fusiona en un agente pequeño; un tema
denso con subcapítulos (ej. **FreqAI = 7**) genera **un agente por subcapítulo** (1 por
`freqai-configuration`, 1 por `freqai-feature-engineering`, …). El capítulo es la fuente de
verdad del agente; las funciones (acción sobre freqtrade) son *tools que el capítulo habilita*.

Freqtrade se expone por **dos superficies de control**, que se reparten naturalmente entre agentes:

- **Superficie CLI** (estado estable, procesos pesados): `download-data`, `backtesting`,
  `hyperopt`, `new-config`, `test-pairlist` → agentes de **"Taller"** (diseño/optimización).
- **Superficie REST API** (`/api/v1`, ~50 endpoints): `forceenter`, `forceexit`, `blacklist`,
  `lock_pair`, `status`, `profit`, `balance`, `start/stop/stopbuy`, `reload_config`
  → agentes de **"Despacho"** (operación en vivo 24/7).

La tesis central: **cada agente es dueño de su dominio documental**. Ninguno muta la estrategia
del otro ni override el riesgo. El único paso Dry-run → Live lo autoriza el Manager **con OK
explícito del usuario**.

## Origen / por qué existe

El usuario opera futuros cripto en horizonte de ~1 semana (caza de alts con momentum, detección
de zonas de venta/liquidez). Se evaluaron alternativas:

- **crypto-signal** (fork propio, archivado): buen esqueleto CCXT + Telegram + modular, pero
  es spot, sin backtest/hyperopt/futuros, y está read-only. → se descarta como base de código.
- **The Graph (subgraphs)**: añade capa on-chain (whale inflows, holders creciendo, TVL real,
  liquidaciones DeFi) como **filtro de screening** — complementario, no sustituye nada.
- **Freqtrade**: framework de trading más maduro (backtest, hiperoptimización con ML, futuros
  con leverage nativo, dry-run, REST API). → **base elegida**.
- **Multi-agente**: freqtrade es una máquina de muchos parámetros y documentación densa;
  repartir la doc por capítulos entre agentes reduce ruido y permite control por módulos
  (patrón MCP Agent Office / Editorial_IA_MCP).

## Arquitectura de la "oficina de trading"

El organigrama se deriva del **árbol de la documentación**, no de funciones inventadas.
El reparto exacto (qué capítulo → qué agente, qué modelo de LLM, qué tools habilita) está en
`docs/oficina-agentes.md` y **se está depurando** (ver preguntas abiertas).

En resumen, los dominios documentales que definen a los empleados:

- **Config** → `configuration/` (parámetros, precedencias, multi-config)
- **Estrategia** → `strategy-101/-advanced/-customization/-callbacks` (4 agentes)
- **Backtest/Análisis** → `backtesting`, `advanced-backtesting`, `lookahead-analysis`, `recursive-analysis` (4 agentes)
- **Optimización** → `hyperopt`, `advanced-hyperopt` (2 agentes)
- **FreqAI (ML)** → 7 subcapítulos → **7 agentes** (uno por subcapítulo)
- **Riesgo/Futuros** → `stoploss`, `leverage`, `exchanges`
- **Control** → `rest-api`, `freq-ui`
- **Notificaciones** → `telegram-usage`, `webhook-config`
- **Datos/Utils** → `data-download`, `data-analysis`, `utils`, `sql_cheatsheet`, `trade-object`
- **Extensiones** → `plugins`, `producer-consumer`
- **Infra/Op** → `installation`, `docker_quickstart`, `bot-basics`, `faq`, `updating`, `developer`, …
- **Manager** (orquestador) → agrega todos los dominios, decide dry→live

### 🙋 Usuario

Autoriza el paso a Live (regla: **nunca arriesgar capital real sin OK explícito**).

## Flujo de control

```
👔 Manager recibe misión: "cazar alts de momentum 7d para futuros"
   ├─ agente data-*/ → descarga datos históricos de candidatos
   ├─ agente strategy*-* → escribe estrategia de momentum (RSI + volumen + sparkline)
   ├─ agente backtesting* → valida contra datos reales (profit factor, drawdown)
   ├─ agente hyperopt* → optimiza ROI/stoploss/trailing (optuna / ML)
   ├─ agente stoploss/leverage → fija riesgo, trailing, límites de leverage
   ↓ (solo si los dominios de validación/riesgo dan el OK)
👔 Manager → valida en DRY-RUN (cero riesgo, mismo exchange)
   ↓ (solo con OK explícito del usuario)
Despacho opera en LIVE (agentes de rest-api/freq-ui + datos):
   ├─ agente rest-api → pairlist en vivo
   ├─ agente freq-ui → long/short con leverage y control de posiciones
   ├─ agente stoploss → vigila y corta pérdidas (Risk Sentinel)
   └─ agente data-analysis → reporta P/L
```

> Cada paso es ejecutado por el agente cuyo **capítulo documental** lo habilita. El Manager
> orquesta entre dominios; ningún dominio salta por encima del otro.

## Stack técnico objetivo

- **freqtrade** (Docker, `stable`): engine de estrategia, backtest, hyperopt, futuros.
- **REST API** `/api/v1` + `freqtrade-client` (librería `FtRestClient`) para agentes de despacho.
- **CLI** subprocess para agentes de taller (backtest/hyperopt son pesados).
- **MCP servers** (FastMCP): cada agente = un empleado persistente con su modelo de LLM.
- **Bifrost / LiteLLM `:4000`**: cerebro LLM local por agente (patrón Editorial_IA_MCP).
- **The Graph (subgraphs)** + **CoinGecko sparkline** (scanner ya probado): screening on-chain
  + momentum que alimenta a Market Scout.
- **Hermes Agent**: registra los MCP (`mcp_servers` en `config.yaml`; `hermes mcp add` cuelga
  con stdio → escribir directo en config + `/reload-mcp`).

## Prototipo (premisa a validar)

En `prototype/` se incluye el **`freqtrade-mcp` wrapper tool-only** de la REST API de
freqtrade (patrón "Direct httpx" del skill `mcp-agent-office`), que expone los endpoints
operativos como tools MCP. Estas tools son las que **los agentes por capítulo** (ej. el agente
de `rest-api`, el de `stoploss`) usan para ejercer su dominio sobre freqtrade.

## RAG por bloque (cerebro documental)

Cada bloque documental de los 12 se indexa desde **ambos mirrors** (`docs-freqtrade/`
fuente + `docs-freqtrade-web/` estable) y se expone como un **MCP server propio** con
recuperación vectorial. El agente de un bloque consulta **solo su corpus** (aislamiento;
nunca cruza bloques ni inventa: no-hits explícito).

### Stack

- `rag/` — núcleo: chunking jerárquico por cabeceras con split por tamaño, embeddings
  (gateway LiteLLM/Bifrost por env, fallback local determinista), vector store ligero
  (numpy + coseno), indexador idempotente, recuperador top-k.
- `servers/run_bloque.py <id>` — MCP FastMCP por bloque con tools `consultar_docs` y
  `health`.
- `tools/index_blocks.py` / `tools/query_block.py` — CLI de indexación y consulta.

### Uso

```bash
# 1. Indexar el bloque piloto (o todos: sin argumento)
python tools/index_blocks.py 02-configuracion

# 2. Consultar sin MCP (depuracion)
python tools/query_block.py 02-configuracion "como activo trading de futuros"

# 3. Levantar el MCP del bloque (stdio, para Hermes)
python servers/run_bloque.py 02-configuracion
```

Configuración de embeddings en `.env` (ver `.env.example`): `EMBED_BASE_URL`,
`EMBED_MODEL`, `EMBED_API_KEY`. Sin gateway disponible, degrada automáticamente a
embeddings locales deterministas.

### Embeddings semánticos (Google Gemini, free tier)

Desde feature 001, el backend de embeddings tiene 3 niveles de prioridad:

1. **Google Gemini** (`gemini-embedding-001`, free tier — $0 por 1M tokens) si hay
   `GEMINI_API_KEY` en `.env` (crear en https://aistudio.google.com/apikey). Semántico y
   multilingüe (dim 768 configurable).
2. **Gateway LiteLLM/Bifrost** (`EMBED_BASE_URL` + `EMBED_MODEL`) si responde.
3. **`local-hash`** — determinista, sin red (aproximación por palabras clave).

Límites del free tier de Gemini: 100 requests/min. El indexador respeta el límite
(sleep entre batches + retry con backoff en 429) y valida la dimensión devuelta.

```bash
# Reindexar todo con Gemini (o un bloque: python tools/index_blocks.py 02-configuracion --force)
python tools/index_blocks.py --force
# El manifiesto index.json queda con embed_model=gemini:gemini-embedding-001
```

### Registro en Hermes (un server por bloque)

```yaml
mcp_servers:
  freq_config:
    command: <proyecto>/.venv/Scripts/python.exe
    args:
      - <proyecto>/servers/run_bloque.py
      - 02-configuracion
    enabled: true
```

El patrón se repite por cada bloque (12 servers) + el Manager. Registro manual en
`config.yaml` (el comando `hermes mcp add` cuelga con stdio en este entorno) y luego
`/reload-mcp` en la sesión.

### Escalado

El framework es parametrizado por bloque: escalar a los 12 = indexar los demás bloques y
levantar un server por cada uno. Sin rediseño (FR-008). Detalle de diseño en
`specs/001-framework-rag-mcp/` (spec-driven, Spec-Kit).

## Agentes LLM por bloque (cerebro + voz)

Sobre el RAG se construye la capa de **agentes LLM**: cada bloque se expone como un MCP
server que responde preguntas del dominio con **fundamento y citas** (el RAG es la única
fuente; el LLM del gateway LiteLLM/Bifrost `:4000` redacta la respuesta).

### Reglas de diseño (constitution)

- Sin hits suficientes en el bloque → el agente **rechaza explícitamente** (no inventa,
  no cruza bloques, no gasta crédito llamando al LLM).
- Si el LLM falla → **degrada a los hits crudos** del RAG (nunca alucina).
- Modelo configurable por bloque vía env: `AGENT_MODEL_<BLOQUE>` (default
  `AGENT_MODEL_DEFAULT=deepseek-via-inference`).

### Uso

```bash
# Levantar el agente del bloque (MCP stdio)
python servers/run_agente.py 02-configuracion
# Tools: responder(query, top_k) | consultar_docs(query, top_k) | health()

# Benchmark de calidad del RAG (recall@1/@3, MRR) — baseline para comparar configs
python tools/benchmark_rag.py 02-configuracion
# → data/benchmark/02-configuracion.json
```

Config en `.env` (ver `.env.example`): `LLM_BASE_URL`, `LLM_API_KEY` (key local del
gateway, gitignored), `AGENT_MODEL_DEFAULT`, `AGENT_MODEL_<BLOQUE>` opcional.

### Registro en Hermes (agente)

```yaml
mcp_servers:
  freq_config:
    command: <proyecto>/.venv/Scripts/python.exe
    args:
      - <proyecto>/servers/run_agente.py
      - 02-configuracion
    enabled: true
```

Tools expuestas: `mcp_freq_config_responder`, `mcp_freq_config_consultar_docs`,
`mcp_freq_config_health`. Detalle en `specs/002-agentes-llm-bloque/`.

## Estado actual

**Depurando la idea y el prototipo.** Este documento queda en modo **idea** mientras se
define la oficina de agentes y se valida la premisa del prototipo. El desarrollo (incluido
cualquier formato spec-driven) se hará **después** de tener la idea definida, no antes.

Aún por depurar / preguntas abiertas:
- ¿En qué bloque hay que **romper más** la documentación y en cuál **fusionar**? El borrador
  asigna FreqAI=7 agentes, Estrategia=4, Backtest=4; ¿se sostiene o se ajusta por densidad real?
- ¿El agente del capítulo debe **cargar ese capítulo en su contexto/prompt** o hacer **RAG**
  sobre un índice de toda la doc y traer solo su sección? (método de "consulta la doc" pendiente).
- ¿Empezamos con un **subconjunto MVP** (ej. solo Config + Estrategia + Backtest + Riesgo) y
  añadimos FreqAI después, o lo hacemos completo desde el inicio?
- ¿El contenedor `freqtrade-mcp` debe ser tool-only (sin LLM) o llevar LLM por capítulo?
- ¿El paso dry-run → Live queda solo autorizado por el usuario (regla dura), o puede haber
  límites automáticos del agente de stoploss/leverage?

## Lecturas de referencia

- `docs/oficina-agentes.md` — diseño de la oficina (roles, modelos, endpoints, capas).
- `docs/freqtrade-integracion.md` — comandos CLI y endpoints REST verificados de la doc
  oficial (mapa de la maquinaria que los agentes controlan).
- `docs/risk-modulo.md` — cuadro de control de riesgo (stoploss/leverage/futuros/delists).

---

*Documento de fase "Idea". No contiene datos reales de trading ni credenciales.*
