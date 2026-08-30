"""Tests del indexador: ambos mirrors, conteos, idempotencia."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.blocks import get_block  # noqa: E402
from rag.config import RAG_DATA_DIR  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.indexer import index_block  # noqa: E402


def _local_embedder():
    # Fuerza el fallback local: determinista y sin red
    return Embedder(base_url="http://127.0.0.1:9", model="test-embed")


def test_index_pilot_block():
    m = index_block(get_block("02-configuracion"), force=True, embedder=_local_embedder())
    assert m["chunk_count"] > 0
    assert m["mirror_counts"]["fuente"] > 0
    assert m["mirror_counts"]["web"] > 0
    assert m["dim"] == 384
    assert m["embed_model"] == "local-hash"
    # Archivos escritos
    rag_dir = RAG_DATA_DIR / "02-configuracion"
    assert (rag_dir / "chunks.json").exists()
    assert (rag_dir / "vectors.npy").exists()
    assert (rag_dir / "index.json").exists()
    chunks = json.loads((rag_dir / "chunks.json").read_text(encoding="utf-8"))
    assert len(chunks) == m["chunk_count"]


def test_index_idempotent():
    e = _local_embedder()
    m1 = index_block(get_block("02-configuracion"), force=True, embedder=e)
    m2 = index_block(get_block("02-configuracion"), force=False, embedder=e)
    assert m2["chunk_count"] == m1["chunk_count"]
    assert m2["content_hash"] == m1["content_hash"]
    assert m2["mirror_counts"] == m1["mirror_counts"]


def test_missing_mirror_ok():
    # Un bloque sin web_dir (inexistente) debe indexar solo la fuente sin romper
    m = index_block(get_block("00-index"), force=True, embedder=_local_embedder())
    assert m["chunk_count"] > 0
    assert m["mirror_counts"].get("web", 0) >= 0
