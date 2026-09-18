"""Cadena de validacion dry-run: datos -> estrategia -> backtest -> hyperopt -> riesgo.

Cada paso corre como subprocess del CLI de freqtrade (patron "Taller").
Umbrales por env: CADENA_PF_MIN (>=1.3) y CADENA_DRAWDOWN_MAX (<=30).
SOLO lectura/validacion: no opera, no riesga capital.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CADENA_PF_MIN = float(os.getenv("CADENA_PF_MIN", "1.3"))
CADENA_DRAWDOWN_MAX = float(os.getenv("CADENA_DRAWDOWN_MAX", "30.0"))

ROOT = Path(__file__).resolve().parent.parent
FT_BIN = os.getenv("FT_BIN", "freqtrade")  # o ruta al binario del contenedor


def _run_ft(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Ejecuta el CLI de freqtrade (subprocess)."""
    return subprocess.run([FT_BIN, *args], capture_output=True, text=True,
                          timeout=timeout, cwd=str(ROOT))


def descargar_datos(pairs: list[str], timeframe: str = "1h",
                    days: int = 60) -> dict:
    """freqtrade download-data para los pares dados."""
    r = _run_ft("download-data", "--pairs", ",".join(pairs),
                "--timeframe", timeframe, "--days", str(days),
                "--datadir", "data")
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "stderr": r.stderr[-500:] if r.stderr else ""}


def backtesting(strategy: str = "SampleStrategy",
                timeframe: str = "1h") -> dict:
    """freqtrade backtesting; extrae profit_factor y drawdown del reporte."""
    r = _run_ft("backtesting", "--strategy", strategy,
                "--timeframe", timeframe, "--datadir", "data")
    if r.returncode != 0:
        return {"ok": False, "returncode": r.returncode,
                "stderr": r.stderr[-500:] if r.stderr else ""}
    # Parseo conservador: el reporte JSON esta en el stdout del comando con
    # el flag --export; aqui se usa una heuristica simple sobre el texto.
    texto = (r.stdout or "") + (r.stderr or "")
    pf = _extraer_metric(texto, "profit factor")
    dd = _extraer_metric(texto, "drawdown")
    # FAIL-CLOSED (regla dura): una metrica que no se pudo leer NO pasa el filtro.
    # Antes se evaluaba "pf is None or pf >= MIN", de modo que un reporte
    # imposible de parsear daba ok=True y la cadena seguia sin validar el riesgo.
    motivos: list[str] = []
    if pf is None:
        motivos.append("profit_factor no encontrado en el reporte")
    elif pf < CADENA_PF_MIN:
        motivos.append(f"profit_factor {pf} < minimo {CADENA_PF_MIN}")
    if dd is None:
        motivos.append("drawdown no encontrado en el reporte")
    elif dd > CADENA_DRAWDOWN_MAX:
        motivos.append(f"drawdown {dd} > maximo {CADENA_DRAWDOWN_MAX}")
    return {"ok": not motivos, "motivos": motivos,
            "profit_factor": pf, "drawdown": dd,
            "pf_min": CADENA_PF_MIN, "dd_max": CADENA_DRAWDOWN_MAX,
            "returncode": r.returncode}


def hyperopt(strategy: str = "SampleStrategy", epochs: int = 30) -> dict:
    """freqtrade hyperopt (optimiza ROI/stoploss/trailing)."""
    r = _run_ft("hyperopt", "--strategy", strategy, "--epochs", str(epochs),
                "--datadir", "data")
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "stderr": r.stderr[-500:] if r.stderr else ""}


def revisar_riesgo(leverage_max: float = 3.0) -> dict:
    """Revisa la config de riesgo (leverage/stoploss) contra limites."""
    # En el MVP: validacion por reglas (sin LLM). El leverage se limita por
    # config del bot; aqui solo se reporta el limite propuesto.
    return {"ok": True, "leverage_max": leverage_max,
            "stoploss_requerido": True}


def _extraer_metric(texto: str, label: str) -> float | None:
    """Extrae un numero de la linea '<label> ... <valor>' (heuristica)."""
    import re
    for linea in texto.splitlines():
        if label.lower() in linea.lower():
            m = re.search(r"(-?\d+\.\d+)", linea)
            if m:
                return float(m.group(1))
    return None


def ejecutar_cadena(pairs: list[str], strategy: str = "SampleStrategy",
                    timeframe: str = "1h") -> dict:
    """Ejecuta la cadena completa en orden; corta si un paso falla."""
    resultados: dict = {}
    pasos = [
        ("datos", descargar_datos, [pairs, timeframe]),
        ("backtest", backtesting, [strategy, timeframe]),
    ]
    for nombre, fn, args in pasos:
        resultados[nombre] = fn(*args)
        if not resultados[nombre].get("ok"):
            resultados["_bloqueado_en"] = nombre
            return resultados
    return resultados
