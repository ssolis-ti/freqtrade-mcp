"""Entrypoint: levanta el MCP del DESPACHO en stdio.

Uso:
    python servers/run_despacho.py

Requiere un freqtrade con REST habilitada (ver .env: FREQTRADE_URL/USER/PASS).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from despacho_mcp import build_despacho_mcp  # noqa: E402


def main() -> int:
    try:
        mcp = build_despacho_mcp()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
