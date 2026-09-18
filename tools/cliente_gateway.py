"""Cliente MCP HTTP: verifica el gateway universal (tools + seguridad).

Se conecta por HTTP a http://127.0.0.1:8765/mcp (o la IP LAN del gateway).
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/mcp"


async def main() -> int:
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"CONECTADO: {init.serverInfo.name} v{init.serverInfo.version}")
            print(f"URL: {URL}")

            res = await session.list_tools()
            tools = res.tools if hasattr(res, "tools") else res
            nombres = sorted(t.name for t in tools)
            print(f"\nTOOLS EXPUESTAS ({len(nombres)}):")
            for n in nombres:
                print(f"  - {n}")

            # Seguridad: las de escritura NO deben existir en solo-lectura
            peligrosas = [t for t in ["entrar", "salir", "vetar", "detener_compras"]
                          if t in nombres]
            print(f"\nSEGURIDAD: tools de escritura expuestas = {peligrosas or 'NINGUNA (correcto)'}")

            # Prueba funcional real
            r = await session.call_tool("docs_listar_bloques", {})
            bloques = json.loads(r.content[0].text)
            print(f"\ndocs_listar_bloques -> {len(bloques)} bloques")

            r = await session.call_tool("docs_health", {"bloque": "configuracion"})
            h = json.loads(r.content[0].text)
            print(f"docs_health(configuracion) -> {h.get('chunk_count')} chunks, {h.get('embed_model')}")

            r = await session.call_tool("grafo_estadisticas", {})
            print(f"grafo_estadisticas -> {r.content[0].text[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
