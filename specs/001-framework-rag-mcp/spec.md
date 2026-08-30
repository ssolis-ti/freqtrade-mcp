# Feature Specification: Framework RAG-por-bloque + MCP por bloque

**Feature Branch**: `001-framework-rag-mcp`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "Operar freqtrade como maquinaria controlada por múltiples
agentes LLM especializados; cada agente con RAG sobre un bloque documental; ambos mirrors
+ embeddings; un MCP server por bloque."

## User Scenarios & Testing

### User Story 1 - Consultar la documentación de un bloque con RAG (Priority: P1)

Como usuario/agente, quiero hacer preguntas en lenguaje natural sobre un bloque
documental de freqtrade (el piloto: `configuración`) y obtener respuestas basadas en su
corpus propio, para que el agente del bloque decida con su fuente de verdad y no
alucinando.

**Why this priority**: Es el corazón del framework. Si cada bloque no responde desde su
propio RAG, no hay aislación de dominio ni fuente de verdad.

**Independent Test**: Puede validarse por completo haciendo una consulta al RAG del bloque
piloto (ej. "¿qué parámetro controla el modo de futuros?") y comprobando que devuelve
fragmentos citados del corpus `configuration` (fuente y web).

**Acceptance Scenarios**:

1. **Given** el bloque `02-configuracion` indexado en los dos mirrors, **When** se envía
   una pregunta en lenguaje natural al MCP del bloque, **Then** responde con pasajes
   relevantes del corpus y sus fuentes (ruta del doc + mirror).
2. **Given** un corpus indexado, **When** la pregunta no tiene respuesta en el bloque,
   **Then** el RAG devuelve no-hits de forma explícita (no inventa ni toma de otro bloque).

---

### User Story 2 - Indexar un bloque documental desde ambos mirrors (Priority: P1)

Como operador, quiero que el framework ingiera los `.md` de `docs-freqtrade/` y
`docs-freqtrade-web/` de un bloque, los divida en chunks y los embeba, para que la
recuperación semántica funcione.

**Why this priority**: Sin índice no hay RAG. El doble mirror (fuente + web) es la
decisión base del usuario.

**Independent Test**: Ejecutar el indexador sobre el bloque piloto y verificar conteos de
chunks por mirror y un `health` del índice (embeddings computados, counts).

**Acceptance Scenarios**:

1. **Given** los archivos `.md` del bloque en ambos mirrors, **When** corre el indexador,
   **Then** produce un vector store por bloque con N chunks de la fuente y M de la web
   (N,M > 0), más un manifiesto de metadatos (origen, ruta, hash).
2. **Given** un doc ya indexado, **When** se reindexa, **Then** no duplica entradas
   (upsert por id determinista = hash de origen+path+chunk).

---

### User Story 3 - Exponer el bloque como un MCP server con herramientas de RAG (Priority: P2)

Como desarrollador, quiero que cada bloque sea un **MCP server FastMCP** independiente que
expone `consultar_docs(query, top_k)` y `health()`, para que Hermes los registre como
empleados persistentes (`mcp_<bloque>_<tool>`).

**Why this priority**: Es la segunda mitad de la decisión base; sin server por bloque no
hay agente por bloque en Hermes. P2 porque depende de P1/P2 de indexación.

**Independent Test**: Levantar el server del bloque piloto, llamar `tools/list` (FastMCP
devuelve herramientas incl. `consultar_docs` y `health`) y ejecutar una consulta real.

**Acceptance Scenarios**:

1. **Given** el MCP del bloque piloto en stdio, **When** se hace handshake `initialize`,
   **Then** responde y lista las tools `consultar_docs` y `health`.
2. **Given** el índdex embebido, **When** se llama `consultar_docs("modo futuros", 3)`,
   **Then** devuelve top-3 chunks relevantes con score y fuente.

---

### User Story 4 - Configurar embeddings desde env (portable) (Priority: P3)

Como operador en otra máquina, quiero elegir el modelo/endpoint de embeddings vía `.env`
(LiteLLM/Bifrost `:4000` por defecto) con fallback local determinista, para que el
framework funcione sin depender de infraestructura ajena.

**Why this priority**: Portabilidad es un principio de la constitution. P3 porque es
configuración, no funcionalidad central.

**Independent Test**: Sin endpoint de embeddings configurado, el índice cae a
sentence-transformers local y la consulta sigue respondiendo.

**Acceptance Scenarios**:

1. **Given** `EMBED_BASE_URL` y `EMBED_MODEL` en `.env`, **When** se indexa, **Then** el
   cliente de embeddings apunta a ese endpoint.
2. **Given** el endpoint inalcanzable, **When** se indexa, **Then** degrada a embeddings
   locales y registra un warning sin fallar.

---

### Edge Cases

- Corpus de un bloque vacío en uno de los mirrors (solo fuente, sin web): indexa el otro,
  marca origin en metadatos.
- Pregunta sin solapamiento con el corpus: respuesta explícita no-hits, no inventada.
- Reindexación: upsert por hash idempotente, sin duplicados.
- Byte-level content changes: hash de chunk invalida solo ese chunk, no todo el índice.

## Requirements

### Functional Requirements

- **FR-001**: El framework DEBE indexar los 12 bloques documentales desde ambos mirrors
  (`docs-freqtrade/` fuente develop + `docs-freqtrade-web/` stable).
- **FR-002**: Cada bloque DEBE tener un vector store aislado (sin compartir embeddings con
  otros bloques).
- **FR-003**: El RAG DEBE responder SOLO desde el corpus de su bloque; ante no-hits debe
  decir "no hay respuesta en este bloque", nunca alucinar ni cruzar bloques.
- **FR-004**: Cada bloque DEBE exponerse como un MCP server FastMCP independiente con al
  menos `consultar_docs(query, top_k)` y `health()`.
- **FR-005**: El embedding DEBE ser configurable vía env (`EMBED_BASE_URL`,
  `EMBED_MODEL`, `EMBED_API_KEY`), con LiteLLM/Bifrost `:4000` como default y
  sentence-transformers local como fallback.
- **FR-006**: La reindexación DEBE ser idempotente (upsert por hash determinista).
- **FR-007**: Los servers MCP DEBEN usar `mcp>=1.27,<2.0` e importar desde
  `mcp.server.fastmcp`.
- **FR-008**: El framework es parametrizado por bloque (config + contenido por bloque);
  escalar a los 12 = añadir corpus y servers, sin rediseñar.

### Key Entities

- **Bloque documental**: directorio de un bloque (ej. `02-configuracion`) con sus `.md`
  en ambos mirrors. Fuente de verdad del agente.
- **Chunk**: unidad de texto del corpus con id determinista (hash origen+path+índice) y
  metadatos (bloque, mirror, ruta).
- **Vector store**: índice por bloque (embeddings + chunks + metadatos).
- **MCP server por bloque**: FastMCP que expone tools de RAG sobre su vector store.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Consultas al bloque piloto devuelven pasajes relevantes y citados (fuente +
  mirror) con score de similitud en el 100% de las pruebas.
- **SC-002**: No-hits se reportan explícitamente sin alucinación (0% de respuestas
  inventadas en consultas fuera de corpus).
- **SC-003**: Reindexar el bloque piloto dos veces produce el mismo conteo de chunks
  (sin duplicados).
- **SC-004**: El MCP del bloque se registra en Hermes y responde a `tools/list` +
  una consulta real (smoke test).
- **SC-005**: Con el endpoint de embeddings caído, el índice degrada a local y la consulta
  sigue respondiendo.

## Assumptions

- El bloque piloto es `02-configuracion` (`configuration.md`, 58K fuente / 64K web).
- Python 3.11/3.14 disponible; `mcp>=1.27,<2.0`; ejecutar scripts como archivo (no
  `python -c`, bloqueado por approval gate en Windows).
- `unset PYTHONPATH` antes de correr venvs de proyecto.
- El endpoint LiteLLM/Bifrost de embeddings puede no estar disponible en todas las
  máquinas → fallback local obligatorio.
- Se prioriza el patrón validado end-to-end sobre el volumen (los 12 bloques se llenan
  por repetición del patrón, no por rediseño).
- El desarrollo SDD empieza ahora (señal del usuario); fase idea ya depurada.
- **Alcance duro del MVP**: este feature solo INDEXA y CONSULTA documentación. NO toca
  superficie live de trading, NO ejecuta dry→live, NO arriesga capital. El gate
  dry→live con OK del usuario (constitution III) es un feature aparte, fuera de scope.

**Estado**: Draft (pendiente de `/speckit.plan` y aprobación de calidad).
