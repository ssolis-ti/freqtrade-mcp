# Quickstart — Framework RAG-por-bloque

**Feature**: `001-framework-rag-mcp` | **Plan**: `plan.md`

Guía rápida para correr el framework end-to-end sobre el bloque piloto `02-configuracion`.

## 1. Requisitos

- Python 3.11+ con `unset PYTHONPATH`
- Dependencias: `pip install "mcp>=1.27,<2.0" openai numpy` (+ `markdownify beautifulsoup4`
  ya presentes)
- Corpus (ya en repo, no requiere descarga): `docs-freqtrade/02-configuracion/` y
  `docs-freqtrade-web/02-configuracion/`

## 2. Configurar embeddings (opcional)

```bash
# .env (no comprometer)
EMBED_BASE_URL=http://localhost:4000
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=tu-key
```

Sin `.env`, el framework usa embeddings locales deterministas (`local-hash`).

## 3. Indexar el bloque piloto

```bash
python tools/index_blocks.py 02-configuracion
# → escribe data/rag/02-configuracion/{chunks.json,vectors.npy,index.json}
```

## 4. Probar consulta sin MCP

```bash
python tools/query_block.py 02-configuracion "¿cómo activo trading de futuros?"
# → top-k chunks con score y fuente
```

## 5. Levantar el MCP server del bloque

```bash
python servers/run_bloque.py 02-configuracion
# → FastMCP stdio; handshake initialize + tools/list → consultar_docs, health
```

## 6. Registrar en Hermes

Añadir el entry en `config.yaml` bajo `mcp_servers.freq_config` (ver `contracts/mcp.md`),
luego `/reload-mcp`. El agente del bloque aparece como empleado persistente.

## Escalado a los 12 bloques

Repetir indexación y levantar un server por bloque (`python servers/run_bloque.py <id>`).
Sin rediseño: el patrón es idéntico por bloque.

Verificar de nuevo: `python tools/probe_deps.py`.
