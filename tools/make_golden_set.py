"""Genera el golden set del bloque piloto desde chunks reales del corpus.

Selecciona ~20 chunks representativos (mayor score potencial) y construye una
pregunta a partir de su heading/texto, con el chunk_id como respuesta esperada.
El archivo generado es la base del benchmark (tools/benchmark_rag.py).
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DATA_DIR

BLOCK = "02-configuracion"
OUT = Path(__file__).resolve().parent / "golden_set.json"

chunks = json.loads((RAG_DATA_DIR / BLOCK / "chunks.json").read_text(encoding="utf-8"))
print(f"chunks disponibles: {len(chunks)}")

# Filtrar chunks con heading significativo y texto razonable
cands = [c for c in chunks
         if c["heading"] and 200 < c["char_len"] < 2000
         and not re.match(r"^Table of contents|^## ", c["heading"])]

# Estrategia: elegir chunks de secciones distintas (por heading) para diversidad
seen = set()
selected = []
for c in cands:
    key = c["heading"].lower()
    if key in seen:
        continue
    seen.add(key)
    selected.append(c)
    if len(selected) >= 20:
        break

# Si faltan, completar con los restantes mas largos
if len(selected) < 20:
    for c in cands:
        if c not in selected:
            selected.append(c)
        if len(selected) >= 20:
            break

def make_question(chunk: dict) -> str:
    h = chunk["heading"]
    text = chunk["text"].replace("\n", " ")[:200]
    # Pregunta: usa el heading como tema y un fragmento del texto
    snippet = re.sub(r"\s+", " ", text)[:120]
    return f"Segun la documentacion, que dice sobre {h}? Contexto: {snippet}"

golden = []
for c in selected:
    golden.append({
        "block": BLOCK,
        "query": make_question(c),
        "expected_chunk_id": c["id"],
        "heading": c["heading"],
        "mirror": c["mirror"],
        "path": c["path"],
    })

OUT.write_text(json.dumps(golden, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"golden set escrito: {len(golden)} preguntas -> {OUT}")
for g in golden[:5]:
    print(f"  - {g['query'][:80]}... -> {g['expected_chunk_id'][:12]}")
