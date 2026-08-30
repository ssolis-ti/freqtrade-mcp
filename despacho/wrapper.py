"""Wrapper REST de freqtrade (logica pura, testeable con mocks).

Extraido de prototype/freqtrade-mcp/mcp_server.py: las 19 tools de la REST API
de freqtrade (/api/v1) como metodos de una clase, sin decoradores MCP. Devuelven
dicts (no JSON strings) para ser consumidos por el MCP del despacho o por tests.

Auth: JWT (access ~15 min) con relogin automatico en 401.
Regla dura: NINGUNA tool de ejecucion se llama sin pasar por despacho/permisos.py.
"""
from __future__ import annotations

import os

import httpx

FT_URL = os.getenv("FREQTRADE_URL", "http://127.0.0.1:8080")
FT_USER = os.getenv("FREQTRADE_USER", "Freqtrader")
FT_PASS = os.getenv("FREQTRADE_PASS", "")
FT_DRY_RUN = os.getenv("FREQTRADE_DRY_RUN", "true").lower() == "true"
FT_API = f"{FT_URL}/api/v1"

# Tools de escritura (exigen OK del usuario; ver permisos.py)
TOOLS_EJECUCION = frozenset({
    "entrar", "salir", "vetar", "bloquear",
    "detener_compras", "arrancar", "detener",
})


class FreqtradeClient:
    """Cliente de la REST API de freqtrade (lectura + ejecucion)."""

    def __init__(self, base_url: str | None = None, user: str | None = None,
                 password: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or FT_URL).rstrip("/")
        self.api = f"{self.base_url}/api/v1"
        self.user = user or FT_USER
        self.password = password or FT_PASS
        self._client = httpx.Client(timeout=timeout)
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    # --- Auth ---

    def _headers(self) -> dict:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def _auth(self) -> None:
        r = self._client.post(
            f"{self.api}/token/login",
            auth=(self.user, self.password),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        body = r.json()
        self._access_token = body["access_token"]
        self._refresh_token = body["refresh_token"]

    def _call(self, method: str, path: str, params: dict | None = None,
              body: dict | None = None) -> dict:
        """Llamada REST con relogin automatico en 401."""
        if not self._access_token:
            self._auth()
        url = f"{self.api}/{path.lstrip('/')}"
        try:
            resp = self._client.request(method, url, params=params, json=body,
                                        headers=self._headers())
            resp.raise_for_status()
            return resp.json() if resp.text else {}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._auth()
                resp = self._client.request(method, url, params=params, json=body,
                                            headers=self._headers())
                resp.raise_for_status()
                return resp.json() if resp.text else {}
            raise

    def ping(self) -> dict:
        return self._call("GET", "ping")

    def status(self) -> dict:
        return self._call("GET", "status")

    def balance(self) -> dict:
        return self._call("GET", "balance")

    def profit(self) -> dict:
        return self._call("GET", "profit")

    def performance(self) -> dict:
        return self._call("GET", "performance")

    def available_pairs(self, timeframe: str, stake_currency: str = "USDT") -> dict:
        return self._call("GET", "available_pairs",
                          {"timeframe": timeframe, "stake_currency": stake_currency})

    def pair_candles(self, pair: str, timeframe: str, limit: int = 100) -> dict:
        return self._call("GET", "pair_candles",
                          {"pair": pair, "timeframe": timeframe, "limit": limit})

    def whitelist(self) -> dict:
        return self._call("GET", "whitelist")

    def blacklist(self) -> dict:
        return self._call("GET", "blacklist")

    def logs(self, limit: int = 100) -> dict:
        return self._call("GET", "logs", {"limit": limit})

    def count(self) -> dict:
        return self._call("GET", "count")

    def show_config(self) -> dict:
        return self._call("GET", "show_config")

    # --- Ejecucion (requieren OK del usuario; permisos.py) ---

    def entrar(self, pair: str, side: str = "long", stake_amount: float | None = None,
               leverage: float | None = None, enter_tag: str = "mcp") -> dict:
        body: dict = {"pair": pair, "side": side, "enter_tag": enter_tag}
        if stake_amount is not None:
            body["stake_amount"] = stake_amount
        if leverage is not None:
            body["leverage"] = leverage
        return self._call("POST", "forceenter", body=body)

    def salir(self, trade_id: int, ordertype: str = "market") -> dict:
        return self._call("POST", "forceexit",
                          body={"tradeid": trade_id, "ordertype": ordertype})

    def vetar(self, pairs: list) -> dict:
        return self._call("POST", "blacklist", body={"blacklist": pairs})

    def bloquear(self, pair: str, until: str, reason: str = "",
                 side: str = "*") -> dict:
        return self._call("POST", "locks",
                          body={"pair": pair, "until": until, "reason": reason,
                                "side": side})

    def detener_compras(self) -> dict:
        return self._call("POST", "stopbuy")

    def arrancar(self) -> dict:
        return self._call("POST", "start")

    def detener(self) -> dict:
        return self._call("POST", "stop")

    # --- Utilidad ---

    def verificar_dry_run(self) -> tuple[bool, str]:
        """Confirma via show_config que el bot corre en dry_run (regla dura)."""
        cfg = self.show_config()
        dry = bool(cfg.get("dry_run", False))
        msg = f"dry_run={dry} (state={cfg.get('state', '?')})"
        return dry, msg

    def close(self) -> None:
        self._client.close()
