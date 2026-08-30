"""Tests del Manager (mocks del LLM — sin gateway)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from despacho.manager import Manager, _extraer_json, _plan_heuristico


class FakeResp:
    class Choice:
        def __init__(self, content):
            self.message = type("M", (), {"content": content})()

    def __init__(self, content):
        self.choices = [self.Choice(content)]


class FakeClient:
    def __init__(self, content):
        self.content = content
        self.chat = type("C", (), {"completions": type("CP", (), {
            "create": lambda self, **kw: FakeResp(content)})()})()


_PLAN_JSON = json.dumps({
    "pasos": [
        {"orden": 1, "dominio": "09-datos", "tool": "download-data",
         "params": {"pairs": ["X/USDT"]}, "estado": "pendiente"},
        {"orden": 2, "dominio": "03-estrategia", "tool": "escribir_estrategia",
         "params": {}, "estado": "pendiente"},
        {"orden": 3, "dominio": "04-backtesting", "tool": "backtesting",
         "params": {}, "estado": "pendiente"},
        {"orden": 4, "dominio": "07-riesgo-futuros", "tool": "revisar_riesgo",
         "params": {}, "estado": "pendiente"},
    ]
})


def test_plan_mision_descompone():
    m = Manager(client=FakeClient(_PLAN_JSON))
    plan = m.plan_mision("cazar alts momentum 7d")
    assert plan["mision"] == "cazar alts momentum 7d"
    assert len(plan["pasos"]) == 4
    for p in plan["pasos"]:
        assert p["dominio"] and p["tool"] and p["estado"] == "pendiente"
    assert plan["decidir_dry_run"] is False


def test_decidir_dry_run_solo_con_validacion_ok():
    m = Manager(client=FakeClient(_PLAN_JSON))
    m.plan_mision("mision")
    # Sin resultados: no decide
    assert m.plan["decidir_dry_run"] is False
    # backtesting OK pero riesgo no -> NO decide
    m.registrar_resultado("backtesting", True)
    assert m.plan["decidir_dry_run"] is False
    # ambos OK -> decide
    m.registrar_resultado("revisar_riesgo", True)
    assert m.plan["decidir_dry_run"] is True


def test_bloqueo_impide_dry_run():
    m = Manager(client=FakeClient(_PLAN_JSON))
    m.plan_mision("mision")
    m.registrar_resultado("backtesting", False, motivo="drawdown 45%")
    m.registrar_resultado("revisar_riesgo", True)
    assert m.plan["decidir_dry_run"] is False
    assert len(m.plan["bloqueos"]) == 1
    assert "drawdown" in m.plan["bloqueos"][0]["motivo"]


def test_plan_heuristico_sin_llm():
    pasos = _plan_heuristico("mision")
    assert len(pasos) == 4
    assert pasos[0]["tool"] == "download-data"
    assert pasos[3]["tool"] == "revisar_riesgo"


def test_extraer_json_con_prosa():
    texto = "Aqui va el plan:\n```json\n" + _PLAN_JSON + "\n```\nFin."
    data = json.loads(_extraer_json(texto))
    assert "pasos" in data


def test_delegar_pasa_por_gate():
    m = Manager(client=FakeClient(_PLAN_JSON))
    # Sin OK -> PermissionError
    try:
        m.delegar("entrar", False)
        assert False, "deberia lanzar"
    except PermissionError:
        pass
    # Con OK -> devuelve params
    assert m.delegar("entrar", True, {"pair": "X/USDT"}) == {"pair": "X/USDT"}
