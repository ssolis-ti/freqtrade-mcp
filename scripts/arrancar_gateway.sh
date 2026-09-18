#!/usr/bin/env bash
# Arranca el gateway MCP universal en background (modo SOLO-LECTURA por defecto).
#
# Uso:
#   ./scripts/arrancar_gateway.sh              # solo-lectura (default)
#   ./scripts/arrancar_gateway.sh --escritura  # expone tools de ejecucion (autorizacion)
#
# El gateway queda escuchando en 0.0.0.0:8765 (LAN).

set -euo pipefail

PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$PROYECTO/.venv/Scripts/python.exe"
LOG="$PROYECTO/gateway.log"

unset PYTHONPATH

MODO="solo-lectura"
FLAG=""
if [[ "${1:-}" == "--escritura" ]]; then
  MODO="ESCRITURA (autorizado)"
  FLAG="--permitir-escritura"
fi

echo "[gateway] arrancando en modo $MODO"
echo "[gateway] log: $LOG"

cd "$PROYECTO"
nohup "$PY" servers/gateway_http.py --transport streamable-http $FLAG >> "$LOG" 2>&1 &
echo "[gateway] PID $!"
sleep 3
echo "[gateway] escuchando en http://0.0.0.0:8765/mcp"
echo "[gateway] probar: $PY tools/cliente_gateway.py"
