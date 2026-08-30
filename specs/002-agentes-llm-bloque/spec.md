# Feature Specification: Agentes LLM por bloque

**Feature Branch**: `002-agentes-llm-bloque`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "La base de proyecto es que como es muy denso dijimos que
hariamos un agente con rag por cada bloque" + decision de arquitectura: un agente LLM por
bloque documental, cada uno con su RAG (feature 001) y su modelo del gateway LiteLLM/Bifrost.

## Contexto (verificado en vivo, 2026-08-30)

- Feature 001 completo: 12 bloques indexados (2,323 chunks), MCP por bloque con
  `consultar_docs` + `health`, tests 18/18, git commit `4789c3d`.
- Gateway LLM `:4000` (LiteLLM, master key local en litellm.env): **21 modelos LLM
  operativos** (deepseek-v4-flash/pro, deepseek-via-inference(-pro), kimi-k3, grok-4.6,
  glm-5.3, nemotron, gpt-oss...).
- Embeddings del gateway: **rotos** — `nvidia-embed` (nv-embedqa-mistral-7b-v2) devuelve
  404/429 (modelo no desplegado en la cuenta NIM). inference.net no lista modelos sin
  gastar credito. → embeddings semanticos locales (sentence-transformers) como upgrade
  opcional; local-hash sigue como fallback base.

## User Scenarios & Testing

### User Story 1 - El agente del bloque responde con fundamento (Priority: P1)

Como agente LLM de un bloque documental, quiero responder preguntas del dominio usando el
RAG de mi bloque (feature 001) como unica fuente, citando los chunks recuperados, para
decidir con fundamento y sin alucinar.

**Why this priority**: Es el corazon del feature: el LLM + RAG = el agente del bloque.

**Independent Test**: Levantar el agente del bloque piloto y preguntar algo del dominio
(ej. "como activo futuros en freqtrade"); la respuesta debe citar chunks con
mirror/path/heading y no inventar parametros.

**Acceptance Scenarios**:

1. **Given** el agente del bloque `02-configuracion` con RAG indexado, **When** se le
   pregunta algo del dominio, **Then** responde con texto fundamentado y cita los chunks
   usados (mirror, path, heading, score).
2. **Given** el LLM del gateway responde, **When** la respuesta se construye, **Then**
   incluye la lista de citas en formato JSON estructurado.

---

### User Story 2 - El agente no alucina fuera de su bloque (Priority: P1)

Como agente, quiero rechazar explicitamente preguntas fuera del corpus de mi bloque o sin
hits suficientes, para no inventar informacion ni cruzar dominios (constitution II).

**Why this priority**: Aislamiento y no-alucinacion son los principios que justifican
todo el diseno (constitution II).

**Independent Test**: Preguntar algo de otro bloque (ej. "como configuro FreqAI" al agente
de configuracion) → el agente responde que no esta en su dominio, sin intentar responder.

**Acceptance Scenarios**:

1. **Given** una pregunta sin hits en el bloque (bajo min_score), **When** el agente
   recibe la pregunta, **Then** responde un rechazo explicito ("fuera de mi dominio")
   sin generar contenido no fundamentado.
2. **Given** el LLM no responde (timeout/error), **When** se intenta responder, **Then**
   el agente degrada devolviendo los hits crudos del RAG (nunca inventa).

---

### User Story 3 - Modelo LLM configurable por bloque (Priority: P2)

Como operador, quiero asignar el modelo de cada agente via config (mapa bloque->modelo
del gateway), para usar el modelo adecuado por densidad (pro para config/estrategia/riesgo,
flash para datos/operativo).

**Why this priority**: El mapa de densidad (oficina-agentes.md) asigna modelos distintos
por dominio; sin config por bloque no se puede aplicar.

**Independent Test**: Configurar el agente del bloque piloto con `deepseek-v4-pro` y
verificar via health que usa ese modelo; cambiar a `deepseek-v4-flash` y verificar.

**Acceptance Scenarios**:

1. **Given** `AGENT_MODEL_02_CONFIGURACION=deepseek-v4-pro` en env, **When** el agente
   arranca, **Then** health reporta ese modelo y las respuestas lo usan.
2. **Given** un modelo inexistente en el gateway, **When** el agente responde, **Then**
   degrada al modelo default (`deepseek-via-inference`) con warning.

---

### User Story 4 - Benchmark de calidad del agente (Priority: P3)

Como operador, quiero medir objetivamente la calidad del agente (recuperacion y
fundamento) sobre un golden set, para comparar configuraciones (local-hash vs embeddings
semanticos, modelo X vs Y).

**Why this priority**: Sin medicion no hay decision de configuracion informada.

**Independent Test**: Correr el benchmark sobre el bloque piloto; reporta recall@1/@3 y
% de respuestas fundamentadas.

**Acceptance Scenarios**:

1. **Given** el golden set de ~20 preguntas con chunk esperado, **When** corre el
   benchmark, **Then** reporta recall@1, recall@3, MRR y groundedness.
2. **Given** el benchmark corriendo, **When** termina, **Then** escribe un reporte JSON
   reutilizable para comparar configuraciones.

---

### Edge Cases

- LLM caido (timeout/401/429): degrada a hits crudos del RAG.
- Pregunta en espanol con corpus en ingles: con local-hash probablemente no-hits (rechazo
  correcto); con embeddings semanticos locales mejora (a medir en benchmark).
- Bloque sin indexar: `INDEX_MISSING` claro (ya en feature 001).
- Modelo configurado que no existe en gateway: fallback a default.
- Respuesta larga truncada por max_tokens del modelo: incluir nota de truncamiento.

## Requirements

### Functional Requirements

- **FR-001**: Cada bloque expone un agente LLM (MCP tool `responder`) que usa el RAG del
  bloque como unica fuente + LLM del gateway para responder.
- **FR-002**: Las respuestas incluyen citas estructuradas (chunk_id, mirror, path,
  heading, score) en JSON.
- **FR-003**: Sin hits suficientes (bajo min_score) el agente responde rechazo explicito,
  nunca inventa ni cruza bloques.
- **FR-004**: El modelo LLM es configurable por bloque via env (`AGENT_MODEL_<BLOQUE>`),
  con default `deepseek-via-inference` y fallback si el modelo no existe.
- **FR-005**: Si el LLM falla (timeout/error), el agente degrada devolviendo los hits
  crudos del RAG.
- **FR-006**: El agente se expone como MCP server stdio (patron feature 001), tool
  `responder` + `health` ampliado (modelo activo).
- **FR-007**: Benchmark con golden set (~20 preguntas) mide recall@1/@3, MRR y
  groundedness; reporte JSON.
- **FR-008**: No se toca el config del gateway LiteLLM externo; el agente usa el gateway
  como cliente (solo lectura de modelos).

### Key Entities

- **Agente de bloque**: MCP server = Retriever (RAG, feature 001) + LLM client (gateway)
  + mapa de modelo.
- **Golden set**: pares (pregunta, chunk_id esperado, bloque).
- **Respuesta fundamentada**: texto + citas JSON.
- **Mapa bloque->modelo**: config env `AGENT_MODEL_<BLOQUE_ID>`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: El agente del bloque piloto responde con citas validas (mirror/path/heading
  existentes en el corpus) en el 100% de las respuestas con hits.
- **SC-002**: Preguntas fuera de dominio producen rechazo explicito en 100% de los casos
  de prueba (sin alucinacion).
- **SC-003**: Con LLM caido (simulado), el agente degrada a hits crudos sin fallar.
- **SC-004**: health reporta el modelo configurado y el activo.
- **SC-005**: Benchmark genera reporte JSON con recall@1/@3 y groundedness reutilizable.

## Assumptions

- El gateway `:4000` con master key local esta disponible para los agentes (cliente).
- Se usan los modelos ya configurados en el gateway (deepseek-via-inference default);
  no se anade ningun modelo nuevo al gateway sin OK del usuario.
- Embeddings: se mantiene local-hash por defecto; sentence-transformers (semantico local)
  es un upgrade opcional del feature 003 (depende de OK del usuario para instalar ~100MB).
- Bloque piloto: `02-configuracion`.
- El registro en Hermes (T033/feature 001) se hara junto con este feature (un solo
  `config.yaml` edit).
- Mismo entorno Windows: `.venv/Scripts/python.exe`, `unset PYTHONPATH`, sin `python -c`.

**Estado**: Draft (pendiente de plan y aprobacion).
