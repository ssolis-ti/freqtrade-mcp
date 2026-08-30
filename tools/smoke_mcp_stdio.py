"""Smoke end-to-end del MCP por stdio: lanza run_bloque.py y conversa por el protocolo.

Usa el cliente MCP oficial (mcp.client.stdio) contra el server real.
"""
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    python = str(Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe")
    server = str(Path(__file__).resolve().parent.parent / "servers" / "run_bloque.py")
    params = StdioServerParameters(command=python, args=[server, "02-configuracion"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("INIT ok:", init.serverInfo.name, init.serverInfo.version)

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("TOOLS:", names)
            assert "consultar_docs" in names and "health" in names

            h = await session.call_tool("health", {})
            print("HEALTH:", h.content[0].text)
            hd = json.loads(h.content[0].text)
            assert hd["ok"] is True

            r = await session.call_tool("consultar_docs", {"query": "trading mode futures", "top_k": 2})
            hits = json.loads(r.content[0].text)
            print(f"CONSULTA: {len(hits)} hits")
            for hit in hits:
                print(f"  [{hit['score']}] {hit['mirror']} {hit['path']} :: {hit['heading']}")
            assert len(hits) > 0

            r2 = await session.call_tool("consultar_docs", {"query": "receta de pizza napolitana", "top_k": 3})
            assert json.loads(r2.content[0].text) == []
            print("NO-HITS: [] correcto")
    print("SMOKE MCP STDIO: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
