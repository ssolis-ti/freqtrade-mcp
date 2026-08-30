"""Indexador: convierte los mirrors de un bloque en un vector store ligero.

Por bloque escribe en data/rag/<id>/:
  - chunks.json: lista de chunks (metadatos + texto)
  - vectors.npy: ndarray float32 [n_chunks, dim] (fila i <-> chunk i)
  - index.json:  manifiesto (embed_model, conteos por mirror, content_hash, ...)

Idempotente: si el content_hash del corpus no cambio y force=False, no reindexa.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from .blocks import Block
from .chunking import Chunk, chunk_markdown
from .config import RAG_DATA_DIR, RAG_MIN_SCORE
from .embeddings import Embedder


def _content_hash(chunks: list[Chunk]) -> str:
    h = hashlib.sha1()
    for c in chunks:
        h.update(c.id.encode("utf-8"))
    return h.hexdigest()


def _read_mirror(block: Block, mirror: str) -> tuple[list[Chunk], list[Path]]:
    """Chunking de todos los .md de un mirror (si el directorio existe)."""
    chunks: list[Chunk] = []
    files = block.md_files(mirror)
    for p in files:
        rel = p.relative_to(block.docs_dir if mirror == "fuente" else block.web_dir)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = p.read_text(encoding="utf-8", errors="replace")
        chunks.extend(chunk_markdown(text, str(rel).replace("\\", "/"), mirror, block.id))
    return chunks, files


def index_block(block: Block, force: bool = False,
                embedder: Embedder | None = None) -> dict:
    """Indexa un bloque (ambos mirrors) y escribe su vector store.

    Args:
        block: bloque documental
        force: si True, reindexa aunque el corpus no haya cambiado
        embedder: instancia reutilizable (default: nueva)

    Returns:
        El manifiesto index.json del bloque.
    """
    rag_dir = RAG_DATA_DIR / block.id
    rag_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[Chunk] = []
    for mirror in ("fuente", "web"):
        c, _ = _read_mirror(block, mirror)
        chunks.extend(c)

    if not chunks:
        raise RuntimeError(f"Bloque {block.id}: sin archivos .md en ningun mirror")

    content_hash = _content_hash(chunks)
    index_path = rag_dir / "index.json"
    if not force and index_path.exists():
        prev = json.loads(index_path.read_text(encoding="utf-8"))
        if prev.get("content_hash") == content_hash:
            return prev  # corpus intacto: no reindexar

    if embedder is None:
        embedder = Embedder()

    texts = [c.text for c in chunks]
    vectors = np.asarray(embedder.embed_texts(texts), dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)

    mirror_counts = {"fuente": 0, "web": 0}
    for c in chunks:
        mirror_counts[c.mirror] = mirror_counts.get(c.mirror, 0) + 1

    manifest = {
        "block": block.id,
        "embed_model": embedder.model_name(),
        "embed_base_url": embedder.base_url if not embedder.is_local() else None,
        "embed_gateway_error": embedder.gateway_error(),
        "dim": int(vectors.shape[1]),
        "chunk_count": len(chunks),
        "mirror_counts": mirror_counts,
        "content_hash": content_hash,
        "min_score": RAG_MIN_SCORE,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    (rag_dir / "chunks.json").write_text(
        json.dumps([c.to_dict() for c in chunks], ensure_ascii=False, indent=1),
        encoding="utf-8")
    np.save(rag_dir / "vectors.npy", vectors)
    (rag_dir / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
