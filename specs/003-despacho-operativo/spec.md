# Feature Specification: Despacho operativo (agentes con manos + Manager + dry-run)

**Feature Branch**: `003-despacho-operativo`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "Quedo lista y operativa la base fundamental ahora una llm
lo puede tomar para operar freqtrade de forma optima" + decision de arquitectura:
unir el cerebro (RAG + agentes, features 001-002) con las manos (wrapper REST
`prototype/freqtrade-mcp`, 19 tools) para que un LLM pueda OPERAR freqtrade en dry-run
con un Manager orquestador.

## Contexto (verificado)

- Features 001-002 completos: 12 bloques indexados, RAG por bloque, agentes LLM con
  citas, MCP stdio validado, 26/26 tests, benchmark (recall@1=0.30 local-hash).
- Wrapper REST `prototype/freqtrade-mcp/mcp_server.py` construido y validado (19 tools,
  auth JWT, patrón direct-httpx) pero **aislado**: ningún agente lo invoca.
- No hay instancia de freqtrade corriendo hoy (falta levantar en Docker dry-run).
- Regla dura (constitution III): dry-run → live SOLO con OK explícito del usuario.

## User Scenarios & Testing

### User Story 1 - El agente del bloque control/riesgo ejecuta sobre freqtrade (Priority: P1)

Como agente del bloque `08-control` (rest-api) o `07-riesgo-futuros` (stoploss/leverage),
quiero invocar las tools del wrapper REST (forceenter, forceexit, blacklist_add,
lock_pair, stopbuy, status, profit, balance...) para ejercer mi dominio sobre una
instancia real de freqtrade en dry-run.

**Why this priority**: Es el puente cerebro→manos; sin él el LLM solo sabe, no hace.

**Independent Test**: Con freqtrade dry-run corriendo, el agente del bloque control
llama `status()` y `profit()` y devuelve datos reales; con permiso del usuario, una
`forceenter` en un par de prueba entra y aparece en `status()`.

**Acceptance Scenarios**:

1. **Given** freqtrade dry-run corriendo (Docker, REST en 127.0.0.1:8080) y credenciales
   en `.env`, **When** el agente del bloque control llama `status`, **Then** devuelve los
   trades actuales (o vacío) sin error.
2. **Given** el agente decide entrar en un par, **When** el usuario da OK explícito,
   **Then** `forceenter` ejecuta y el trade aparece en `status()` (dry-run, cero riesgo).
3. **Given** un par señalado como riesgo (delist/shutdown), **When** el agente de riesgo
   decide vetarlo, **Then** `blacklist_add` lo añade y `whitelist()` lo refleja.

---

### User Story 2 - Manager orquestador delega y controla el flujo (Priority: P1)

Como Manager, quiero recibir una misión ("cazar alts momentum 7d en futuros"), delegar a
los agentes de los dominios correctos (datos → estrategia → backtest → hyperopt →
riesgo), recoger sus resultados y decidir si el plan pasa a dry-run — para orquestar sin
que ningún dominio salte por encima de otro.

**Why this priority**: Es la capa de coordinación; sin Manager no hay flujo completo.

**Independent Test**: El Manager procesa una misión de ejemplo y produce un plan con
pasos asignados a dominios (cada paso = tool de un agente), que se puede ejecutar en
dry-run.

**Acceptance Scenarios**:

1. **Given** una misión del usuario, **When** el Manager la descompone, **Then** produce
   un plan ordenado de pasos, cada uno asignado al agente cuyo bloque documental lo
   habilita.
2. **Given** el plan completo, **When** todos los dominios de validación (backtest,
   riesgo) dan OK, **Then** el Manager propone pasar a dry-run.
3. **Given** un dominio falla (p.ej. backtest con drawdown excesivo), **When** el Manager
   recibe el resultado, **Then** NO propone dry-run y reporta el bloqueo al usuario.

---

### User Story 3 - Cadena de validación completa en dry-run (Priority: P2)

Como operador, quiero que el flujo completo (datos → estrategia → backtest → hyperopt →
riesgo) se ejecute en dry-run con una instancia real de freqtrade, para validar que el
framework produce estrategias operativas sin arriesgar capital.

**Why this priority**: Valida el valor real del framework (no solo consulta, produce).

**Independent Test**: El flujo produce una estrategia validada (profit factor y drawdown
dentro de umbrales) usando datos descargados, y la deja lista para dry-run.

**Acceptance Scenarios**:

1. **Given** datos históricos descargados de candidatos, **When** el agente de estrategia
   escribe la estrategia de momentum, **Then** el agente de backtesting la valida contra
   datos reales (reporta PF y drawdown).
2. **Given** el backtest con métricas dentro de umbral, **When** el agente de hyperopt
   optimiza ROI/stoploss/trailing, **Then** produce la config final.
3. **Given** la config final, **When** el agente de riesgo la revisa (leverage, stoploss),
   **Then** aprueba o rechaza con justificación.

---

### User Story 4 - Registro en Hermes y benchmark del despacho (Priority: P3)

Como operador, quiero registrar el agente del despacho en Hermes (MCP) y medir su
calidad, para usarlo desde el chat y comparar configuraciones.

**Why this priority**: Cierre operativo; depende de US1-US3.

**Independent Test**: El agente registrado responde `mcp_freq_*` tools en Hermes tras
`/reload-mcp`.

**Acceptance Scenarios**:

1. **Given** el entry en config.yaml, **When** `/reload-mcp`, **Then** las tools del
   despacho aparecen disponibles en el chat.
2. **Given** el benchmark del despacho, **When** corre, **Then** reporta tiempos y tasa
   de éxito de las llamadas REST.

---

### Edge Cases

- freqtrade no corriendo: las tools de lectura devuelven error claro (conexión), el
  agente reporta "bot no disponible" sin fallar.
- Token JWT expirado: relogin automático (ya en el wrapper, `_call` 401→_auth).
- forceenter sin OK del usuario: el agente la rechaza (regla dura).
- Pairs delistados/shutdown: el agente de riesgo los veta antes de operar.
- Rate limit del exchange: las llamadas fallan con error del bot; el agente reporta y
  reintenta con backoff.
- LLM caído en el Manager: degrada a plan basado solo en reglas/heurística.

## Requirements

### Functional Requirements

- **FR-001**: El agente del bloque control/riesgo DEBE poder invocar las 19 tools del
  wrapper REST (`prototype/freqtrade-mcp`) contra una instancia de freqtrade.
- **FR-002**: Las tools de ejecución (`forceenter`, `forceexit`, `blacklist_add`,
  `lock_pair`, `stopbuy`) DEBEN exigir OK explícito del usuario (constitution III);
  sin OK, el agente las rechaza.
- **FR-003**: El Manager DEBE descomponer una misión en pasos asignados a dominios
  documentales y producir un plan ordenado.
- **FR-004**: El Manager DEBE recoger resultados de los dominios y decidir dry-run SOLO
  si backtest + riesgo dan OK; si fallan, reporta el bloqueo.
- **FR-005**: La cadena datos → estrategia → backtest → hyperopt → riesgo DEBE ejecutarse
  en dry-run (cero riesgo) contra freqtrade real (Docker).
- **FR-006**: Las credenciales de freqtrade (FREQTRADE_URL/USER/PASS) DEBEN venir de
  `.env` (nunca hardcodeadas).
- **FR-007**: Si freqtrade no está disponible, las tools DEBEN reportar error claro y
  el agente degradar sin fallar.
- **FR-008**: El paso dry-run → live queda FUERA de alcance (requiere feature aparte y
  OK explícito del usuario).

### Key Entities

- **Despacho**: conjunto de agentes con manos (control, riesgo) + Manager.
- **Plan**: lista ordenada de pasos {dominio, tool, params, estado}.
- **OK del usuario**: autorización explícita para tools de ejecución (regla dura).
- **Instancia freqtrade**: bot corriendo en Docker con REST API habilitada (dry-run).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Con freqtrade dry-run, el agente control ejecuta lectura (status/profit) y
  escritura (forceenter con OK) con 100% de éxito en pruebas.
- **SC-002**: Sin OK del usuario, 0% de tools de ejecución se ejecutan (rechazo total).
- **SC-003**: El Manager produce un plan con ≥1 paso por dominio implicado en la misión.
- **SC-004**: La cadena completa (datos→estrategia→backtest→hyperopt→riesgo) corre en
  dry-run y produce una estrategia validada con PF ≥ umbral y drawdown ≤ umbral.
- **SC-005**: Sin freqtrade disponible, las tools reportan error claro y el framework no
  crashea (tests con mock).

## Assumptions

- Se levanta freqtrade en Docker dry-run para las pruebas (requiere OK del usuario y
  Docker local; no gasta crédito).
- El wrapper REST existente se integra tal cual (patrón direct-httpx), sin rediseño;
  si hace falta, se extiende (p.ej. nuevos endpoints) sin romper las 19 tools.
- El Manager usa el gateway `:4000` (deepseek-via-inference default).
- El flujo completo puede requerir datos de mercado: se usa `freqtrade download-data`
  (gratis, datos históricos públicos).
- Las herramientas de backtest/hyperopt corren como CLI (subprocess) — patrón "Taller";
  las de operación como REST — patrón "Despacho".
- Registro en Hermes al final (T033 + despacho).

**Estado**: Draft (pendiente de plan y aprobación).
