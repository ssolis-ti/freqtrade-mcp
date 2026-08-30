# Contracts — Agentes LLM por bloque

**Feature**: `002-agentes-llm-bloque`

## Tool MCP `responder` (por bloque)

- **inputs**:
  - `query: str` (requerido)
  - `top_k: int` (default 3, máx 10)
- **output** (JSON string):
  ```json
  {
    "respuesta": "texto del LLM fundamentado en los chunks...",
    "citas": [
      {"chunk_id": "...", "mirror": "fuente", "path": "configuration.md",
       "heading": "Trading Mode", "score": 0.42}
    ],
    "estado": "ok" | "sin_hits" | "degradado_llm"
  }
  ```
- **`sin_hits`**: `respuesta` = mensaje de rechazo explícito ("no está en mi dominio"),
  `citas` = `[]`. NO se llama al LLM (ahorro).
- **`degradado_llm`**: `respuesta` = concatenación de los hits crudos (texto + fuente),
  `citas` = hits. Ocurre si el LLM falla tras 1 retry (timeout/429/5xx).

## Tool MCP `health` (ampliada)

```json
{
  "block": "02-configuracion",
  "ok": true,
  "chunk_count": 118,
  "mirror_counts": {"fuente": 54, "web": 64},
  "embed_model": "local-hash",
  "modelo_configurado": "deepseek-via-inference",
  "modelo_activo": "deepseek-via-inference"
}
```

- `modelo_configurado`: env `AGENT_MODEL_<BLOQUE>` o default.
- `modelo_activo`: el que realmente se usa (igual al configurado salvo fallback).

## Clase interna `rag/agent.py`

```python
class AgenteLLM:
    def __init__(self, block_id: str, embedder=None, client=None): ...
    def responder(self, query: str, top_k: int = 3) -> dict:  # respuesta + citas + estado
    def health(self) -> dict
```

- `client`: openai client (inyectable para tests/mocks). Default: gateway `:4000`.
- `model`: env `AGENT_MODEL_<BLOQUE>` → default `deepseek-via-inference`.
- `MAX_TOKENS = 2000`, `TEMPERATURE = 0.3`, retry 1.

## Config env (.env)

```bash
LLM_BASE_URL=http://localhost:4000/v1
LLM_API_KEY=<master key local, gitignored>
AGENT_MODEL_DEFAULT=deepseek-via-inference
# opcional por bloque:
# AGENT_MODEL_02_CONFIGURACION=deepseek-v4-pro
```

## Registro Hermes (junto con feature 001, T033)

```yaml
mcp_servers:
  freq_config:
    command: <proyecto>/.venv/Scripts/python.exe
    args: [<proyecto>/servers/run_agente.py, 02-configuracion]
    enabled: true
```

Nota: `run_agente.py` (nuevo) reemplaza a `run_bloque.py` para ese bloque (expone
`responder` + `consultar_docs` + `health`); o se registran ambos si se quiere el RAG puro
y el agente por separado.
