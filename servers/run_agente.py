"""Entrypoint: levanta el MCP del AGENTE LLM de un bloque en stdio.

Uso:
    python servers/run_agente.py 02-configuracion

El bloque debe estar indexado primero:
    python tools/index_blocks.py 02-configuracion
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_mcp import build_agent_mcp  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python servers/run_agente.py <bloque_id>", file=sys.stderr)
        return 2
    block_id = sys.argv[1]
    try:
        mcp = build_agent_mcp(block_id)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
