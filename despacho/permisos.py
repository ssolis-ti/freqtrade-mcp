"""Gate de permisos del despacho (regla dura, constitution III).

Las tools de ejecucion (entrar, salir, vetar, bloquear, detener_compras,
arrancar, detener) exigen OK EXPLICITO del usuario. Se aplica en DOS capas:
en el MCP del despacho (antes de llamar al wrapper) y en el Manager (antes de
delegar). Sin OK -> PermissionError, nunca se llega al exchange.
"""
from __future__ import annotations

from .wrapper import TOOLS_EJECUCION


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
