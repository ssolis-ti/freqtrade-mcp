"""Tests de las barreras de seguridad de la fase 1.

Cubren las tres garantias que antes no existian:
  1. La cadena falla CERRADA si una metrica de riesgo no se pudo leer.
  2. Ninguna tool de ejecucion corre sin verificar dry_run contra el bot real.
  3. El gateway HTTP exige Bearer y no se deja exponer a la red sin key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from despacho import cadena, permisos
from servers import gateway_http


class FakeProc:
    def __init__(self, rc, stdout="", stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


class FakeClient:
    """Cliente minimo: controla que devuelve verificar_dry_run."""

    def __init__(self, dry=True, explota=False):
        self.dry = dry
        self.explota = explota
        self.llamadas = 0

    def verificar_dry_run(self):
        self.llamadas += 1
        if self.explota:
            raise RuntimeError("bot caido")
        return self.dry, f"dry_run={self.dry}"


@pytest.fixture(autouse=True)
def _limpiar():
    permisos.limpiar_cache_dry_run()
    yield
    permisos.limpiar_cache_dry_run()


# --- 1. Fail-closed de los umbrales de riesgo ---

def test_backtest_sin_metricas_no_pasa(monkeypatch):
    """Un reporte que no se puede parsear NO debe dar ok=True."""
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(0, stdout="salida ilegible"))
    r = cadena.backtesting()
    assert r["ok"] is False
    assert any("profit_factor" in m for m in r["motivos"])
    assert any("drawdown" in m for m in r["motivos"])


def test_backtest_drawdown_excesivo_no_pasa(monkeypatch):
    salida = "Profit factor: 2.10\nMax Drawdown: 47.0%\n"
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(0, stdout=salida))
    r = cadena.backtesting()
    assert r["ok"] is False
    assert "drawdown" in r["motivos"][0]


# --- 2. dry_run obligatorio antes de ejecutar ---

def test_dry_run_ok_no_bloquea():
    permisos.exigir_dry_run(FakeClient(dry=True))  # no debe lanzar


def test_live_sin_autorizacion_bloquea(monkeypatch):
    monkeypatch.setattr(permisos, "PERMITIR_LIVE", False)
    with pytest.raises(PermissionError, match="PERMITIR_LIVE"):
        permisos.exigir_dry_run(FakeClient(dry=False))


def test_live_con_autorizacion_humana_pasa(monkeypatch):
    monkeypatch.setattr(permisos, "PERMITIR_LIVE", True)
    permisos.exigir_dry_run(FakeClient(dry=False))  # el operador lo autorizo


def test_bot_inalcanzable_bloquea():
    """Fail-closed: si no se puede comprobar, no se opera."""
    with pytest.raises(PermissionError, match="fail-closed"):
        permisos.exigir_dry_run(FakeClient(explota=True))


def test_cache_evita_una_llamada_por_operacion():
    c = FakeClient(dry=True)
    for _ in range(5):
        permisos.exigir_dry_run(c)
    assert c.llamadas == 1


def test_despacho_ejecucion_exige_dry_run(monkeypatch):
    """La tool 'entrar' con ok_usuario=True sigue bloqueada si el bot esta live."""
    from servers.despacho_mcp import build_despacho_mcp

    cliente = FakeClient(dry=False)
    cliente.entrar = lambda *a, **k: {"no": "deberia llegar aqui"}
    monkeypatch.setattr(permisos, "PERMITIR_LIVE", False)
    mcp = build_despacho_mcp(client=cliente, manager=object())
    entrar = mcp._tool_manager.get_tool("entrar")
    with pytest.raises(PermissionError, match="PERMITIR_LIVE"):
        entrar.fn(pair="BTC/USDT", ok_usuario=True)


# --- 3. Auth del gateway ---

def test_gateway_loopback_reconocido():
    assert gateway_http._es_loopback("127.0.0.1") is True
    assert gateway_http._es_loopback("0.0.0.0") is False
    assert gateway_http._es_loopback("192.168.1.50") is False


def test_middleware_rechaza_sin_token():
    import asyncio

    llamado = {"si": False}

    async def app_interna(scope, receive, send):
        llamado["si"] = True

    mw = gateway_http.BearerAuthMiddleware(app_interna, "clave-secreta")
    enviados = []

    async def send(msg):
        enviados.append(msg)

    scope = {"type": "http", "headers": [(b"authorization", b"Bearer incorrecta")]}
    asyncio.run(mw(scope, None, send))
    assert enviados[0]["status"] == 401
    assert llamado["si"] is False


def test_middleware_acepta_token_correcto():
    import asyncio

    llamado = {"si": False}

    async def app_interna(scope, receive, send):
        llamado["si"] = True

    mw = gateway_http.BearerAuthMiddleware(app_interna, "clave-secreta")
    scope = {"type": "http", "headers": [(b"authorization", b"Bearer clave-secreta")]}
    asyncio.run(mw(scope, None, lambda m: None))
    assert llamado["si"] is True
