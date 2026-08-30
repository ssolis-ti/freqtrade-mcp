# Research — Fase 0: Agentes LLM por bloque

**Feature**: `002-agentes-llm-bloque` | **Fecha**: 2026-08-30

## Hallazgos verificados en vivo

### Gateway LLM `:4000` (LiteLLM) — OPERATIVO

- Master key local en `Desktop/deploys-docker/litellm-deploy/internal/litellm.env`
  (LITELLM_MASTER_KEY). El agente la lee desde `.env` del proyecto (gitignored).
- **21 modelos** listados. Default elegido: `deepseek-via-inference` (el mismo que usa
  Hermes; probado: responde).
- **Pitfall confirmado**: con `max_tokens=10` el modelo devuelve `content: ''` aunque
  `completion_tokens=10` (el razonamiento consume el presupuesto). Con `max_tokens=200`
  responde `content: 'funcionando'`, `finish_reason: stop`. → **el agente debe usar
  `max_tokens >= 2000`** (skill spec-kit: deepseek-v4-flash devuelve content vacío con
  finish_reason:length si max_tokens es bajo).
- **Campo extra**: `reasoning_content` (DeepSeek razona). El agente debe extraer SOLO
  `message.content` para la respuesta final.

### Embeddings del gateway — ROTOS (no bloquea el feature)

- `nvidia-embed` (alias de `nv-embedqa-mistral-7b-v2` vía NIM): **404** — función no
  existe en la cuenta NIM. Nombre directo: **429** — sin deployments.
- `inference.net` (INFERENCE_API_KEY): **403** al listar modelos (no se puede confirmar
  embeddings sin gastar crédito; no gastamos sin OK).
- → Los agentes usan el RAG existente con `local-hash` (feature 001). Embeddings
  semánticos locales (sentence-transformers) = feature 003 (requiere OK para instalar
  ~100MB). No bloquea: los agentes funcionan con el RAG actual.

## Decisiones técnicas

### 1. Cliente LLM: openai SDK contra el gateway

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:4000/v1", api_key=LLM_API_KEY,
                timeout=(5.0, 90.0))
resp = client.chat.completions.create(
    model=model, messages=[...], max_tokens=2000, temperature=0.3)
text = resp.choices[0].message.content  # SOLO content, ignorar reasoning_content
```

- Retry: 1 reintento ante timeout/429/5xx.
- Llamada al LLM SOLO si hay hits (ahorra crédito; no-hits → rechazo sin gastar).

### 2. Prompt del agente (construido desde los hits)

```
Eres el agente del bloque documental {block} de freqtrade.
Responde SOLO con la informacion de los fragmentos siguientes, en el idioma de la pregunta.
Si la informacion no esta en los fragmentos, dilo explicitamente.
Cita al final cada fragmento usado como: [fuente: {mirror}/{path} — {heading}]

FRAGMENTOS:
1) (score 0.42) [fuente] configuration.md — Trading Mode
   <texto...>
...
PREGUNTA: ...
```

### 3. Formato de respuesta (MCP)

```json
{
  "respuesta": "texto del LLM...",
  "citas": [
    {"chunk_id": "...", "mirror": "fuente", "path": "configuration.md",
     "heading": "Trading Mode", "score": 0.42}
  ],
  "estado": "ok" | "sin_hits" | "degradado_llm"
}
```

- `sin_hits`: rechazo explícito, sin llamar al LLM.
- `degradado_llm`: LLM falló → devuelve los hits crudos (nunca inventa).

### 4. Modelo por bloque

`AGENT_MODEL_<BLOQUE_ID_UPPER_SIN_GUION>` en env (ej. `AGENT_MODEL_02_CONFIGURACION`),
default `deepseek-via-inference`. Si el modelo no existe en el gateway → fallback default.

## Riesgos / mitigaciones

| Riesgo | Mitigación |
|---|---|
| max_tokens bajo → content vacío | max_tokens >= 2000 fijo |
| reasoning_content confundido con respuesta | extraer solo `message.content` |
| LLM caído/429 | retry 1 + degradación a hits crudos |
| Gasto de crédito en no-hits | no llamar al LLM sin hits |
| Embeddings débiles (local-hash) | feature 003 (semántico local) — medido por benchmark |

## Resultado

El feature es implementable con lo existente: openai SDK (ya instalado) + gateway
operativo + RAG del feature 001. Sin dependencias nuevas.
