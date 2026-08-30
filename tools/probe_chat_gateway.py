"""Fase 0 feature 002: detalle de la respuesta del gateway (campos y finish_reason)."""
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

if not key:
    print("No master key")
    sys.exit(1)

payload = {
    "model": "deepseek-via-inference",
    "messages": [{"role": "user", "content": "Di exactamente la palabra: funcionando"}],
    "max_tokens": 200,
    "temperature": 0,
}
req = urllib.request.Request(
    f"{BASE}/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read())
        ch = body["choices"][0]
        msg = ch["message"]
        print("finish_reason:", ch.get("finish_reason"))
        print("content:", repr(msg.get("content"))[:200])
        print("campos del message:", list(msg.keys()))
        for k, v in msg.items():
            if k != "content":
                print(f"  {k}: {repr(v)[:120]}")
        print("usage:", body.get("usage"))
except Exception as e:
    print(f"[ERR] {type(e).__name__}: {e}")
