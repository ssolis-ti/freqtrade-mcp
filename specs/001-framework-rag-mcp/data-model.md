# Data Model — Framework RAG-por-bloque

**Feature**: `001-framework-rag-mcp` | **Plan**: `plan.md`

## Entidades

### 1. Bloque documental (`block`)

Identidad canónica de un dominio documental freqtrade.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | `01-instalacion`, `02-configuracion`, … `11-operativo` |
| `name` | string | Nombre legible (p.ej. `configuracion`) |
| `docs_dir_fuente` | path | `docs-freqtrade/<id>/` (mirror fuente develop) |
| `docs_dir_web` | path | `docs-freqtrade-web/<id>/` (mirror web stable) |
| `rag_dir` | path | `data/rag/<id>/` (vector store + manifiesto) |

Persistido en `rag/blocks.py` (catálogo estático de 12 bloques).

### 2. Chunk (`chunk`)

Unidad mínima de texto del corpus. División **jerárquica por cabeceras** `##`/`###` y, si
una sección supera `MAX_CHARS` (~2000), **subdivisión recursiva en párrafos con solape**
(~200 chars), heredando el `heading_path`. Esto es obligatorio porque `configuration.md`
tiene una sección de 24.6K chars.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | string | `sha1(mirror \| path \| chunk_index)` — determinista, clave de upsert |
| `block` | string | Bloque al que pertenece |
| `mirror` | enum `fuente`\|`web` | Origen del doc |
| `path` | string | Ruta relativa del `.md` dentro del mirror |
| `heading` | string | Cabecera `##`/`###` (contexto del chunk) — puede ser vacío |
| `heading_path` | string | Cadena de cabeceras padre (`A / B / C`) |
| `text` | string | Contenido del chunk (sin la cabecera) |
| `char_len` | int | `len(text)` |

### 3. Embedding vector

`numpy.ndarray` float32, fila i ↔ chunk i del mismo bloque.

- **dim**: definida por el modelo (`text-embedding-3-small` → 1536; fallback local → fija).
- Orden: índice de `chunks.json`.

### 4. Manifiesto de índice (`data/rag/<id>/index.json`)

| Campo | Tipo | Descripción |
|---|---|---|
| `block` | string | Bloque |
| `embed_model` | string | Modelo usado (p.ej. `text-embedding-3-small`, `local-hash`) |
| `embed_base_url` | string | Endpoint (para reproducibilidad) |
| `dim` | int | Dimensión de vectores |
| `chunk_count` | int | Total de chunks |
| `mirror_counts` | `{fuente: int, web: int}` | Conteo por mirror |
| `built_at` | timestamp | Fecha de construcción |
| `content_hash` | string | Hash agregado del corpus (para detectar cambios) |
| `min_score` | float | Umbral de recuperación (config globional default) |

### 5. Resultado de consulta (`hit`)

| Campo | Tipo | Descripción |
|---|---|---|
| `chunk_id` | string | |
| `block`, `mirror`, `path`, `heading` | | copiado del chunk |
| `text` | string | |
| `score` | float | Similitud de coseno |

## Persistencia (`data/`, gitignored)

```text
data/rag/<block>/
├── chunks.json       # lista de chunk (metadatos + texto)
├── vectors.npy       # 2D ndarray float32 [n_chunks, dim]
└── index.json        # manifiesto del índice
```

`.gitignore` debe excluir `data/` (regenerable por indexación). Manifiestos y catálogo
de bloques viven en código (`rag/blocks.py`).

## Reglas

- **Idempotencia**: el `chunk.id` es determinista por contenido+origen+posición; reindexar
  reemplaza solo chunks modificados.
- **Aislamiento**: nunca se mezclan vectores de bloques distintos (no compartir `.npy`).
- **Portabilidad**: cero rutas absolutas en datos; todo relativo a la raíz del proyecto.
