"""Mide el costo de contexto del corpus por bloque (chars y tokens estimados).

Justifica la tesis de diseno: el corpus total NO cabe en el contexto de un LLM;
por eso RAG por bloque en vez de cargar la doc en el prompt.
Token estimado = chars / 4 (regla aproximada para ingles tecnico).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.blocks import all_blocks

TOK_PER_CHAR = 0.25  # ~4 chars por token
CTX_128K = 128_000
CTX_200K = 200_000

rows = []
total_chars = 0
for b in all_blocks():
    files = b.md_files("fuente") + b.md_files("web")
    chars = sum(p.stat().st_size for p in files)
    total_chars += chars
    rows.append((b.id, len(files), chars))

print(f"{'bloque':<22} {'archivos':>8} {'chars':>10} {'tokens~':>10}")
print("-" * 54)
for bid, n, c in rows:
    print(f"{bid:<22} {n:>8} {c:>10} {int(c*TOK_PER_CHAR):>10}")

print("-" * 54)
tokens = int(total_chars * TOK_PER_CHAR)
print(f"{'TOTAL':<22} {sum(r[1] for r in rows):>8} {total_chars:>10} {tokens:>10}")
print()
print(f"Contexto 128K tokens: el corpus ocupa {tokens/CTX_128K:.1f}x el contexto")
print(f"Contexto 200K tokens: el corpus ocupa {tokens/CTX_200K:.1f}x el contexto")
print(f"Solo el bloque mas grande (03-estrategia): {int(max(rows,key=lambda r:r[2])[2]*TOK_PER_CHAR)} tokens ~ ({max(rows,key=lambda r:r[2])[2]/CTX_128K:.1%} de 128K)")
