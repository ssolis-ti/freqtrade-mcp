#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_docs_web.py — Mirror de la página oficial de freqtrade (freqtrade.io/en/stable/),
versión renderizada (Material for MkDocs), organizada por los mismos bloques
documentales que docs-freqtrade/ (el Markdown fuente del repo).

El capítulo = dominio de un agente. Aquí capturamos la versión ESTABLE PUBLICADA,
tal como la ve un humano (admonitions, tablas renderizadas, admonitions Material).

Uso:  python fetch_docs_web.py [--base https://www.freqtrade.io/en/stable] [--out docs-freqtrade-web]
"""
import argparse
import os
import re
import sys
import time
import urllib.request
import urllib.error

try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
except ImportError:
    print("Faltan dependencias. Instalar: pip install beautifulsoup4 markdownify")
    sys.exit(1)

BASE_DEFAULT = "https://www.freqtrade.io/en/stable"

# Mismos bloques que fetch_docs.py
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


def fetch_html(url: str, retries: int = 3) -> str:
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            if e.code in (429, 503):
                wait = 15 * (i + 1)
                print(f"  [retry {i+1}] {e.code} -> sleep {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"  [HTTP {e.code}] {url}", flush=True)
            return ""
        except Exception as e:
            if i == retries - 1:
                print(f"  [ERROR] {url}: {e}", flush=True)
                return ""
            time.sleep(5)
    return ""


def extract_article(html: str, base_url: str) -> str:
    """Extrae <article class='md-content__inner md-typeset'> (Material for MkDocs)
    y lo convierte a Markdown limpio."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Localizar el artículo principal
    article = soup.find("article", class_="md-content__inner")
    if not article:
        article = soup.find("article")
    if not article:
        # fallback: body
        article = soup.body
    if not article:
        return ""

    # 2. Quitar elementos de navegación/desechables dentro del artículo
    for sel in ["script", "style", "noscript", "button", "nav",
                ".md-content__button", ".headerlink", "footer", "aside"]:
        for el in article.select(sel):
            el.decompose()

    # 3. Admonitions Material -> blockquotes con etiqueta
    #    <div class="admonition warning"><p class="admonition-title">Warning</p>...
    for ad in article.select("div.admonition"):
        title_el = ad.select_one(".admonition-title")
        label = title_el.get_text(strip=True) if title_el else "NOTE"
        if title_el:
            title_el.decompose()
        new_block = soup.new_tag("blockquote")
        lab = soup.new_tag("p")
        b = soup.new_tag("strong")
        b.string = f"📌 {label}"
        lab.append(b)
        new_block.append(lab)
        for child in list(ad.children):
            if child is not None:
                new_block.append(child.extract())
        ad.replace_with(new_block)

    # 4. Imágenes relativas -> absolutas
    for img in article.find_all("img"):
        src = img.get("src", "")
        if src.startswith("/"):
            img["src"] = base_url.rstrip("/") + src
        elif src and not src.startswith("http"):
            img["src"] = base_url.rstrip("/") + "/" + src.lstrip("./")

    # 5. Links relativos -> absolutos
    for a in article.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") and not href.startswith("//"):
            a["href"] = base_url.rstrip("/") + href

    # 6. Tablas: añadir saltos de línea que markdownify respete
    for tbl in article.select("table"):
        tbl.insert_before("\n")
        tbl.insert_after("\n")

    # 7. Convertir a Markdown
    text = md(str(article), heading_style="ATX", bullets="-", strip=["span"])
    # limpiar espacios de ancho cero y ruido de anclas
    text = re.sub(r"\[​\]\(#[^)]*\)", "", text)
    text = text.replace("\u200b", "").replace("\u200a", "").replace("\ufeff", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--out", default="docs-freqtrade-web")
    args = ap.parse_args()

    out_root = os.path.abspath(args.out)
    os.makedirs(out_root, exist_ok=True)

    stats = {"ok": 0, "empty": 0}
    index_lines = [
        "# Documentación oficial de Freqtrade — página web (mirror local)",
        "",
        f"> Fuente: `{args.base}/` (Material for MkDocs, versión estable publicada)",
        f"> Descargado: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Versión RENDERIZADA (lo que ve un humano). El Markdown fuente está en `docs-freqtrade/`.",
        "Cada bloque = dominio documental de un agente.",
        "",
    ]

    for folder, title, chapters in BLOCKS:
        folder_path = os.path.join(out_root, folder)
        os.makedirs(folder_path, exist_ok=True)
        index_lines.append(f"## {folder} — {title}")
        index_lines.append("")
        for ch in chapters:
            url = f"{args.base.rstrip('/')}/{ch}/"
            html = fetch_html(url)
            if not html:
                stats["empty"] += 1
                index_lines.append(f"- [ ] `{ch}.md` — **no descargado**")
                print(f"  [VACÍO] {ch}", flush=True)
                continue
            md_text = extract_article(html, args.base)
            if not md_text:
                stats["empty"] += 1
                index_lines.append(f"- [ ] `{ch}.md` — artículo vacío")
                print(f"  [VACÍO-ART] {ch}", flush=True)
                continue
            out_file = os.path.join(folder_path, f"{ch}.md")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(f"<!-- Fuente: {url} -->\n\n" + md_text)
            stats["ok"] += 1
            index_lines.append(f"- [x] [`{ch}.md`]({folder}/{ch}.md) — {len(md_text):,} chars")
            print(f"  [OK] {ch} -> {folder}/{ch}.md ({len(md_text):,} chars)", flush=True)
            time.sleep(0.6)  # amable con el sitio

    with open(os.path.join(out_root, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"\n=== Resumen: {stats['ok']} ok, {stats['empty']} vacíos ===")
    print(f"Índice: {os.path.join(out_root, 'README.md')}")


if __name__ == "__main__":
    main()
