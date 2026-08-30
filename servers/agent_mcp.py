"""MCP server del agente LLM por bloque.

Expone sobre UN bloque:
  - responder(query, top_k): respuesta LLM fundamentada en el RAG del bloque + citas
  - consultar_docs(query, top_k): recuperacion pura (heredada del RAG)
  - health(): estado del indice + modelo LLM activo
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from rag.agent import AgenteLLM
from rag.embeddings import Embedder
from rag.retriever import Retriever


def build_agent_mcp(block_id: str, embedder: Embedder | None = None,
                    client=None) -> FastMCP:
    """Construye el FastMCP del agente del bloque (no lo corre)."""
    agente = AgenteLLM(block_id, embedder=embedder, client=client)
    retriever = agente.retriever

    mcp = FastMCP(
        f"freq-agente-{block_id}",
        instructions=(
            f"Agente del bloque documental '{block_id}' de freqtrade. "
            "Responde SOLO con responder() sobre este bloque; nunca inventes ni "
            "tomes informacion de otros bloques."
        ),
    )

    @mcp.tool()
    def responder(query: str, top_k: int = 3) -> str:
        """Responde una pregunta del dominio del bloque con fundamento en su documentacion y citas."""
        try:
            return json.dumps(agente.responder(query, top_k=top_k), ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"AGENT_FAIL: {e}", "estado": "error"}, ensure_ascii=False)

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
        """Estado del agente: indice del bloque + modelo LLM configurado/activo."""
        return json.dumps(agente.health(), ensure_ascii=False)

    return mcp
