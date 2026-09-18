"""Gateway MCP universal: una sola superficie HTTP para cualquier agente o LLM.

Concentra en un unico proceso y endpoint las tools de:
  - Base de conocimiento freqtrade (RAG de los 12 bloques documentales)
  - Operacion (despacho: wrapper REST de freqtrade)
  - Grafo de conocimiento (graphify: god_nodes, query, shortest_path, ...)

Transporte: Streamable HTTP (spec MCP 2025-03-26) sobre 127.0.0.1:8765 por defecto.
Auth: Bearer API key obligatoria (GATEWAY_API_KEY). Sin key solo se permite
escuchar en loopback; exponer el gateway a la LAN sin key esta prohibido.
Seguridad: MODO SOLO-LECTURA por defecto. Las tools de escritura solo se exponen
si el gateway arranca con --permitir-escritura (confirmacion explicita del usuario).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Permitir importar rag/, despacho/ y servers/ desde la raiz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from rag.agent import AgenteLLM
from rag.blocks import all_blocks
from rag.retriever import Retriever

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8765"))
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")

# Nombres de tool seguros (sin guiones) por bloque
_ALIAS = {
    "00-index": "index",
    "01-instalacion": "instalacion",
    "02-configuracion": "configuracion",
    "03-estrategia": "estrategia",
    "04-backtesting": "backtesting",
    "05-hyperopt": "hyperopt",
    "06-freqai": "freqai",
    "07-riesgo-futuros": "riesgo_futuros",
    "08-control": "control",
    "09-datos": "datos",
    "10-extensiones": "extensiones",
    "11-operativo": "operativo",
}


def build_gateway(permitir_escritura: bool = False,
                  ft_client=None, manager=None):  # noqa: ANN001
    """Construye el FastMCP del gateway universal.

    Args:
        permitir_escritura: si False (default) las tools de ejecucion NO se exponen.
        ft_client: cliente de freqtrade inyectable (tests).
        manager: Manager inyectable (tests).
    """
    mcp = FastMCP(
        "freqtrade-universal",
        instructions=(
            "Base de conocimiento y operacion de freqtrade. "
            "Tools 'docs_*': base de conocimiento (RAG de los 12 bloques documentales "
            "oficiales). Tools 'bot_*': estado y lectura del bot. "
            "Tools 'grafo_*': conocimiento estructural del codigo. "
            "Las tools de escritura (entrar/salir/vetar/...) solo existen si el "
            "gateway fue autorizado en modo escritura por el operador humano."
        ),
        host=GATEWAY_HOST,
        port=GATEWAY_PORT,
    )

    # ------------------------------------------------------------------
    # 1. BASE DE CONOCIMIENTO (RAG por bloque) — lectura, sin gate
    # ------------------------------------------------------------------
    _agentes: dict = {}
    _retrievers: dict = {}

    def _agente(block_id: str) -> AgenteLLM:
        if block_id not in _agentes:
            _agentes[block_id] = AgenteLLM(block_id)
        return _agentes[block_id]

    def _retriever(block_id: str) -> Retriever:
        if block_id not in _retrievers:
            _retrievers[block_id] = Retriever(block_id)
        return _retrievers[block_id]

    @mcp.tool()
    def docs_listar_bloques() -> str:
        """Lista los 12 bloques documentales de freqtrade disponibles como conocimiento."""
        out = []
        for b in all_blocks():
            out.append({"id": b.id, "alias": _ALIAS.get(b.id, b.id), "nombre": b.name})
        return json.dumps(out, ensure_ascii=False)

    @mcp.tool()
    def docs_health(bloque: str) -> str:
        """Estado del indice RAG de un bloque (chunks, modelo de embeddings, dimension)."""
        bid = _resolver_bloque(bloque)
        return json.dumps(_retriever(bid).health(), ensure_ascii=False)

    @mcp.tool()
    def docs_buscar(bloque: str, query: str, top_k: int = 3) -> str:
        """Recuperacion pura (chunks con score y fuente) en UN bloque documental."""
        bid = _resolver_bloque(bloque)
        hits = _retriever(bid).query(query, top_k=top_k)
        return json.dumps(hits, ensure_ascii=False)

    @mcp.tool()
    def docs_preguntar(bloque: str, query: str, top_k: int = 3) -> str:
        """Responde una pregunta usando SOLO la documentacion de un bloque, con citas."""
        bid = _resolver_bloque(bloque)
        return json.dumps(_agente(bid).responder(query, top_k=top_k), ensure_ascii=False)

    @mcp.tool()
    def docs_buscar_global(query: str, top_k_por_bloque: int = 2) -> str:
        """Busca en los 12 bloques a la vez (util si no sabes donde esta la respuesta)."""
        resultados = {}
        for b in all_blocks():
            try:
                hits = _retriever(b.id).query(query, top_k=top_k_por_bloque)
                if hits:
                    resultados[b.id] = hits
            except Exception as e:  # noqa: BLE001
                resultados[b.id] = {"error": str(e)[:120]}
        return json.dumps(resultados, ensure_ascii=False)

    def _resolver_bloque(valor: str) -> str:
        """Acepta id ('02-configuracion') o alias ('configuracion')."""
        v = (valor or "").strip()
        if v in _ALIAS:
            return v
        for bid, alias in _ALIAS.items():
            if alias == v:
                return bid
        # buscar por sufijo/nombre
        for b in all_blocks():
            if v.lower() in b.id.lower() or v.lower() in b.name.lower():
                return b.id
        raise ValueError(
            f"Bloque '{valor}' no reconocido. Usa docs_listar_bloques() para ver los ids.")

    # ------------------------------------------------------------------
    # 2. OPERACION (despacho) — lectura siempre; escritura solo con flag
    # ------------------------------------------------------------------
    def _ft():  # noqa: ANN202
        nonlocal ft_client
        if ft_client is None:
            from despacho.wrapper import FreqtradeClient
            ft_client = FreqtradeClient()
        return ft_client

    @mcp.tool()
    def bot_ping() -> str:
        """Verifica que el bot de freqtrade responde."""
        return json.dumps(_ft().ping(), ensure_ascii=False)

    @mcp.tool()
    def bot_status() -> str:
        """Trades abiertos del bot."""
        return json.dumps(_ft().status(), ensure_ascii=False)

    @mcp.tool()
    def bot_profit() -> str:
        """Resumen de profit/loss del bot."""
        return json.dumps(_ft().profit(), ensure_ascii=False)

    @mcp.tool()
    def bot_balance() -> str:
        """Balance de la cuenta del exchange."""
        return json.dumps(_ft().balance(), ensure_ascii=False)

    @mcp.tool()
    def bot_whitelist() -> str:
        """Lista blanca de pares del bot."""
        return json.dumps(_ft().whitelist(), ensure_ascii=False)

    @mcp.tool()
    def bot_blacklist() -> str:
        """Lista negra de pares del bot."""
        return json.dumps(_ft().blacklist(), ensure_ascii=False)

    @mcp.tool()
    def bot_count() -> str:
        """Cantidad de trades abiertos."""
        return json.dumps(_ft().count(), ensure_ascii=False)

    @mcp.tool()
    def bot_logs(limit: int = 100) -> str:
        """Ultimos logs del bot."""
        return json.dumps(_ft().logs(limit), ensure_ascii=False)

    @mcp.tool()
    def bot_show_config() -> str:
        """Config combinada final del bot (usar para verificar dry_run antes de operar)."""
        return json.dumps(_ft().show_config(), ensure_ascii=False)

    @mcp.tool()
    def plan_mision(mision: str) -> str:
        """Descompone una mision de trading en un plan de pasos por dominio documental."""
        from despacho.manager import Manager
        mgr = manager or Manager()
        return json.dumps(mgr.plan_mision(mision), ensure_ascii=False)

    @mcp.tool()
    def cadena_dry_run(pairs: str, strategy: str = "SampleStrategy",
                       timeframe: str = "1h") -> str:
        """Cadena de validacion dry-run (datos -> backtest). pairs separados por coma."""
        from despacho import cadena
        lista = [p.strip() for p in pairs.split(",") if p.strip()]
        return json.dumps(cadena.ejecutar_cadena(lista, strategy, timeframe),
                          ensure_ascii=False)

    # ------------------------------------------------------------------
    # 3. GRAFO DE CONOCIMIENTO (graphify)
    # ------------------------------------------------------------------
    @mcp.tool()
    def grafo_estadisticas() -> str:
        """Estadisticas del grafo de conocimiento del codigo (nodos, edges, comunidades)."""
        return json.dumps(_grafo_stats(), ensure_ascii=False)

    @mcp.tool()
    def grafo_god_nodes(top_n: int = 10) -> str:
        """Conceptos mas conectados del codigo (las abstracciones centrales)."""
        g = _cargar_grafo()
        if not g:
            return json.dumps({"aviso": "grafo no generado; corre: graphify extract . --code-only"})
        # Formato networkx: los edges estan en 'links' (source/target)
        grado: dict = {}
        for e in g.get("links", g.get("edges", [])):
            for lado in ("source", "target"):
                n = e.get(lado)
                if n:
                    grado[n] = grado.get(n, 0) + 1
        # mapear id -> label
        etiquetas = {n.get("id"): n.get("label") or n.get("id")
                     for n in g.get("nodes", [])}
        top = sorted(grado.items(), key=lambda kv: -kv[1])[:max(1, top_n)]
        return json.dumps(
            [{"nodo": etiquetas.get(k, k), "id": k, "edges": v} for k, v in top],
            ensure_ascii=False)

    @mcp.tool()
    def grafo_consultar(question: str) -> str:
        """Busca en el grafo del codigo nodos relacionados con una pregunta (BFS textual)."""
        g = _cargar_grafo()
        if not g:
            return json.dumps({"aviso": "grafo no generado; corre: graphify extract . --code-only"})
        terms = [t for t in question.lower().replace("?", "").split() if len(t) > 3]
        hits = []
        for n in g.get("nodes", []):
            etiqueta = str(n.get("label") or n.get("id") or "")
            bajo = etiqueta.lower()
            score = sum(1 for t in terms if t in bajo)
            if score:
                hits.append({"nodo": etiqueta, "tipo": n.get("type"),
                             "coincidencias": score})
        hits.sort(key=lambda h: -h["coincidencias"])
        return json.dumps(hits[:15], ensure_ascii=False)

    def _grafo_path() -> str:
        from rag.config import ROOT
        return str(ROOT / "graphify-out" / "graph.json")

    def _cargar_grafo() -> dict:
        try:
            with open(_grafo_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def _grafo_stats() -> dict:
        g = _cargar_grafo()
        if not g:
            return {"aviso": "grafo no generado; corre: graphify extract . --code-only"}
        comunidades = {n.get("community") for n in g.get("nodes", [])
                       if n.get("community") is not None}
        return {"nodos": len(g.get("nodes", [])),
                "edges": len(g.get("links", g.get("edges", []))),
                "comunidades": len(comunidades),
                "ruta": _grafo_path()}

    # ------------------------------------------------------------------
    # 4. ESCRITURA — solo si el operador autorizo explicitamente
    # ------------------------------------------------------------------
    if permitir_escritura:
        from despacho import permisos

        def _gate_escritura(tool_name: str) -> None:
            """Barrera de escritura del gateway.

            La autorizacion humana aqui es el flag --permitir-escritura del
            proceso (un LLM no puede activarlo). Encima se exige que el bot
            este en dry_run, comprobado contra el bot real y fail-closed.
            """
            permisos.autorizar(tool_name, True)
            permisos.exigir_dry_run(_ft())

        @mcp.tool()
        def entrar(pair: str, side: str = "long",
                   stake_amount: float | None = None,
                   leverage: float | None = None) -> str:
            """FUERZA ENTRADA (gateway en modo escritura autorizado)."""
            _gate_escritura("entrar")
            return json.dumps(_ft().entrar(pair, side, stake_amount, leverage),
                              ensure_ascii=False)

        @mcp.tool()
        def salir(trade_id: int, ordertype: str = "market") -> str:
            """FUERZA SALIDA (gateway en modo escritura autorizado)."""
            _gate_escritura("salir")
            return json.dumps(_ft().salir(trade_id, ordertype), ensure_ascii=False)

        @mcp.tool()
        def vetar(pairs: str) -> str:
            """Anade pares a la blacklist (separados por coma)."""
            _gate_escritura("vetar")
            lista = [p.strip() for p in pairs.split(",") if p.strip()]
            return json.dumps(_ft().vetar(lista), ensure_ascii=False)

        @mcp.tool()
        def detener_compras() -> str:
            """Detiene nuevas compras."""
            _gate_escritura("detener_compras")
            return json.dumps(_ft().detener_compras(), ensure_ascii=False)

    return mcp


def _es_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")


class BearerAuthMiddleware:
    """Middleware ASGI: exige `Authorization: Bearer <GATEWAY_API_KEY>`.

    Se aplica a TODA peticion HTTP del gateway. La comparacion es de tiempo
    constante para no filtrar el prefijo de la key por temporizacion.
    """

    def __init__(self, app, api_key: str) -> None:  # noqa: ANN001
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):  # noqa: ANN001
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        import hmac

        cabeceras = {k.decode().lower(): v.decode()
                     for k, v in scope.get("headers", [])}
        entregado = cabeceras.get("authorization", "")
        prefijo = "Bearer "
        token = entregado[len(prefijo):] if entregado.startswith(prefijo) else ""
        if not hmac.compare_digest(token, self.api_key):
            cuerpo = json.dumps({"error": "unauthorized"}).encode()
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"www-authenticate", b"Bearer")]})
            await send({"type": "http.response.body", "body": cuerpo})
            return
        await self.app(scope, receive, send)


def construir_app(mcp, api_key: str):  # noqa: ANN001
    """App ASGI del gateway, con auth Bearer si hay key configurada."""
    app = mcp.streamable_http_app()
    if api_key:
        return BearerAuthMiddleware(app, api_key)
    return app


def main() -> int:  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Gateway MCP universal de freqtrade")
    parser.add_argument("--permitir-escritura", action="store_true",
                        help="Expone las tools de ejecucion (requiere autorizacion humana)")
    parser.add_argument("--transport", default="streamable-http",
                        choices=["streamable-http", "stdio"])
    parser.add_argument("--host", default=GATEWAY_HOST,
                        help="Interfaz de escucha (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=GATEWAY_PORT)
    args = parser.parse_args()

    # Regla dura: no exponer fuera de loopback sin autenticacion.
    if args.transport == "streamable-http" and not _es_loopback(args.host)             and not GATEWAY_API_KEY:
        print("[gateway] ABORTADO: escuchar en "
              f"{args.host} sin GATEWAY_API_KEY expondria todas las tools a la "
              "red sin autenticacion. Define GATEWAY_API_KEY en .env o usa "
              "--host 127.0.0.1.", file=sys.stderr)
        return 2

    mcp = build_gateway(permitir_escritura=args.permitir_escritura)
    modo = "ESCRITURA" if args.permitir_escritura else "SOLO-LECTURA"
    auth = "con auth Bearer" if GATEWAY_API_KEY else "SIN auth (solo loopback)"

    if args.transport == "stdio":
        print(f"[gateway] modo {modo} | stdio", file=sys.stderr)
        mcp.run(transport="stdio")
        return 0

    import uvicorn

    print(f"[gateway] modo {modo} | {auth} | "
          f"http://{args.host}:{args.port}/mcp", file=sys.stderr)
    uvicorn.run(construir_app(mcp, GATEWAY_API_KEY),
                host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
