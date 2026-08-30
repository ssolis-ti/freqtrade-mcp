"""Barrido: verifica que cada bloque responde a una query representativa.

Para cada bloque indexado lanza una consulta en ingles (idioma del corpus) y
reporta hits/no-hits + health. No modifica nada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.retriever import Retriever

# Query representativa por bloque (ingles, terminos del corpus)
QUERIES = {
    "00-index": "freqtrade documentation overview",
    "01-instalacion": "how to install freqtrade with docker",
    "02-configuracion": "configuration file parameters",
    "03-estrategia": "write a strategy with indicators",
    "04-backtesting": "run backtesting with downloaded data",
    "05-hyperopt": "hyperopt loss function optimization",
    "06-freqai": "freqai training model features",
    "07-riesgo-futuros": "stoploss leverage futures trading",
    "08-control": "rest api endpoints control bot",
    "09-datos": "download historical data pairs",
    "10-extensiones": "pairlist handlers",
    "11-operativo": "telegram webhook notifications",
}

ok = 0
for bid, q in QUERIES.items():
    try:
        r = Retriever(bid)
        hits = r.query(q, top_k=1)
        h = r.health()
        status = f"{len(hits)} hit(s) [{hits[0]['score']:.3f}]" if hits else "no-hits"
        print(f"[OK] {bid}: chunks={h['chunk_count']:>4} {status}")
        ok += 1
    except Exception as e:
        print(f"[FAIL] {bid}: {e}")

print(f"\nBarrido: {ok}/{len(QUERIES)} bloques responden")
