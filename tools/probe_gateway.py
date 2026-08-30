"""Prueba el gateway :4000 con la master key de litellm.env.

Reporta SOLO existencia/estado (modelos LLM y de embeddings disponibles),
nunca imprime valores de keys.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\P0zcl\Desktop\deploys-docker\litellm-deploy\internal\litellm.env")
BASE = "http://localhost:4000"

key = None
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^LITELLM_MASTER_KEY=(.*)$", line)
        if m:
            key = m.group(1).strip().strip('"').strip("'")
            break

print("master key encontrada:", bool(key))
if not key:
    sys.exit(1)


def get(path):
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


try:
    models = get("/v1/models").get("data", [])
    ids = sorted(m.get("id", "") for m in models)
    print(f"modelos en gateway: {len(ids)}")
    print("  LLM:", [i for i in ids if "embed" not in i.lower()][:20])
    print("  EMBEDDINGS:", [i for i in ids if "embed" in i.lower()])
except Exception as e:
    print("ERR /v1/models:", type(e).__name__, e)

# Probe directo de embeddings si hay modelo candidato
try:
    models = get("/v1/models").get("data", [])
    emb = [m.get("id") for m in models if "embed" in m.get("id", "").lower()]
    if emb:
        req = urllib.request.Request(
            f"{BASE}/v1/embeddings",
            data=json.dumps({"model": emb[0], "input": "test"}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            vec = body["data"][0]["embedding"]
            print(f"embeddings OK con {emb[0]}: dim={len(vec)}")
    else:
        print("No hay modelo de embeddings configurado en el gateway")
except Exception as e:
    print("ERR probe embeddings:", type(e).__name__, e)
