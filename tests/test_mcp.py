"""Tests del server MCP: construccion, tools listadas, consulta y health reales."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DATA_DIR  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.indexer import index_block  # noqa: E402
from rag.blocks import get_block  # noqa: E402


def _ensure_indexed():
    e = Embedder(base_url="http://127.0.0.1:9", model="test-embed", gemini_key="")
    if not (RAG_DATA_DIR / "02-configuracion" / "index.json").exists():
        index_block(get_block("02-configuracion"), force=True, embedder=e)
    return e


def test_server_builds_and_lists_tools():
    from servers.block_mcp import build_mcp
    mcp = build_mcp("02-configuracion")
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "consultar_docs" in names
    assert "health" in names


def test_consultar_docs_tool():
    from servers.block_mcp import build_mcp
    e = _ensure_indexed()
    mcp = build_mcp("02-configuracion", embedder=e)
    result = asyncio.run(mcp.call_tool("consultar_docs", {"query": "stoploss configuration", "top_k": 2}))
    out = result[0][0].text
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["block"] == "02-configuracion"


def test_consultar_docs_no_hits():
    from servers.block_mcp import build_mcp
    e = _ensure_indexed()
    mcp = build_mcp("02-configuracion", embedder=e)
    result = asyncio.run(mcp.call_tool("consultar_docs", {"query": "zzzqqqxxx no such term", "top_k": 3}))
    out = result[0][0].text
    assert json.loads(out) == []


def test_health_tool():
    from servers.block_mcp import build_mcp
    e = _ensure_indexed()
    mcp = build_mcp("02-configuracion", embedder=e)
    result = asyncio.run(mcp.call_tool("health", {}))
    h = json.loads(result[0][0].text)
    assert h["ok"] is True
    assert h["chunk_count"] > 0
