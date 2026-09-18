# Conector universal — estado y uso (feature 005, IMPLEMENTADO)

**Estado: OPERATIVO** (2026-09-18). Gateway MCP HTTP validado end-to-end.

Un solo endpoint HTTP expone **toda** la base de conocimiento y las herramientas de
freqtrade, para que **cualquier agente o LLM** de la LAN lo consuma.

---

## 1. Qué es

`servers/gateway_http.py` — un proceso FastMCP con transporte **Streamable HTTP**
(spec MCP 2025-03-26) que agrupa:

| Grupo | Tools | Gate |
|---|---|---|
| **Conocimiento** (`docs_*`) | `docs_listar_bloques`, `docs_health`, `docs_buscar`, `docs_preguntar`, `docs_buscar_global` | sin gate (lectura) |
| **Bot** (`bot_*`) | `bot_ping`, `bot_status`, `bot_profit`, `bot_balance`, `bot_whitelist`, `bot_blacklist`, `bot_count`, `bot_logs`, `bot_show_config` | sin gate (lectura) |
| **Grafo** (`grafo_*`) | `grafo_estadisticas`, `grafo_god_nodes`, `grafo_consultar` | sin gate (lectura) |
| **Orquestación** | `plan_mision`, `cadena_dry_run` | sin gate (planificación) |
| **Escritura** | `entrar`, `salir`, `vetar`, `detener_compras` | **NO EXPUESTAS** salvo `--permitir-escritura` |

**Total en modo solo-lectura: 19 tools.**

---

## 2. Arranque

```bash
cd /c/Users/P0zcl/Desktop/proyectos/freq && unset PYTHONPATH
.venv/Scripts/python.exe servers/gateway_http.py --transport streamable-http
# → [gateway] modo SOLO-LECTURA | http://0.0.0.0:8765/mcp
```

**Modo escritura (requiere autorización humana explícita)**:
```bash
.venv/Scripts/python.exe servers/gateway_http.py --permitir-escritura
```

Con `scripts/arrancar_gateway.sh` (Windows/bash) se levanta en background con log.

---

## 3. Cómo lo consume un cliente

### Desde Hermes (config.yaml)
```yaml
mcp_servers:
  freqtrade_universal:
    url: http://127.0.0.1:8765/mcp        # o http://<IP-LAN>:8765/mcp
    enabled: true
```
Luego `/reload-mcp`. Con eso el chat puede usar `mcp_freqtrade_universal_*`.

### Desde cualquier cliente MCP (Python)
```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://<IP-LAN>:8765/mcp") as (r, w, _):
    async with ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool("docs_preguntar",
                               {"bloque": "configuracion",
                                "query": "how to enable futures trading"})
        print(res.content[0].text)
```

### Prueba rápida incluida
```bash
.venv/Scripts/python.exe tools/cliente_gateway.py
# o contra otro equipo: tools/cliente_gateway.py http://192.168.x.x:8765/mcp
```

---

## 4. Ejemplos de uso (preguntas reales)

```python
# Conocimiento: preguntar a un bloque (respuesta LLM + citas)
docs_preguntar(bloque="riesgo_futuros", query="como configuro el stoploss trailing")

# Conocimiento: recuperar chunks crudos (sin LLM, rápido)
docs_buscar(bloque="configuracion", query="dry run", top_k=5)

# Conocimiento: no sé en qué bloque está
docs_buscar_global(query="hyperopt loss function", top_k_por_bloque=1)

# Grafo: entender el código
grafo_god_nodes(top_n=10)          # abstracciones centrales
grafo_consultar("como se conecta el retriever con el agente")

# Operación (lectura)
bot_show_config()                  # verificar dry_run antes de operar
bot_status()                       # trades abiertos
bot_profit()                       # P/L

# Orquestación
plan_mision("cazar alts momentum 7d en futuros")
```

---

## 5. Verificado (2026-09-18)

| Prueba | Resultado |
|---|---|
| Servidor HTTP en LAN | ✅ escucha en `0.0.0.0:8765` |
| Handshake MCP | ✅ `freqtrade-universal` v1.29.1, protocolo 2025-03-26 |
| Tools expuestas | ✅ 19 (docs 5 + bot 9 + grafo 2 + plan/gadena 2) |
| **Seguridad solo-lectura** | ✅ **ninguna tool de escritura expuesta** |
| RAG por bloque | ✅ 12 bloques; `configuracion` → 118 chunks, Gemini semántico |
| Grafo del código | ✅ 468 nodos, 939 edges, 19 comunidades |
| Tests | ✅ 8/8 (`tests/test_gateway.py`) |

---

## 6. Seguridad

- **Modo solo-lectura por defecto**: las tools de escritura no se registran (no es que
  estén bloqueadas — no existen en el listado). Verificado por test automatizado.
- **Escritura solo con flag explícito**: `--permitir-escritura` (autorización humana al
  arrancar el proceso).
- **Regla dura de la constitution (III)**: nunca arriesgar capital sin OK explícito.
- **Pendiente (endurecimiento)**: API key Bearer por HTTP. Hoy el gateway escucha en LAN
  sin auth — aceptable en red doméstica confiable, **no exponer a internet** sin auth+TLS.
- Dry-run obligatorio: `bot_show_config()` para verificar antes de cualquier operación.

---

## 7. Pendientes

1. **API key** (Bearer) para el transporte HTTP — antes de exponer fuera de la LAN.
2. **Registro en Hermes** por `url` (requiere OK del usuario para editar config.yaml).
3. **Reindexar bloques 03-11 con Gemini** cuando haya cuota (3 bloques ya semánticos).
4. **freqtrade real**: sin Docker/gateway encendido, las tools `bot_*` no tienen contra
   qué operar; los tests usan mocks.
