"""Copia LLM_API_KEY desde litellm.env al .env del proyecto (sin imprimirla).

Solo escribe si .env no existe o no tiene LLM_API_KEY. Nunca imprime el valor.
"""
import re
import sys
from pathlib import Path

SRC = Path(r"C:\Users\P0zcl\Desktop\deploys-docker\litellm-deploy\internal\litellm.env")
DST = Path(__file__).resolve().parent.parent / ".env"

if not SRC.exists():
    print("litellm.env no existe; nada que copiar")
    sys.exit(0)

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
