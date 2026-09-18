"""Gate de permisos del despacho (regla dura, constitution III).

Las tools de ejecucion (entrar, salir, vetar, bloquear, detener_compras,
arrancar, detener) exigen OK EXPLICITO del usuario. Se aplica en DOS capas:
en el MCP del despacho (antes de llamar al wrapper) y en el Manager (antes de
delegar). Sin OK -> PermissionError, nunca se llega al exchange.
"""
from __future__ import annotations

import os
import time

from .wrapper import TOOLS_EJECUCION

# Ventana de cache de la comprobacion de dry_run (segundos). Evita una llamada
# REST por operacion sin dejar de detectar un cambio de modo del bot.
DRY_RUN_TTL = float(os.getenv("DRY_RUN_TTL", "30"))

# Autorizacion explicita para operar en LIVE. Solo el operador humano la pone,
# y nunca desde una tool: es una variable de entorno del proceso.
PERMITIR_LIVE = os.getenv("PERMITIR_LIVE", "").lower() in ("1", "true", "si")

_cache_dry: dict[int, tuple[float, bool, str]] = {}


def requiere_ok(tool_name: str) -> bool:
    """True si la tool es de ejecucion (exige OK del usuario)."""
    return tool_name in TOOLS_EJECUCION


def autorizar(tool_name: str, ok_usuario: bool) -> None:
    """Valida el OK para una tool de ejecucion. Lanza PermissionError si falta.

    Se llama SIEMPRE antes de invocar una tool de escritura. Doble capa:
    el agente y el Manager la invocan por separado.
    """
    if requiere_ok(tool_name) and not ok_usuario:
        raise PermissionError(
            f"'{tool_name}' exige OK explicito del usuario (constitution III). "
            "El despacho no ejecuta operaciones sin autorizacion.")


def exigir_dry_run(client) -> None:  # noqa: ANN001
    """Aborta si el bot NO corre en dry_run (regla dura, constitution III).

    Se llama antes de CUALQUIER tool de ejecucion. La comprobacion consulta
    show_config del bot real (no una variable local) y se cachea DRY_RUN_TTL
    segundos. Si el bot esta en live, solo continua cuando el operador humano
    arranco el proceso con PERMITIR_LIVE=1 — un LLM no puede activarlo.

    Fail-closed: si la comprobacion no se puede hacer (bot caido, error REST),
    se bloquea la operacion.
    """
    clave = id(client)
    ahora = time.monotonic()
    cacheado = _cache_dry.get(clave)
    if cacheado and ahora - cacheado[0] < DRY_RUN_TTL:
        dry, msg = cacheado[1], cacheado[2]
    else:
        try:
            dry, msg = client.verificar_dry_run()
        except Exception as e:  # noqa: BLE001
            raise PermissionError(
                "No se pudo verificar dry_run contra el bot "
                f"({type(e).__name__}: {str(e)[:120]}). Operacion bloqueada "
                "por seguridad (fail-closed).") from e
        _cache_dry[clave] = (ahora, dry, msg)

    if not dry and not PERMITIR_LIVE:
        raise PermissionError(
            f"El bot NO esta en dry_run ({msg}). Operar con capital real exige "
            "PERMITIR_LIVE=1 en el entorno del proceso, puesto por el operador "
            "humano (constitution III). Operacion bloqueada.")


def limpiar_cache_dry_run() -> None:
    """Invalida la cache de dry_run (tests y reload de config del bot)."""
    _cache_dry.clear()
