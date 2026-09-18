# Freqtrade Multi-Agent Framework

> **Base implementada y operativa** — sistema de agentes LLM especializados que operan
> freqtrade, donde cada agente se apropia de **un bloque documental** de la documentación
> oficial con **RAG propio** (cerebro) y herramientas de control (manos, feature 003).
>
> **Para entender el proyecto en profundidad** (arquitectura, módulos, tools, formatos,
> estado): leer `docs/ARQUITECTURA.md` — es el documento maestro.

## Inicio rápido

```bash
# 1. Entorno (Python 3.11+; en Windows usar el venv del proyecto, nunca el global)
python -m venv .venv && . .venv/Scripts/activate   # o .venv/bin/activate en Linux
unset PYTHONPATH                      # obligatorio si hay un PYTHONPATH global
pip install -r requirements.txt

# 2. Configuracion (copia y completa; .env nunca se versiona)
cp .env.example .env                  # EMBED_* / GEMINI_API_KEY / LLM_* / FREQTRADE_*

# 3. Corpus de documentacion (ya incluido en docs-freqtrade* ; regenerable)
python tools/fetch_docs.py --branch develop --out docs-freqtrade
python tools/fetch_docs_web.py --out docs-freqtrade-web

# 4. Indexar el RAG (12 bloques documentales)
python tools/index_blocks.py

# 5. Probar
python tools/query_block.py 02-configuracion "how to enable futures trading"
python tools/benchmark_rag.py 02-configuracion     # recall@1/@3, MRR

# 6. Gateway MCP universal (un endpoint HTTP para cualquier agente/LLM)
python servers/gateway_http.py --transport streamable-http
# -> http://0.0.0.0:8765/mcp   (19 tools, solo-lectura por defecto)

# 7. Tests
python -m pytest tests/ -q
```

> **Portabilidad**: los ejemplos de configuración de este repo usan rutas de una
> instalación concreta (p. ej. `C:\Users\<usuario>\Desktop\proyectos\freq`). Sustitúyelas
> por la ruta donde clonaste el repo. Ningún script depende de una ruta de usuario: la
> raíz del proyecto se deriva de la ubicación del propio archivo.

## Clonar en otra máquina

El repositorio **no versiona los índices del RAG** (`data/rag/`, gitignored) ni el grafo
del código (`graphify-out/`): ambos son artefactos regenerables y pesados. Tras clonar hay
que reconstruirlos, o el primer arranque falla con `INDEX_MISSING`.

```bash
git clone https://github.com/ssolis-ti/freqtrade-mcp.git && cd freqtrade-mcp

# 1. Entorno (Windows: .venv/Scripts/activate)
python -m venv .venv && . .venv/bin/activate
unset PYTHONPATH                  # obligatorio si hay un PYTHONPATH global
pip install -r requirements.txt

# 2. Credenciales (nunca se versionan)
cp .env.example .env              # completar GEMINI_API_KEY / LLM_* / EMBED_* / FREQTRADE_*

# 3. Reconstruir los índices del RAG (12 bloques; el corpus SÍ viene en el repo)
python tools/index_blocks.py      # sin GEMINI_API_KEY degrada a local-hash (funcional, menos preciso)

# 4. Verificar
python tools/verificar_indices.py
python -m pytest tests/ -q
```

Opcional — grafo del código (local, sin coste, sin LLM; habilita las tools `grafo_*` del
gateway):

```bash
graphify extract . --code-only --no-viz   # requiere: uv tool install "graphifyy[mcp]"
```

> Lo que **sí** viaja en el repo: los dos mirrors de documentación (`docs-freqtrade/`,
> `docs-freqtrade-web/`), el código, las specs y el baseline de benchmark. Lo que **no**:
> `.env`, `.venv/`, `data/rag/`, `graphify-out/`.

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

**Base fundamental implementada y operativa** (features 001 + 002, 26/26 tests GREEN):
corpus descargado, RAG por bloque, agentes LLM por bloque, MCP stdio validado,
benchmark funcional. El estado pormenorizado (índices, pendientes, limitaciones) está
en `docs/ARQUITECTURA.md` sección 10.

Lo que sigue (feature 003 — **spec definido**, pendiente de implementación):
- `despacho/` — capa de operación: wrapper REST integrable, gate de permisos (OK del
  usuario para tools de ejecución), Manager orquestador, cadena dry-run.
- Conectar los agentes al wrapper REST de freqtrade (`prototype/freqtrade-mcp`, 19 tools)
  para que puedan OPERAR (forceenter, forceexit, blacklist, ...).
- Cadena de validación (datos → estrategia → backtest → hyperopt → riesgo) en dry-run.
- Paso dry-run → live: **solo con OK explícito del usuario** (regla dura, constitution III).
- Detalle completo: `specs/003-despacho-operativo/`.

## Lecturas de referencia

- `docs/ARQUITECTURA.md` — **documento maestro** (arquitectura, módulos, tools, formatos, estado).
- `docs/conector-universal.md` — **gateway MCP HTTP**: un endpoint para cualquier agente/LLM
  (19 tools, solo-lectura por defecto, LAN).
- `docs/graphify-evaluacion.md` — evaluación del knowledge graph (código vs docs).
- `docs/oficina-agentes.md` — diseño de la oficina (roles, modelos, endpoints, capas).
- `docs/freqtrade-integracion.md` — comandos CLI y endpoints REST verificados de la doc
  oficial (mapa de la maquinaria que los agentes controlan).
- `docs/risk-modulo.md` — cuadro de control de riesgo (stoploss/leverage/futuros/delists).
- `specs/001-framework-rag-mcp/`, `specs/002-agentes-llm-bloque/` y
  `specs/003-despacho-operativo/` — specs SDD del diseño.

---

*Documento de fase "Idea". No contiene datos reales de trading ni credenciales.*
