"""Diagnostica nvidia-embed en el gateway :4000 (detalle del error, sin exponer keys)."""
import json
import re
import sys
import urllib.error
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

print("key:", bool(key))

for model in ["nvidia-embed", "openai/nvidia/nv-embedqa-mistral-7b-v2"]:
    try:
        req = urllib.request.Request(
            f"{BASE}/v1/embeddings",
            data=json.dumps({"model": model, "input": "test document"}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
            vec = body["data"][0]["embedding"]
            print(f"[OK] {model}: dim={len(vec)}, usage={body.get('usage')}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        print(f"[ERR] {model}: HTTP {e.code} -> {detail}")
    except Exception as e:
        print(f"[ERR] {model}: {type(e).__name__}: {e}")
