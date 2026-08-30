"""Chunking de documentacion markdown en unidades de RAG.

Estrategia jerarquica:
  1. Se divide el documento por cabeceras markdown (## / ### / ...).
  2. Cada seccion hereda su heading_path (cadena de cabeceras padre).
  3. Si una seccion supera CHUNK_MAX_CHARS, se subdivide en ventanas por parrafos
     con solape (CHUNK_OVERLAP_CHARS) para no romper el contexto.
  4. El id de cada chunk es determinista: sha1(mirror|path|idx).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .config import CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_MIRROR_FUENTE = "fuente"
_MIRROR_WEB = "web"


@dataclass
class Chunk:
    id: str
    block: str
    mirror: str
    path: str
    heading: str
    heading_path: str
    text: str
    char_len: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_len = len(self.text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "block": self.block,
            "mirror": self.mirror,
            "path": self.path,
            "heading": self.heading,
            "heading_path": self.heading_path,
            "text": self.text,
            "char_len": self.char_len,
        }


def _chunk_id(mirror: str, path: str, idx: int) -> str:
    raw = f"{mirror}|{path}|{idx}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _split_paragraph_windows(text: str, max_chars: int, overlap: int) -> list[str]:
    """Subdivide texto largo en ventanas por parrafos con solape.

    Prefiere cortes en limites de parrafo; si un parrafo aislado es enorme,
    lo parte por lineas. Garantiza que ninguna ventana exceda max_chars.
    """
    if len(text) <= max_chars:
        return [text]

    paras = re.split(r"\n\s*\n", text)
    windows: list[str] = []
    current = ""

    for p in paras:
        # Parrafo gigante: partir por lineas
        if len(p) > max_chars:
            if current:
                windows.append(current)
                current = ""
            lines = p.splitlines()
            buf = ""
            for ln in lines:
                if len(buf) + len(ln) + 1 > max_chars and buf:
                    windows.append(buf)
                    buf = buf[-overlap:] if overlap else ""
                buf = (buf + "\n" + ln).strip() if buf else ln
            if buf:
                windows.append(buf)
            continue

        if not current:
            current = p
        elif len(current) + len(p) + 2 <= max_chars:
            current = f"{current}\n\n{p}"
        else:
            windows.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{p}" if tail else p

    if current:
        windows.append(current)
    return windows


def chunk_markdown(text: str, path: str, mirror: str, block_id: str,
                   max_chars: int | None = None,
                   overlap: int | None = None) -> list[Chunk]:
    """Convierte un documento markdown en chunks de RAG.

    Args:
        text: contenido completo del .md
        path: ruta relativa del archivo dentro del mirror (para el id)
        mirror: "fuente" o "web"
        block_id: id del bloque documental
        max_chars: tamano maximo de chunk (default CHUNK_MAX_CHARS)
        overlap: solape entre ventanas (default CHUNK_OVERLAP_CHARS)

    Returns:
        Lista de Chunk con id determinista.
    """
    max_chars = max_chars or CHUNK_MAX_CHARS
    overlap = overlap if overlap is not None else CHUNK_OVERLAP_CHARS
    lines = text.splitlines()
    chunks: list[Chunk] = []
    idx = 0

    # Pila de cabeceras: (nivel, texto)
    heading_stack: list[tuple[int, str]] = []
    current_heading = ""
    buf: list[str] = []

    def flush() -> None:
        nonlocal idx, buf, current_heading
        body = "\n".join(buf).strip()
        if not body:
            buf = []
            return
        heading_path = " / ".join(h for _, h in heading_stack) if heading_stack else ""
        for win in _split_paragraph_windows(body, max_chars, overlap):
            chunks.append(Chunk(
                id=_chunk_id(mirror, path, idx),
                block=block_id,
                mirror=mirror,
                path=path,
                heading=current_heading,
                heading_path=heading_path,
                text=win,
            ))
            idx += 1
        buf = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            # Podar la pila: quitar cabeceras de nivel >= al nuevo
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_heading = title
        else:
            buf.append(line)

    flush()
    return chunks
