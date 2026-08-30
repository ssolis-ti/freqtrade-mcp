"""Recuperador: consulta top-k por similitud de coseno sobre el vector store.

Aislamiento: un Retriever carga SOLO el vector store de su bloque.
No-hits: si ningun score >= min_score, devuelve [] (nunca inventa).
"""
from __future__ import annotations

import json

import numpy as np

from .blocks import get_block
from .config import RAG_DATA_DIR, RAG_MIN_SCORE
from .embeddings import Embedder


class Retriever:
    """Consulta el vector store de un bloque documental."""

    def __init__(self, block_id: str, embedder: Embedder | None = None) -> None:
        self.block_id = block_id
        self.block = get_block(block_id)
        rag_dir = RAG_DATA_DIR / block_id
        self.index_path = rag_dir / "index.json"
        self.chunks_path = rag_dir / "chunks.json"
        self.vectors_path = rag_dir / "vectors.npy"
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"INDEX_MISSING: bloque {block_id} no indexado. "
                f"Ejecuta: python tools/index_blocks.py {block_id}")
        self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.chunks = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        self.vectors = np.load(self.vectors_path)
        self.embedder = embedder or Embedder()

    # --- Consulta ---

    def query(self, query: str, top_k: int = 3,
              min_score: float | None = None) -> list[dict]:
        """Top-k chunks mas relevantes del bloque para la query.

        Devuelve [] si ningun chunk supera min_score (no-hits explicito).
        """
        top_k = max(1, min(int(top_k), 10))
        threshold = RAG_MIN_SCORE if min_score is None else float(min_score)

        qv = np.asarray(self.embedder.embed_query(query), dtype=np.float32)
        if qv.ndim == 1:
            qv = qv.reshape(1, -1)
        qnorm = np.linalg.norm(qv)
        if qnorm == 0:
            return []
        qv = qv / qnorm

        vnorm = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        vnorm[vnorm == 0] = 1.0
        vn = self.vectors / vnorm

        scores = (vn @ qv.T).flatten()
        order = np.argsort(-scores)
        hits = []
        for i in order:
            if len(hits) >= top_k:
                break
            if float(scores[i]) < threshold:
                break  # orden descendente: los siguientes seran menores
            chunk = self.chunks[int(i)]
            hits.append({
                "chunk_id": chunk["id"],
                "block": chunk["block"],
                "mirror": chunk["mirror"],
                "path": chunk["path"],
                "heading": chunk["heading"],
                "heading_path": chunk["heading_path"],
                "text": chunk["text"],
                "score": round(float(scores[i]), 4),
            })
        return hits

    # --- Estado ---

    def health(self) -> dict:
        return {
            "block": self.block_id,
            "ok": True,
            "chunk_count": self.index.get("chunk_count", len(self.chunks)),
            "mirror_counts": self.index.get("mirror_counts", {}),
            "embed_model": self.index.get("embed_model"),
            "dim": self.index.get("dim"),
        }
