"""CLI: indexar uno o todos los bloques documentales.

Uso:
    python tools/index_blocks.py [bloque_id] [--force]

Sin argumento indexa los 12 bloques. Con bloque_id indexa solo ese.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Permitir importar el paquete rag/ desde la raiz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.blocks import all_blocks, get_block  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.indexer import index_block  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexar bloques documentales")
    parser.add_argument("block_id", nargs="?", help="Id del bloque (default: todos)")
    parser.add_argument("--force", action="store_true",
                        help="Reindexar aunque el corpus no haya cambiado")
    args = parser.parse_args()

    blocks = [get_block(args.block_id)] if args.block_id else all_blocks()
    embedder = Embedder()
    t0 = time.time()
    for b in blocks:
        t = time.time()
        try:
            manifest = index_block(b, force=args.force, embedder=embedder)
            mc = manifest["mirror_counts"]
            print(f"[OK] {b.id}: {manifest['chunk_count']} chunks "
                  f"(fuente={mc.get('fuente', 0)}, web={mc.get('web', 0)}), "
                  f"model={manifest['embed_model']}, "
                  f"dim={manifest['dim']}, {time.time()-t:.1f}s")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {b.id}: {e}", file=sys.stderr)
    print(f"Total: {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
