"""Demo: un LLM 've y entiende' la doc de freqtrade via el agente RAG."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.agent import AgenteLLM

# Bloque 04 (local-hash consistente) para que la demo no dependa del rate
# limit de Gemini. Con 02 (Gemini) funciona igual cuando la cuota se recupera.
a = AgenteLLM("04-backtesting")

preguntas = [
    "How do I run a backtest with downloaded data?",
    "What does backtesting require to work?",
]

for q in preguntas:
    r = a.responder(q, top_k=3)
    print("=" * 70)
    print(f"PREGUNTA: {q}")
    print(f"estado: {r['estado']}")
    print(f"RESPUESTA: {r['respuesta'][:500]}")
    if r["citas"]:
        print("CITAS:")
        for c in r["citas"]:
            print(f"  [{c['score']}] {c['mirror']} {c['path']} - {c['heading']}")
