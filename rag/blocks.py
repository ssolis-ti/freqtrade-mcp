"""Catalogo de los 12 bloques documentales de freqtrade.

Cada bloque mapea su id a los dos mirrors de documentacion:
  - fuente: docs-freqtrade/<id>/  (markdown del repo, rama develop)
  - web:    docs-freqtrade-web/<id>/  (pagina estable renderizada)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT

DOCS_DIR = ROOT / "docs-freqtrade"
DOCS_WEB_DIR = ROOT / "docs-freqtrade-web"


@dataclass(frozen=True)
class Block:
    """Un bloque documental: identidad + rutas a sus dos mirrors."""

    id: str
    name: str
    docs_dir: Path
    web_dir: Path

    @property
    def rag_dir(self) -> Path:
        return ROOT / "data" / "rag" / self.id

    def md_files(self, mirror: str) -> list[Path]:
        """Lista (ordenada) de archivos .md del bloque en el mirror dado."""
        base = self.docs_dir if mirror == "fuente" else self.web_dir
        if not base.exists():
            return []
        return sorted(p for p in base.rglob("*.md") if p.is_file())


def _b(block_id: str, name: str) -> Block:
    return Block(id=block_id, name=name,
                 docs_dir=DOCS_DIR / block_id, web_dir=DOCS_WEB_DIR / block_id)


BLOCKS: tuple[Block, ...] = (
    _b("00-index", "Indice"),
    _b("01-instalacion", "Instalacion"),
    _b("02-configuracion", "Configuracion"),
    _b("03-estrategia", "Estrategia"),
    _b("04-backtesting", "Backtesting y analisis"),
    _b("05-hyperopt", "Hyperopt"),
    _b("06-freqai", "FreqAI"),
    _b("07-riesgo-futuros", "Riesgo y futuros"),
    _b("08-control", "Control (API/UI)"),
    _b("09-datos", "Datos y utilidades"),
    _b("10-extensiones", "Extensiones"),
    _b("11-operativo", "Operativo"),
)

_BY_ID: dict[str, Block] = {b.id: b for b in BLOCKS}


def get_block(block_id: str) -> Block:
    """Devuelve un bloque por id; KeyError si no existe."""
    return _BY_ID[block_id]


def all_blocks() -> list[Block]:
    return list(BLOCKS)
