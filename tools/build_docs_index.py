#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_docs_index.py — Regenera README.md índice de un mirror de docs por bloques."""
import os
import sys

BLOCKS_ORDER = ["00-index", "01-instalacion", "02-configuracion", "03-estrategia",
                "04-backtesting", "05-hyperopt", "06-freqai", "07-riesgo-futuros",
                "08-control", "09-datos", "10-extensiones", "11-operativo"]
TITLES = {
    "00-index": "Índice",
    "01-instalacion": "Instalación / Infra",
    "02-configuracion": "Configuración",
    "03-estrategia": "Estrategia",
    "04-backtesting": "Backtesting / Validación",
    "05-hyperopt": "Hiperoptimización",
    "06-freqai": "FreqAI (ML) — 7 agentes",
    "07-riesgo-futuros": "Riesgo / Futuros",
    "08-control": "Control / UI",
    "09-datos": "Datos / Utilidades / Análisis",
    "10-extensiones": "Extensiones / Plugins",
    "11-operativo": "Operativo / FAQ / Dev",
}


def build(root: str) -> str:
    lines = [f"# {os.path.basename(root.rstrip(os.sep))} — índice", ""]
    total = 0
    total_chars = 0
    for folder in BLOCKS_ORDER:
        fp = os.path.join(root, folder)
        if not os.path.isdir(fp):
            continue
        lines.append(f"## {folder} — {TITLES.get(folder, folder)}")
        lines.append("")
        for fn in sorted(os.listdir(fp)):
            if not fn.endswith(".md") or fn == "README.md":
                continue
            p = os.path.join(fp, fn)
            size = os.path.getsize(p)
            total += 1
            total_chars += size
            lines.append(f"- [`{fn}`]({folder}/{fn}) — {size:,} bytes")
        lines.append("")
    lines.append(f"---\n*{total} archivos, {total_chars:,} bytes.*")
    return "\n".join(lines)


if __name__ == "__main__":
    for root in sys.argv[1:]:
        idx = build(root)
        out = os.path.join(root, "README.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(idx)
        print(f"[OK] {out} ({len(idx):,} chars)")
