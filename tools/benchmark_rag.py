"""Benchmark de calidad del RAG: recall@1/@3, MRR y aislamiento.

Uso:
    python tools/benchmark_rag.py <bloque_id> [--top-k 3]

Carga el golden set del bloque, consulta el RAG y reporta metricas.
Escribe el reporte en data/benchmark/<bloque>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DATA_DIR
from rag.embeddings import Embedder
from rag.retriever import Retriever


def _hits_contain(hits: list[dict], expected_id: str) -> tuple[bool, int]:
    for i, h in enumerate(hits):
        if h["chunk_id"] == expected_id:
            return True, i
    return False, -1


def run_benchmark(block_id: str, top_k: int = 3) -> dict:
    golden_path = Path(__file__).resolve().parent / "golden_set.json"
    if not golden_path.exists():
        raise FileNotFoundError("golden_set.json no existe; corre tools/make_golden_set.py")
    items = json.loads(golden_path.read_text(encoding="utf-8"))
    items = [g for g in items if g["block"] == block_id]

    embedder = Embedder(base_url="http://127.0.0.1:9", model="benchmark-local")
    r = Retriever(block_id, embedder=embedder)

    rec1 = rec3 = 0
    mrr_sum = 0.0
    detalle = []
    for g in items:
        hits = r.query(g["query"], top_k=top_k)
        found, rank = _hits_contain(hits, g["expected_chunk_id"])
        if found:
            if rank == 0:
                rec1 += 1
            rec3 += 1
            mrr_sum += 1.0 / (rank + 1)
        detalle.append({
            "query": g["query"][:90],
            "expected": g["expected_chunk_id"][:12],
            "found": found,
            "rank": rank if found else None,
            "top_score": hits[0]["score"] if hits else None,
        })

    n = len(items)
    metrics = {
        "block": block_id,
        "top_k": top_k,
        "n_preguntas": n,
        "recall@1": round(rec1 / n, 3) if n else 0.0,
        "recall@3": round(rec3 / n, 3) if n else 0.0,
        "mrr": round(mrr_sum / n, 3) if n else 0.0,
        "embed_model": r.index.get("embed_model"),
        "detalle": detalle,
    }

    out = RAG_DATA_DIR.parent / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{block_id}.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("block_id")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    t0 = time.time()
    m = run_benchmark(args.block_id, args.top_k)
    print(f"Benchmark {m['block']} ({m['n_preguntas']} preguntas, top-{m['top_k']}):")
    print(f"  recall@1 = {m['recall@1']}")
    print(f"  recall@3 = {m['recall@3']}")
    print(f"  MRR      = {m['mrr']}")
    print(f"  model    = {m['embed_model']}")
    print(f"  tiempo   = {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
