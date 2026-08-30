"""Smoke del MCP del despacho: tools listadas + gate de permisos + plan.

Usa un FreqtradeClient con MockTransport (sin freqtrade real) y un Manager
con cliente simulado, montados en el FastMCP del despacho.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from despacho.manager import Manager
from despacho.wrapper import FreqtradeClient
from servers.despacho_mcp import build_despacho_mcp


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/token/login"):
        return httpx.Response(200, json={"access_token": "tok", "refresh_token": "ref"})
    if url.endswith("/status"):
        return httpx.Response(200, json={"trades": []})
    if url.endswith("/profit"):
        return httpx.Response(200, json={"profit_closed_coin": 2.3})
    if url.endswith("/show_config"):
        return httpx.Response(200, json={"dry_run": True, "state": "running"})
    if url.endswith("/forceenter"):
        return httpx.Response(200, json={"pair": "X/USDT", "trade": "abc"})
    return httpx.Response(200, json={"ok": True})


class FakeLLM:
    class Chat:
        class Completions:
            @staticmethod
            def create(**kwargs):
                content = json.dumps({"pasos": [
                    {"orden": 1, "dominio": "09-datos", "tool": "download-data",
                     "params": {"pairs": ["X/USDT"]}, "estado": "pendiente"},
                    {"orden": 2, "dominio": "04-backtesting", "tool": "backtesting",
                     "params": {}, "estado": "pendiente"},
                    {"orden": 3, "dominio": "07-riesgo-futuros",
                     "tool": "revisar_riesgo", "params": {}, "estado": "pendiente"},
                ]})
                resp = type("R", (), {"choices": [type("C", (), {
                    "message": type("M", (), {"content": content})()})()]})()
                return resp
        completions = Completions()
    chat = Chat()


async def main() -> int:
    ft = FreqtradeClient(base_url="http://test:8080", user="u", password="p")
    ft._client = httpx.Client(transport=httpx.MockTransport(_handler))
    mcp = build_despacho_mcp(client=ft, manager=Manager(client=FakeLLM()))

    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    print("TOOLS:", names)
    assert "bot_status" in names and "entrar" in names and "plan_mision" in names

    # Lectura sin OK
    r = await mcp.call_tool("bot_status", {})
    print("bot_status:", r[0][0].text)
    assert json.loads(r[0][0].text) == {"trades": []}

    # Ejecucion sin OK -> PermissionError
    try:
        await mcp.call_tool("entrar", {"pair": "X/USDT", "ok_usuario": False})
        print("FALLO: entrar sin OK no lanzo error")
        return 1
    except Exception as e:
        print(f"entrar sin OK -> {type(e).__name__}: {str(e)[:80]}")

    # Ejecucion con OK
    r = await mcp.call_tool("entrar", {"pair": "X/USDT", "ok_usuario": True,
                                       "stake_amount": 10})
    print("entrar con OK:", r[0][0].text)
    assert "X/USDT" in r[0][0].text

    # Manager: plan
    r = await mcp.call_tool("plan_mision", {"mision": "cazar alts momentum 7d"})
    plan = json.loads(r[0][0].text)
    print(f"plan_mision: {len(plan['pasos'])} pasos, decidir_dry_run={plan['decidir_dry_run']}")
    assert len(plan["pasos"]) == 3

    print("SMOKE DESPACHO MCP: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
