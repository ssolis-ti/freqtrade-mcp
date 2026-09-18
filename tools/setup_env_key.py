"""Copia LLM_API_KEY desde el entorno de LiteLLM al .env del proyecto (sin imprimirla).

La ruta del litellm.env se toma de la variable LITELLM_ENV_PATH (o se autodetecta
en ubicaciones comunes). Asi el script es portable: no depende de rutas de un usuario.

Solo escribe si .env no existe o no tiene LLM_API_KEY. Nunca imprime el valor.
"""
import os
import re
import sys
from pathlib import Path

# Candidatos: variable de entorno primero, luego rutas relativas comunes
CANDIDATOS = [
    os.getenv("LITELLM_ENV_PATH", ""),
    "litellm.env",
    "../litellm-deploy/internal/litellm.env",
    "../deploys-docker/litellm-deploy/internal/litellm.env",
    "~/litellm-deploy/internal/litellm.env",
]

DST = Path(__file__).resolve().parent.parent / ".env"

SRC = None
for cand in CANDIDATOS:
    if not cand:
        continue
    p = Path(cand).expanduser()
    if p.exists():
        SRC = p
        break

if SRC is None:
    print("No se encontro litellm.env. Define LITELLM_ENV_PATH=/ruta/a/litellm.env")
    sys.exit(1)

key = None
for line in SRC.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^LITELLM_MASTER_KEY=(.*)$", line)
    if m:
        key = m.group(1).strip().strip('"').strip("'")
        break

if not key:
    print("LITELLM_MASTER_KEY vacia; nada que copiar")
    sys.exit(0)

dst_text = DST.read_text(encoding="utf-8") if DST.exists() else ""
if "LLM_API_KEY=" in dst_text:
    print(".env ya tiene LLM_API_KEY; sin cambios")
    sys.exit(0)

block = "LLM_API_KEY=" + key
if dst_text and not dst_text.endswith("\n"):
    dst_text += "\n"
DST.write_text(dst_text + block + "\n", encoding="utf-8")
print(f".env actualizado (LLM_API_KEY escrita; largo key={len(key)} chars)")
