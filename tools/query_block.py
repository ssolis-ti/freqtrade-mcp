"""CLI: consultar el RAG de un bloque sin pasar por MCP (depuracion).

Uso:
    python tools/query_block.py <bloque_id> "query" [--top-k N] [--min-score X]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.retriever import Retriever  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Consultar RAG de un bloque")
    parser.add_argument("block_id", help="Id del bloque (ej. 02-configuracion)")
    parser.add_argument("query", help="Pregunta en lenguaje natural")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=None)
    args = parser.parse_args()

    try:
        retriever = Retriever(args.block_id)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    hits = retriever.query(args.query, top_k=args.top_k, min_score=args.min_score)
    if not hits:
        print("No-hits: ninguna seccion del bloque supera el umbral de similitud.")
        return 0

    for h in hits:
        print("-" * 72)
        print(f"[{h['score']:.3f}] {h['mirror']} | {h['path']} | {h['heading']}")
        if h.get("heading_path"):
            print(f"  path: {h['heading_path']}")
        print(h["text"][:400])
    print("-" * 72)
    print(f"{len(hits)} hits (model={retriever.index.get('embed_model')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
