"""Tests del wrapper REST (mocks de httpx — sin freqtrade real)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest

from despacho.wrapper import FreqtradeClient, TOOLS_EJECUCION


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/token/login"):
        return httpx.Response(200, json={"access_token": "tok", "refresh_token": "ref"})
    if url.endswith("/forceenter"):
        return httpx.Response(200, json={"pair": "X/USDT", "trade": "abc"})
    if url.endswith("/status"):
        return httpx.Response(200, json={"trades": []})
    if url.endswith("/profit"):
        return httpx.Response(200, json={"profit_closed_coin": 1.5})
    if url.endswith("/show_config"):
        return httpx.Response(200, json={"dry_run": True, "state": "running"})
    if url.endswith("/blacklist"):
        return httpx.Response(200, json={"blacklist": ["X/USDT"]})
    return httpx.Response(200, json={"ok": True})


def _client() -> FreqtradeClient:
    c = FreqtradeClient(base_url="http://test:8080", user="u", password="p")
    c._client = httpx.Client(transport=httpx.MockTransport(_handler))
    return c


def test_tools_ejecucion_definidas():
    assert TOOLS_EJECUCION == {
        "entrar", "salir", "vetar", "bloquear",
        "detener_compras", "arrancar", "detener"}


def test_auth_y_lectura():
    c = _client()
    r = c.status()
    assert r == {"trades": []}
    assert c._access_token == "tok"  # se autentico


def test_profit():
    c = _client()
    assert c.profit() == {"profit_closed_coin": 1.5}


def test_entrar():
    c = _client()
    r = c.entrar("X/USDT", side="long", stake_amount=10)
    assert r["pair"] == "X/USDT"


def test_show_config_dry_run():
    c = _client()
    dry, msg = c.verificar_dry_run()
    assert dry is True
    assert "dry_run=True" in msg


def test_relogin_en_401(monkeypatch):
    """Tras 401, relogin y reintento una vez."""
    c = _client()
    llamadas = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/token/login"):
            return httpx.Response(200, json={"access_token": "tok2",
                                             "refresh_token": "ref2"})
        llamadas["n"] += 1
        if url.endswith("/status") and llamadas["n"] == 1:
            return httpx.Response(401, json={"error": "token expired"})
        return _handler(request)

    c._client = httpx.Client(transport=httpx.MockTransport(flaky))
    r = c.status()
    assert r == {"trades": []}  # relogin + reintento funciono
    assert c._access_token == "tok2"
