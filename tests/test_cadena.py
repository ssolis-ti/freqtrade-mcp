"""Tests de la cadena dry-run (mocks de subprocess — sin freqtrade)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from despacho import cadena


class FakeProc:
    def __init__(self, rc, stdout="", stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


def test_descargar_datos_ok(monkeypatch):
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(0))
    r = cadena.descargar_datos(["X/USDT"], "1h")
    assert r["ok"] is True


def test_descargar_datos_falla(monkeypatch):
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(1, stderr="boom"))
    r = cadena.descargar_datos(["X/USDT"])
    assert r["ok"] is False
    assert "boom" in r["stderr"]


def test_backtesting_umbrales(monkeypatch):
    ok_out = ("...\nProfit factor: 1.85\nMax Drawdown: 12.5%\n...")
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(0, stdout=ok_out))
    r = cadena.backtesting()
    assert r["ok"] is True
    assert r["profit_factor"] == 1.85
    assert r["drawdown"] == 12.5


def test_backtesting_rechaza_drawdown_alto(monkeypatch):
    bad_out = "Profit factor: 1.1\nMax Drawdown: 45.2%"
    monkeypatch.setattr(cadena, "_run_ft",
                        lambda *a, **k: FakeProc(0, stdout=bad_out))
    r = cadena.backtesting()
    assert r["ok"] is False  # PF < 1.3 o DD > 30 -> rechazo
    assert r["profit_factor"] == 1.1


def test_cadena_corta_en_fallo(monkeypatch):
    calls = []

    def fake_run(*a, **k):
        calls.append(a[0])
        if a[0] == "backtesting":
            return FakeProc(1, stderr="sin datos")
        return FakeProc(0)

    monkeypatch.setattr(cadena, "_run_ft", fake_run)
    r = cadena.ejecutar_cadena(["X/USDT"])
    assert r["datos"]["ok"] is True
    assert r["backtest"]["ok"] is False
    assert r["_bloqueado_en"] == "backtest"


def test_revisar_riesgo_siempre_ok():
    r = cadena.revisar_riesgo(leverage_max=3)
    assert r["ok"] is True
    assert r["leverage_max"] == 3.0
