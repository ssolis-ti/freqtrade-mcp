"""Prueba las tools MCP de graphify contra el grafo del CODIGO del framework."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

GRAPH = sys.argv[1] if len(sys.argv) > 1 else str(
    Path(__file__).resolve().parent.parent / "graphify-out" / "graph.json")
MCP_BIN = str(Path.home() / "AppData/Roaming/uv/tools/graphifyy/Scripts/graphify-mcp.exe")


async def main() -> int:
    params = StdioServerParameters(command=MCP_BIN, args=["--graph", GRAPH])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            r = await session.call_tool("graph_stats", {})
            print("=== GRAPH_STATS ===")
            print(r.content[0].text[:600])

            r = await session.call_tool("god_nodes", {"top_n": 8})
            print("\n=== GOD_NODES (top 8) ===")
            print(r.content[0].text[:800])

            r = await session.call_tool("query_graph",
                                        {"question": "how does the agent call the retriever",
                                         "depth": 2})
            print("\n=== QUERY_GRAPH ===")
            print(r.content[0].text[:700])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
