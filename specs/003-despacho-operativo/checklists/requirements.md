# Requirements Checklist — Despacho operativo

Feature: `003-despacho-operativo`

## Functional Requirements

- [ ] **FR-001** — Agente control/riesgo invoca las 19 tools del wrapper REST contra freqtrade
- [ ] **FR-002** — Tools de ejecución exigen OK explícito del usuario; sin OK se rechazan
- [ ] **FR-003** — Manager descompone misión en pasos por dominio y produce plan ordenado
- [ ] **FR-004** — Manager decide dry-run SOLO si backtest + riesgo dan OK; si fallan, reporta bloqueo
- [ ] **FR-005** — Cadena datos→estrategia→backtest→hyperopt→riesgo corre en dry-run (cero riesgo)
- [ ] **FR-006** — Credenciales freqtrade desde `.env` (nunca hardcodeadas)
- [ ] **FR-007** — Sin freqtrade disponible: error claro, agente degrada sin fallar
- [ ] **FR-008** — Paso dry-run → live FUERA de alcance (feature aparte + OK usuario)

## Success Criteria

- [ ] **SC-001** — Con freqtrade dry-run: lectura (status/profit) y escritura (forceenter con OK) 100% éxito
- [ ] **SC-002** — Sin OK del usuario: 0% de tools de ejecución se ejecutan
- [ ] **SC-003** — Manager produce plan con ≥1 paso por dominio implicado
- [ ] **SC-004** — Cadena completa corre en dry-run y produce estrategia validada (PF/drawdown umbrales)
- [ ] **SC-005** — Sin freqtrade: error claro, framework no crashea (tests con mock)

## Alcance (decidido)

- Integrar wrapper REST existente (19 tools) sin rediseño; extender solo si falta un endpoint
- Manager: deepseek-via-inference (gateway :4000)
- Dry-run obligatorio; live fuera de alcance (regla dura)
- freqtrade en Docker local para pruebas (requiere OK usuario)
