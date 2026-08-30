"""Smoke end-to-end del MCP del AGENTE por stdio: run_agente.py real.

Usa el cliente MCP oficial contra el server real (1 llamada LLM con hits).
"""
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    python = str(Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe")
    server = str(Path(__file__).resolve().parent.parent / "servers" / "run_agente.py")
    params = StdioServerParameters(command=python, args=[server, "02-configuracion"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("INIT ok:", init.serverInfo.name, init.serverInfo.version)

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("TOOLS:", names)
            assert {"responder", "consultar_docs", "health"} <= set(names)

            h = await session.call_tool("health", {})
            hd = json.loads(h.content[0].text)
            print("HEALTH:", hd.get("block"), hd.get("chunk_count"), "chunks |",
                  hd.get("modelo_activo"))
            assert hd["ok"] is True

            r = await session.call_tool("responder",
                                        {"query": "What is the purpose of dry run mode?",
                                         "top_k": 2})
            resp = json.loads(r.content[0].text)
            print("RESPONDER estado:", resp.get("estado"), "| citas:", len(resp.get("citas", [])))
            print("respuesta:", resp.get("respuesta", "")[:250])
            assert resp.get("estado") in ("ok", "degradado_llm")

            r2 = await session.call_tool("responder",
                                         {"query": "receta de cocina italiana", "top_k": 2})
            resp2 = json.loads(r2.content[0].text)
            print("NO-HITS estado:", resp2.get("estado"))
            assert resp2.get("estado") == "sin_hits"
    print("SMOKE AGENTE MCP STDIO: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
