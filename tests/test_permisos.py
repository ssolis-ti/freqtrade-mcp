"""Tests del gate de permisos (regla dura, constitution III)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from despacho.permisos import autorizar, requiere_ok


def test_requiere_ok_solo_ejecucion():
    for t in ["entrar", "salir", "vetar", "bloquear",
              "detener_compras", "arrancar", "detener"]:
        assert requiere_ok(t) is True
    for t in ["bot_status", "bot_profit", "plan_mision", "consultar_docs"]:
        assert requiere_ok(t) is False


def test_autorizar_sin_ok_lanza():
    with pytest.raises(PermissionError, match="OK explicito"):
        autorizar("entrar", False)


def test_autorizar_con_ok_pasa():
    autorizar("entrar", True)  # no debe lanzar
    autorizar("salir", True)


def test_lectura_no_exige_ok():
    autorizar("bot_status", False)  # no debe lanzar
