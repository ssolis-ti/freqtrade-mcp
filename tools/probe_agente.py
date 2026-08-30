"""Prueba el agente con queries alineadas al corpus (citas reales)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.agent import AgenteLLM

a = AgenteLLM("02-configuracion")

for q in ["What is the purpose of the dry run mode?",
          "How do I set up my exchange API keys?"]:
    r = a.responder(q, top_k=3)
    print("=" * 70)
    print(f"Q: {q}")
    print(f"estado: {r['estado']}")
    print(f"respuesta: {r['respuesta'][:400]}")
    print(f"citas: {len(r['citas'])}")
    for c in r["citas"]:
        print(f"  [{c['score']}] {c['mirror']} {c['path']} - {c['heading']}")
