"""Inspecciona las tools que expone el MCP server de graphify (graphify-mcp)."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

GRAPH = sys.argv[1] if len(sys.argv) > 1 else str(
    Path(r"C:\Users\P0zcl\Desktop\proyectos\freq\docs-freqtrade\02-configuracion\graphify-out\graph.json"))

MCP_BIN = str(Path.home() / "AppData/Roaming/uv/tools/graphifyy/Scripts/graphify-mcp.exe")


async def main() -> int:
    params = StdioServerParameters(command=MCP_BIN, args=["--graph", GRAPH])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("INIT:", init.serverInfo.name, init.serverInfo.version)
            result = await session.list_tools()
            tools = result.tools
            print(f"TOOLS ({len(tools)}):")
            for t in tools:
                props = list((t.inputSchema or {}).get("properties", {}).keys())
                print(f"  - {t.name}")
                print(f"      desc: {(t.description or '')[:120]}")
                print(f"      params: {props}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
