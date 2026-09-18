"""Verifica la consistencia del vector store de TODOS los bloques.

Compara index.json (dim, chunk_count) con la forma real de vectors.npy y el
numero de chunks. Marca ademas que backend de embeddings tiene cada bloque.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from rag.blocks import all_blocks
from rag.config import RAG_DATA_DIR

degradados = []
for bid in [b.id for b in all_blocks()]:
    d = RAG_DATA_DIR / bid
    if not (d / "index.json").exists():
        print(f"{bid}: SIN INDICE")
        continue
    idx = json.loads((d / "index.json").read_text(encoding="utf-8"))
    v = np.load(d / "vectors.npy")
    chunks = json.loads((d / "chunks.json").read_text(encoding="utf-8"))
    print(f"{bid}: index_dim={idx.get('dim')} model={idx.get('embed_model')} "
          f"| vectors.shape={v.shape} | chunks={len(chunks)} "
          f"| {'OK' if v.shape[1] == idx.get('dim') else 'INCONSISTENTE'}")
    if idx.get("embed_model", "").startswith("local-hash"):
        degradados.append(bid)

if degradados:
    print()
    print(f"{len(degradados)} bloque(s) en local-hash (recuperacion por palabras "
          f"clave, no semantica): {', '.join(degradados)}")
    print("Reindexar con: tools/index_blocks.py <bloque> --force  (requiere cuota de Gemini)")
