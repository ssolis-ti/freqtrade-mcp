#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
freqtrade-mcp — wrapper TOOL-ONLY de la REST API de freqtrade (/api/v1).
Convierte los endpoints operativos en tools MCP para que los agentes del
Despacho (Market Scout, Position Manager, Risk Sentinel, Analyst, Manager)
controlen freqtrade como empleados persistentes.

PATRÓN: "Direct httpx" (skill mcp-agent-office) — sin subprocess, sin LLM
en el loop. Cada endpoint de freqtrade = una tool MCP.

Ejecutar:  python mcp_server.py   (transporte stdio, para registrar en Hermes)
Config por env vars (no hardcodear secretos).
"""
import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

# ---- Configuración por entorno (nunca hardcodear credenciales) ----
FT_URL = os.environ.get("FREQTRADE_URL", "http://127.0.0.1:8080")
FT_USER = os.environ.get("FREQTRADE_USER", "Freqtrader")
FT_PASS = os.environ.get("FREQTRADE_PASS", "")
FT_WORKER = os.environ.get("FREQTRADE_WORKER", "empleado")  # nombre del agente
FT_API = f"{FT_URL}/api/v1"

mcp = FastMCP(f"freqtrade-{FT_WORKER}",
              instructions=(
                  "Controlas la REST API de freqtrade para el rol "
                  f"'{FT_WORKER}'. Sigue las reglas del módulo de riesgo: "
                  "nunca pases a Live sin OK explícito del usuario."
              ))

_ACCESS_TOKEN = None
_REFRESH_TOKEN = None
_client = httpx.Client(timeout=30.0)


def _headers() -> dict:
    if _ACCESS_TOKEN:
        return {"Authorization": f"Bearer {_ACCESS_TOKEN}"}
    return {}


def _auth():
    """Login y refresco de JWT. El access token dura ~15 min."""
    global _ACCESS_TOKEN, _REFRESH_TOKEN
    r = _client.post(f"{FT_API}/token/login", auth=(FT_USER, FT_PASS),
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    _ACCESS_TOKEN = r.json()["access_token"]
    _REFRESH_TOKEN = r.json()["refresh_token"]


def _call(method: str, path: str, params: dict = None, body: dict = None):
    """Wrapper genérico: autentica si hace falta y hace la llamada REST."""
    if not _ACCESS_TOKEN:
        _auth()
    url = f"{FT_API}/{path.lstrip('/')}"
    try:
        resp = _client.request(method, url, params=params, json=body, headers=_headers())
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except httpx.HTTPStatusError as e:
        # token expirado -> relogin y reintentar una vez
        if e.response.status_code == 401:
            _auth()
            resp = _client.request(method, url, params=params, json=body, headers=_headers())
            resp.raise_for_status()
            return resp.json() if resp.text else {}
        raise


# ---------------- Tools: lectura / consulta ----------------

@mcp.tool()
def ping() -> str:
    """Verifica que el bot responde. Devuelve status."""
    return json.dumps(_call("GET", "ping"))


@mcp.tool()
def status() -> str:
    """Estado de los trades abiertos."""
    return json.dumps(_call("GET", "status"))


@mcp.tool()
def balance() -> str:
    """Balance de la cuenta del exchange."""
    return json.dumps(_call("GET", "balance"))


@mcp.tool()
def profit() -> str:
    """Resumen de profit/loss del bot."""
    return json.dumps(_call("GET", "profit"))


@mcp.tool()
def performance() -> str:
    """Rendimiento por moneda."""
    return json.dumps(_call("GET", "performance"))


@mcp.tool()
def available_pairs(timeframe: str, stake_currency: str = "USDT") -> str:
    """Pairs con datos disponibles para el timeframe dado."""
    return json.dumps(_call("GET", "available_pairs",
                            {"timeframe": timeframe, "stake_currency": stake_currency}))


@mcp.tool()
def pair_candles(pair: str, timeframe: str, limit: int = 100) -> str:
    """Velas en vivo para un par dado (OHLCV)."""
    return json.dumps(_call("GET", "pair_candles",
                            {"pair": pair, "timeframe": timeframe, "limit": limit}))


@mcp.tool()
def whitelist() -> str:
    """Lista blanca de pares actual."""
    return json.dumps(_call("GET", "whitelist"))


@mcp.tool()
def blacklist() -> str:
    """Lista negra de pares actual."""
    return json.dumps(_call("GET", "blacklist"))


@mcp.tool()
def logs(limit: int = 100) -> str:
    """Últimos logs del bot."""
    return json.dumps(_call("GET", "logs", {"limit": limit}))


@mcp.tool()
def count() -> str:
    """Cantidad de trades abiertos."""
    return json.dumps(_call("GET", "count"))


# ---------------- Tools: ejecución / control de riesgo ----------------

@mcp.tool()
def forceenter(pair: str, side: str = "long", stake_amount: float = None,
               leverage: float = None, enter_tag: str = "mcp") -> str:
    """FUERZA ENTRADA en un par. side='long'|'short'. USA CON CUIDADO: riesga capital real.
    Solo con autorización explícita del usuario."""
    body = {"pair": pair, "side": side, "enter_tag": enter_tag}
    if stake_amount is not None:
        body["stake_amount"] = stake_amount
    if leverage is not None:
        body["leverage"] = leverage
    return json.dumps(_call("POST", "forceenter", body=body))


@mcp.tool()
def forceexit(trade_id: int, ordertype: str = "market") -> str:
    """FUERZA SALIDA de un trade. Preferir 'market'."""
    return json.dumps(_call("POST", "forceexit",
                            body={"tradeid": trade_id, "ordertype": ordertype}))


@mcp.tool()
def blacklist_add(pairs: list) -> str:
    """Añade pares a la blacklist (vetar por delist/shutdown/riesgo)."""
    return json.dumps(_call("POST", "blacklist", body={"blacklist": pairs}))


@mcp.tool()
def lock_pair(pair: str, until: str, reason: str = "", side: str = "*") -> str:
    """Bloquea un par hasta una fecha (ISO 'YYYY-MM-DD HH:MM:SSZ')."""
    return json.dumps(_call("POST", "locks",
                            body={"pair": pair, "until": until, "reason": reason, "side": side}))


@mcp.tool()
def stopbuy() -> str:
    """Detiene NUEVAS compras (sella salidas con gracia)."""
    return json.dumps(_call("POST", "stopbuy"))


@mcp.tool()
def start() -> str:
    """Arranca el bot si estaba detenido."""
    return json.dumps(_call("POST", "start"))


@mcp.tool()
def stop() -> str:
    """Detiene el bot por completo."""
    return json.dumps(_call("POST", "stop"))


@mcp.tool()
def show_config() -> str:
    """Muestra la config combinada final del bot (precedencia CLI>env>config>estrategia)."""
    return json.dumps(_call("GET", "show_config"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
