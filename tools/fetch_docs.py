#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_docs.py — Descarga la documentación oficial de freqtrade (fuente Markdown
del repo GitHub, rama develop) y la organiza por bloques documentales.

Cada bloque = dominio de un agente (la documentación ES el organigrama).
Fuente: https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/<name>.md

Uso:  python fetch_docs.py [--branch develop] [--out docs-freqtrade]
"""
import argparse
import os
import sys
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/freqtrade/freqtrade/{branch}/docs/{name}.md"

# Bloques documentales: nombre_carpeta -> (título, [capítulos])
BLOCKS = [
    ("00-index", "Índice", ["index"]),
    ("01-instalacion", "Instalación / Infra",
        ["installation", "docker_quickstart", "advanced-setup", "updating"]),
    ("02-configuracion", "Configuración",
        ["configuration"]),
    ("03-estrategia", "Estrategia",
        ["strategy-101", "strategy-advanced", "strategy-customization",
         "strategy-callbacks", "strategy_migration", "trade-object"]),
    ("04-backtesting", "Backtesting / Validación",
        ["backtesting", "advanced-backtesting", "lookahead-analysis", "recursive-analysis"]),
    ("05-hyperopt", "Hiperoptimización",
        ["hyperopt", "advanced-hyperopt"]),
    ("06-freqai", "FreqAI (ML) — 7 agentes",
        ["freqai", "freqai-configuration", "freqai-feature-engineering",
         "freqai-parameter-table", "freqai-running",
         "freqai-reinforcement-learning", "freqai-developers"]),
    ("07-riesgo-futuros", "Riesgo / Futuros",
        ["stoploss", "leverage", "exchanges"]),
    ("08-control", "Control / UI",
        ["rest-api", "freq-ui", "telegram-usage", "webhook-config"]),
    ("09-datos", "Datos / Utilidades / Análisis",
        ["data-download", "data-analysis", "utils", "sql_cheatsheet",
         "plotting", "strategy_analysis_example"]),
    ("10-extensiones", "Extensiones / Plugins",
        ["plugins", "producer-consumer"]),
    ("11-operativo", "Operativo / FAQ / Dev",
        ["bot-basics", "bot-usage", "faq", "deprecated", "developer",
         "advanced-orderflow"]),
]

ALL_CHAPTERS = [c for _, _, chs in BLOCKS for c in chs]


def fetch(url: str, retries: int = 3) -> bytes:
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b""
            if e.code in (429, 503):
                wait = 10 * (i + 1)
                print(f"  [retry {i+1}] {e.code} -> sleep {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"  [HTTP {e.code}] {url}", flush=True)
            return b""
        except Exception as e:
            if i == retries - 1:
                print(f"  [ERROR] {url}: {e}", flush=True)
                return b""
            time.sleep(5)
    return b""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="develop")
    ap.add_argument("--out", default="docs-freqtrade")
    args = ap.parse_args()

    out_root = os.path.abspath(args.out)
    os.makedirs(out_root, exist_ok=True)

    stats = {"ok": 0, "empty": 0, "fail": 0}
    index_lines = ["# Documentación oficial de Freqtrade (mirror local)",
                   "",
                   f"> Fuente: `https://github.com/freqtrade/freqtrade` rama `{args.branch}` → `docs/*.md`",
                   f"> Descargado: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                   "",
                   "Cada bloque = dominio documental de un agente de la oficina.",
                   "El capítulo es la fuente de verdad del agente.",
                   ""]

    for folder, title, chapters in BLOCKS:
        folder_path = os.path.join(out_root, folder)
        os.makedirs(folder_path, exist_ok=True)
        index_lines.append(f"## {folder} — {title}")
        index_lines.append("")
        for ch in chapters:
            url = BASE.format(branch=args.branch, name=ch)
            data = fetch(url)
            if not data:
                stats["fail" if url.endswith(f"{ch}.md") and data is None else "empty"] += 1
                # distinguir 404 (no existe) de fallo real
                index_lines.append(f"- [ ] `{ch}.md` — **no descargado**")
                print(f"  [VACÍO] {ch}", flush=True)
                continue
            out_file = os.path.join(folder_path, f"{ch}.md")
            with open(out_file, "wb") as f:
                f.write(data)
            stats["ok"] += 1
            index_lines.append(f"- [x] [`{ch}.md`]({folder}/{ch}.md) — {len(data):,} bytes")
            print(f"  [OK] {ch} -> {folder}/{ch}.md ({len(data):,} bytes)", flush=True)
            time.sleep(0.4)  # rate limit amable

    with open(os.path.join(out_root, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"\n=== Resumen: {stats['ok']} descargados, {stats['empty']} vacíos/404, {stats['fail']} fallos ===")
    print(f"Índice: {os.path.join(out_root, 'README.md')}")


if __name__ == "__main__":
    main()
