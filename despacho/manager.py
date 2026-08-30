"""Manager orquestador: mision -> plan por dominios -> decision dry-run.

El Manager descompone una mision en pasos, cada uno asignado al agente cuyo
bloque documental lo habilita (constitution I). Decide dry-run SOLO si los
dominios de validacion (backtesting + riesgo) dan OK; si un paso falla, lo
registra como bloqueo y NO propone dry-run.
"""
from __future__ import annotations

import json
import os
import re
import warnings

from .permisos import autorizar

MANAGER_MODEL = os.getenv("MANAGER_MODEL", "deepseek-via-inference")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:4000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Dominio documental que habilita cada tipo de paso (constitution I)
_DOMINIO_POR_PASO = {
    "download-data": "09-datos",
    "escribir_estrategia": "03-estrategia",
    "backtesting": "04-backtesting",
    "hyperopt": "05-hyperopt",
    "revisar_riesgo": "07-riesgo-futuros",
    "operar": "08-control",
}

_VALIDACION_OBLIGATORIA = {"backtesting", "revisar_riesgo"}

_SYSTEM_PROMPT = (
    "Eres el Manager de una oficina de agentes que operan freqtrade. "
    "Descompone la mision del usuario en pasos concretos. Cada paso tiene: "
    "orden, dominio (uno de: 09-datos, 03-estrategia, 04-backtesting, "
    "05-hyperopt, 07-riesgo-futuros, 08-control), tool (una de: download-data, "
    "escribir_estrategia, backtesting, hyperopt, revisar_riesgo, operar), "
    "params (objeto) y estado ('pendiente'). Responde SOLO JSON valido con la "
    "clave 'pasos' (lista). Nunca inventes pares: usa 'X/USDT' como placeholder."
)


class Manager:
    """Orquestador: plan_mision + decision de dry-run."""

    def __init__(self, client=None) -> None:
        self._client = client
        self.plan: dict = {"mision": "", "pasos": [], "decidir_dry_run": False,
                           "bloqueos": []}

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=LLM_BASE_URL,
                                  api_key=LLM_API_KEY or "no-need",
                                  timeout=(5.0, 90.0))
        return self._client

    def plan_mision(self, mision: str) -> dict:
        """Descompone la mision en un plan de pasos por dominio (LLM gateway)."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"MISION: {mision}"},
        ]
        try:
            resp = self._get_client().chat.completions.create(
                model=MANAGER_MODEL, messages=messages,
                max_tokens=1500, temperature=0.2)
            texto = resp.choices[0].message.content or "{}"
            data = json.loads(_extraer_json(texto))
            pasos = data.get("pasos", [])
        except Exception as e:  # noqa: BLE001 - degrada a plan heuristico
            warnings.warn(f"Manager LLM fallo ({type(e).__name__}: {e}); "
                          "plan heuristico.", RuntimeWarning, stacklevel=3)
            pasos = _plan_heuristico(mision)

        self.plan = {
            "mision": mision,
            "pasos": _normalizar_pasos(pasos),
            "decidir_dry_run": False,
            "bloqueos": [],
        }
        return self.plan

    def registrar_resultado(self, tool: str, ok: bool, motivo: str = "") -> None:
        """Registra el resultado de un paso y actualiza la decision de dry-run."""
        for paso in self.plan["pasos"]:
            if paso.get("tool") == tool:
                paso["estado"] = "ok" if ok else "fallo"
                if not ok:
                    self.plan["bloqueos"].append(
                        {"dominio": paso.get("dominio"), "motivo": motivo or tool})
                break
        self._redecidir()

    def _redecidir(self) -> None:
        """decidir_dry_run = True SOLO si backtesting y riesgo dieron OK (FR-004)."""
        ok_validacion = all(
            any(p.get("tool") == v and p.get("estado") == "ok"
                for p in self.plan["pasos"])
            for v in _VALIDACION_OBLIGATORIA
        )
        self.plan["decidir_dry_run"] = bool(ok_validacion and not self.plan["bloqueos"])

    def estado_plan(self) -> dict:
        return self.plan

    def delegar(self, tool: str, ok_usuario: bool, params: dict | None = None):
        """Delega un paso de ejecucion; SIEMPRE pasa por el gate de permisos."""
        autorizar(tool, ok_usuario)
        return params or {}


def _extraer_json(texto: str) -> str:
    """Extrae el primer objeto JSON del texto (el LLM puede añadir prosa)."""
    m = re.search(r"\{.*\}", texto, re.S)
    return m.group(0) if m else "{}"


def _normalizar_pasos(pasos: list) -> list:
    out = []
    for i, p in enumerate(pasos):
        tool = str(p.get("tool", "")).strip()
        dominio = str(p.get("dominio", _DOMINIO_POR_PASO.get(tool, ""))).strip()
        out.append({
            "orden": int(p.get("orden", i + 1)),
            "dominio": dominio,
            "tool": tool,
            "params": p.get("params", {}) or {},
            "estado": str(p.get("estado", "pendiente")),
        })
    return out


def _plan_heuristico(mision: str) -> list:
    """Plan por reglas cuando el LLM no esta disponible (degradacion elegante)."""
    pasos = [
        {"orden": 1, "dominio": "09-datos", "tool": "download-data",
         "params": {"pairs": ["X/USDT"], "timeframe": "1h"}, "estado": "pendiente"},
        {"orden": 2, "dominio": "03-estrategia", "tool": "escribir_estrategia",
         "params": {"momentum": "RSI+volumen"}, "estado": "pendiente"},
        {"orden": 3, "dominio": "04-backtesting", "tool": "backtesting",
         "params": {"timeframe": "1h"}, "estado": "pendiente"},
        {"orden": 4, "dominio": "07-riesgo-futuros", "tool": "revisar_riesgo",
         "params": {"leverage_max": 3}, "estado": "pendiente"},
    ]
    return pasos
