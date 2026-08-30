"""Tests de chunking: jerarquia por cabeceras, split por tamano, id determinista."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunking import chunk_markdown  # noqa: E402
from rag.config import CHUNK_MAX_CHARS  # noqa: E402

SAMPLE = """# Configure the bot

## The Freqtrade configuration file

The bot is configured via a JSON file.

### Environment variables

Environment variables can be used to override settings.

## Multiple configuration files

Multiple configs are merged in order.

### Parameters table

%s
""" % ("param: value\n" * 500)


def test_chunking_by_headings():
    chunks = chunk_markdown(SAMPLE, "configuration.md", "fuente", "02-configuracion")
    assert len(chunks) >= 3
    # La primera seccion con heading propio debe heredar el heading_path
    heads = [c.heading for c in chunks if c.heading]
    assert "Environment variables" in heads


def test_large_section_is_split():
    chunks = chunk_markdown(SAMPLE, "configuration.md", "web", "02-configuracion")
    for c in chunks:
        assert c.char_len <= CHUNK_MAX_CHARS + 400  # solape incluido
    assert len(chunks) > 3  # la tabla de parametros grande se subdividio


def test_id_deterministic():
    a = chunk_markdown(SAMPLE, "configuration.md", "fuente", "02-configuracion")
    b = chunk_markdown(SAMPLE, "configuration.md", "fuente", "02-configuracion")
    assert [c.id for c in a] == [c.id for c in b]
    assert [c.text for c in a] == [c.text for c in b]


def test_ids_differ_between_mirrors():
    a = chunk_markdown(SAMPLE, "configuration.md", "fuente", "02-configuracion")
    b = chunk_markdown(SAMPLE, "configuration.md", "web", "02-configuracion")
    assert [c.id for c in a] != [c.id for c in b]


def test_real_configuration_chunking():
    p = Path(__file__).resolve().parent.parent / "docs-freqtrade" / "02-configuracion" / "configuration.md"
    text = p.read_text(encoding="utf-8")
    chunks = chunk_markdown(text, "configuration.md", "fuente", "02-configuracion")
    assert len(chunks) > 20
    for c in chunks:
        assert c.char_len <= CHUNK_MAX_CHARS + 400
        assert c.heading_path  # contexto jerarquico presente
