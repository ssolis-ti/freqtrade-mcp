"""Tests del gateway MCP universal (mocks; sin freqtrade ni LLM reales)."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from servers.gateway_http import build_gateway


def _tool_names(mcp) -> set:
    res = asyncio.run(mcp.list_tools())
    items = res.tools if hasattr(res, "tools") else res
    return {t.name for t in items}


def test_modo_solo_lectura_no_expone_escritura():
    """CRITICO: sin --permitir-escritura, las tools de escritura NO existen."""
    mcp = build_gateway(permitir_escritura=False)
    names = _tool_names(mcp)
    for peligrosa in ["entrar", "salir", "vetar", "detener_compras"]:
        assert peligrosa not in names, f"{peligrosa} NO debe existir en solo-lectura"
    # Pero las de lectura y conocimiento si
    for esperada in ["docs_listar_bloques", "docs_preguntar", "docs_buscar",
                     "bot_status", "plan_mision", "grafo_god_nodes"]:
        assert esperada in names, f"falta {esperada}"


def test_modo_escritura_expone_gate():
    mcp = build_gateway(permitir_escritura=True)
    names = _tool_names(mcp)
    for esperada in ["entrar", "salir", "vetar", "detener_compras"]:
        assert esperada in names


def test_docs_listar_bloques():
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("docs_listar_bloques", {}))
    bloques = json.loads(r[0][0].text)
    assert len(bloques) == 12
    ids = {b["id"] for b in bloques}
    assert "02-configuracion" in ids and "06-freqai" in ids


def test_docs_buscar_resuelve_alias():
    """Acepta tanto id ('02-configuracion') como alias ('configuracion')."""
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("docs_buscar",
                                  {"bloque": "configuracion",
                                   "query": "dry run", "top_k": 2}))
    hits = json.loads(r[0][0].text)
    assert isinstance(hits, list)


def test_docs_buscar_global():
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("docs_buscar_global",
                                  {"query": "stoploss", "top_k_por_bloque": 1}))
    data = json.loads(r[0][0].text)
    assert len(data) == 12  # los 12 bloques consultados


def test_docs_health():
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("docs_health", {"bloque": "02-configuracion"}))
    h = json.loads(r[0][0].text)
    assert h["ok"] is True
    assert h["chunk_count"] > 0


def test_grafo_estadisticas():
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("grafo_estadisticas", {}))
    data = json.loads(r[0][0].text)
    # El grafo del codigo fue generado; si no, habria 'aviso'
    assert "nodos" in data or "aviso" in data


def test_grafo_god_nodes():
    mcp = build_gateway()
    r = asyncio.run(mcp.call_tool("grafo_god_nodes", {"top_n": 5}))
    data = json.loads(r[0][0].text)
    if isinstance(data, list):
        assert len(data) <= 5
        assert "nodo" in data[0] and "edges" in data[0]
