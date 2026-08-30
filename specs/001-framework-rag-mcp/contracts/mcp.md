# Contracts — Framework RAG-por-bloque

**Feature**: `001-framework-rag-mcp`

Interfaz pública de los MCP servers por bloque y de los módulos internos. El contrato MCP
es el superficie universal; el resto son contratos internos de Python.

## Contrato MCP (por bloque)

Todos los servers (`run_bloque.py <id>`) exponen el mismo surface:

### Tool `consultar_docs`

- **inputs**:
  - `query: str` (requerido)
  - `top_k: int` (default 3, máx 10)
- **output**: `JSON list` de `hit`:
  ```json
  [{"chunk_id": "...", "block": "02-configuracion", "mirror": "web",
    "path": "configuration.md", "heading": "Trading Mode",
    "text": "...", "score": 0.87}]
  ```
- **no-hits**: devuelve `[]` si ningún score ≥ `min_score` (no alucina).

### Tool `health`

- **inputs**: ninguno
- **output**:
  ```json
  {"block": "02-configuracion", "ok": true, "chunk_count": 57,
   "mirror_counts": {"fuente": 31, "web": 26},
   "embed_model": "text-embedding-3-small", "dim": 1536}
  ```

### Tipos de error

- `EMBED_FAIL` — no se pudo computar embedding de la query ni por gateway ni local.
- `INDEX_MISSING` — el bloque no está indexado (`health.ok=false`).

## Contrato interno (`rag/`)

### `embeddings.Embedder`

```python
class Embedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]  # lotes
    def embed_query(self, query: str) -> list[float]
    def model_name(self) -> str          # ej. "text-embedding-3-small" | "local-hash"
    def dim(self) -> int
```

Reglas: `embed_texts` con batching (≤16 por request) y timeout corto; si el gateway no
responde o da 401, `model_name()=="local-hash"` y vectores generados localmente.

### `chunking.chunk_markdown(text, path, mirror) -> list[chunk]`

Divide por cabeceras `##`/`###`, construye `heading_path`, asigna `id` hash, calcula
`char_len`.

### `indexer.index_block(block, force=False) -> index.json`

Lee ambos mirrors del bloque, chunking + embeddings, guarda `chunks.json`/`vectors.npy`/
`index.json`. `force=True` reindexa entero; si no, reusa chunks con hash inalterado.

### `retriever.Retriever(block)`

```python
def query(self, q: str, top_k: int = 3, min_score: float | None) -> list[hit]
```

Cos por coseno sobre `vectors.npy`; filtra por `min_score`.

## Registro Hermes

Un entry por bloque en `config.yaml` → `mcp_servers.<id>`:

```yaml
mcp_servers:
  freq_config:
    command: <proj>/.venv/Scripts/python.exe
    args:
      - <proj>/servers/run_bloque.py
      - 02-configuracion
    enabled: true
```

(Paths relativos al proyecto; sin hardcodear usuarios.)
