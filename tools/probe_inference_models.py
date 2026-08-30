"""Consulta (solo lectura, sin gasto) si inference.net expone modelos de embeddings.

GET /v1/models no consume tokens. Reporta nombres, nunca valores de key.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\P0zcl\Desktop\deploys-docker\litellm-deploy\internal\litellm.env")

key = None
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^INFERENCE_API_KEY=(.*)$", line)
        if m:
            key = m.group(1).strip().strip('"').strip("'")
            break

print("INFERENCE_API_KEY:", bool(key))
if not key:
    sys.exit(1)

for base in ["https://api.inference.net/v1", "https://api.inference.net"]:
    try:
        req = urllib.request.Request(f"{base}/models",
                                     headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
            ids = [m.get("id", "") for m in body.get("data", [])]
            emb = [i for i in ids if "embed" in i.lower()]
            print(f"[{base}] {len(ids)} modelos; embeddings: {emb[:10]}")
            if emb:
                break
    except Exception as e:
        print(f"[{base}] ERR {type(e).__name__}: {e}")
