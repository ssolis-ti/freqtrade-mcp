"""Verifica consistencia real del vector store de 02: shape de vectors.npy vs index.json."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from rag.config import RAG_DATA_DIR

for bid in ["02-configuracion", "00-index", "01-instalacion", "03-estrategia"]:
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
