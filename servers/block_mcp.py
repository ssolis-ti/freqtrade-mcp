"""Server MCP generico por bloque documental.

Expone dos tools sobre el vector store de UN bloque:
  - consultar_docs(query, top_k): recuperacion top-k con score y fuente
  - health(): estado del indice

Aislamiento: cada server se construye para un solo bloque (Retriever propio).
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from rag.embeddings import Embedder
from rag.retriever import Retriever


def build_mcp(block_id: str, embedder: Embedder | None = None) -> FastMCP:
    """Construye el FastMCP del bloque (no lo corre; run_bloque.py lo hace)."""
    retriever = Retriever(block_id, embedder=embedder)

    mcp = FastMCP(
        f"freq-{block_id}",
        instructions=(
            f"Agente RAG del bloque documental '{block_id}' de freqtrade. "
            "Responde SOLO usando consultar_docs sobre este bloque; nunca inventes "
            "y nunca tomes informacion de otros bloques."
        ),
    )

    @mcp.tool()
    def consultar_docs(query: str, top_k: int = 3) -> str:
        """Consulta la documentacion del bloque. Devuelve JSON list de hits (texto, fuente, score)."""
        try:
            hits = retriever.query(query, top_k=top_k)
            return json.dumps(hits, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"EMBED_FAIL: {e}"}, ensure_ascii=False)

    @mcp.tool()
    def health() -> str:
        """Estado del indice del bloque (chunk_count, mirror_counts, modelo)."""
        return json.dumps(retriever.health(), ensure_ascii=False)

    return mcp
