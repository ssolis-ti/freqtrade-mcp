"""MCP del despacho: manos (wrapper REST) + Manager, con gate de permisos.

Tools de LECTURA (sin OK): bot_status, bot_profit, bot_balance, bot_whitelist,
bot_blacklist, bot_count, bot_logs, bot_show_config, bot_ping.
Tools de EJECUCION (exigen OK del usuario - permisos.autorizar): entrar, salir,
vetar, bloquear, detener_compras, arrancar, detener.
Manager: plan_mision, estado_plan.
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from despacho import cadena, permisos
from despacho.manager import Manager
from despacho.wrapper import FreqtradeClient


def build_despacho_mcp(client: FreqtradeClient | None = None,
                       manager: Manager | None = None) -> FastMCP:
    ft = client or FreqtradeClient()
    mgr = manager or Manager()

    mcp = FastMCP(
        "freq-despacho",
        instructions=(
            "Controlas la REST API de freqtrade (despacho). Regla dura: ninguna "
            "tool de ejecucion (entrar, salir, vetar, bloquear, detener_compras, "
            "arrancar, detener) sin OK explicito del usuario. Solo dry-run."
        ),
    )

    # ---------- Lectura (sin OK) ----------

    @mcp.tool()
    def bot_ping() -> str:
        """Verifica que el bot responde."""
        return json.dumps(ft.ping(), ensure_ascii=False)

    @mcp.tool()
    def bot_status() -> str:
        """Trades abiertos del bot."""
        return json.dumps(ft.status(), ensure_ascii=False)

    @mcp.tool()
    def bot_profit() -> str:
        """Resumen de profit/loss."""
        return json.dumps(ft.profit(), ensure_ascii=False)

    @mcp.tool()
    def bot_balance() -> str:
        """Balance de la cuenta."""
        return json.dumps(ft.balance(), ensure_ascii=False)

    @mcp.tool()
    def bot_whitelist() -> str:
        """Lista blanca de pares."""
        return json.dumps(ft.whitelist(), ensure_ascii=False)

    @mcp.tool()
    def bot_blacklist() -> str:
        """Lista negra de pares."""
        return json.dumps(ft.blacklist(), ensure_ascii=False)

    @mcp.tool()
    def bot_count() -> str:
        """Cantidad de trades abiertos."""
        return json.dumps(ft.count(), ensure_ascii=False)

    @mcp.tool()
    def bot_logs(limit: int = 100) -> str:
        """Ultimos logs del bot."""
        return json.dumps(ft.logs(limit), ensure_ascii=False)

    @mcp.tool()
    def bot_show_config() -> str:
        """Config combinada final del bot (verificar dry_run antes de operar)."""
        return json.dumps(ft.show_config(), ensure_ascii=False)

    # ---------- Ejecucion (gate de permisos) ----------

    def _gate(tool_name: str, ok_usuario: bool) -> None:
        """Doble barrera antes de tocar el exchange: OK del usuario + dry_run.

        `exigir_dry_run` consulta al bot real (show_config) y falla cerrado si
        no se puede comprobar o si el bot esta en live sin PERMITIR_LIVE.
        """
        permisos.autorizar(tool_name, ok_usuario)
        permisos.exigir_dry_run(ft)

    def _ejecutar(tool_name: str, ok_usuario: bool, fn):
        _gate(tool_name, ok_usuario)
        return json.dumps(fn(), ensure_ascii=False)

    @mcp.tool()
    def entrar(pair: str, ok_usuario: bool, side: str = "long",
               stake_amount: float | None = None,
               leverage: float | None = None) -> str:
        """FUERZA ENTRADA. Exige ok_usuario=True (regla dura)."""
        _gate("entrar", ok_usuario)
        return json.dumps(ft.entrar(pair, side, stake_amount, leverage),
                          ensure_ascii=False)

    @mcp.tool()
    def salir(trade_id: int, ok_usuario: bool, ordertype: str = "market") -> str:
        """FUERZA SALIDA. Exige ok_usuario=True (regla dura)."""
        _gate("salir", ok_usuario)
        return json.dumps(ft.salir(trade_id, ordertype), ensure_ascii=False)

    @mcp.tool()
    def vetar(pairs: list, ok_usuario: bool) -> str:
        """Anade pares a la blacklist. Exige ok_usuario=True."""
        _gate("vetar", ok_usuario)
        return json.dumps(ft.vetar(pairs), ensure_ascii=False)

    @mcp.tool()
    def bloquear(pair: str, until: str, ok_usuario: bool,
                 reason: str = "") -> str:
        """Bloquea un par hasta una fecha. Exige ok_usuario=True."""
        _gate("bloquear", ok_usuario)
        return json.dumps(ft.bloquear(pair, until, reason), ensure_ascii=False)

    @mcp.tool()
    def detener_compras(ok_usuario: bool) -> str:
        """Detiene nuevas compras. Exige ok_usuario=True."""
        _gate("detener_compras", ok_usuario)
        return json.dumps(ft.detener_compras(), ensure_ascii=False)

    @mcp.tool()
    def arrancar(ok_usuario: bool) -> str:
        """Arranca el bot. Exige ok_usuario=True."""
        _gate("arrancar", ok_usuario)
        return json.dumps(ft.arrancar(), ensure_ascii=False)

    @mcp.tool()
    def detener(ok_usuario: bool) -> str:
        """Detiene el bot. Exige ok_usuario=True."""
        _gate("detener", ok_usuario)
        return json.dumps(ft.detener(), ensure_ascii=False)

    # ---------- Manager ----------

    @mcp.tool()
    def plan_mision(mision: str) -> str:
        """Descompone una mision en un plan de pasos por dominio."""
        return json.dumps(mgr.plan_mision(mision), ensure_ascii=False)

    @mcp.tool()
    def estado_plan() -> str:
        """Estado del plan actual (pasos, bloqueos, decision dry-run)."""
        return json.dumps(mgr.estado_plan(), ensure_ascii=False)

    # ---------- Cadena ----------

    @mcp.tool()
    def cadena_dry_run(pairs: list, strategy: str = "SampleStrategy",
                       timeframe: str = "1h") -> str:
        """Ejecuta la cadena datos->backtest en dry-run (lectura/validacion)."""
        return json.dumps(cadena.ejecutar_cadena(pairs, strategy, timeframe),
                          ensure_ascii=False)

    return mcp
