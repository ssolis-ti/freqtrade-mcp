"""Tests del retriever: top-k, umbral min_score, no-hits explicito, aislamiento."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DATA_DIR  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.indexer import index_block  # noqa: E402
from rag.retriever import Retriever  # noqa: E402
from rag.blocks import get_block  # noqa: E402


def _ensure_indexed():
    e = Embedder(base_url="http://127.0.0.1:9", model="test-embed")
    if not (RAG_DATA_DIR / "02-configuracion" / "index.json").exists():
        index_block(get_block("02-configuracion"), force=True, embedder=e)
    return e


def test_query_returns_relevant_hits():
    e = _ensure_indexed()
    r = Retriever("02-configuracion", embedder=e)
    hits = r.query("stoploss configuration parameter", top_k=3)
    assert len(hits) > 0
    for h in hits:
        assert h["block"] == "02-configuracion"
        assert "score" in h and "text" in h and "mirror" in h
    # Los hits deben estar ordenados por score descendente
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_top_k_respected():
    e = _ensure_indexed()
    r = Retriever("02-configuracion", embedder=e)
    assert len(r.query("configuration", top_k=1)) <= 1
    assert len(r.query("configuration", top_k=5)) <= 5


def test_no_hits_out_of_corpus():
    e = _ensure_indexed()
    r = Retriever("02-configuracion", embedder=e)
    hits = r.query("zzzqqqxxxwvvv no such term", top_k=3)
    assert hits == []


def test_min_score_threshold():
    e = _ensure_indexed()
    r = Retriever("02-configuracion", embedder=e)
    strict = r.query("configuration", top_k=3, min_score=0.99)
    assert strict == []


def test_missing_block_raises():
    try:
        Retriever("99-no-existe")
        assert False, "deberia lanzar KeyError (bloque inexistente)"
    except KeyError:
        pass


def test_health():
    e = _ensure_indexed()
    r = Retriever("02-configuracion", embedder=e)
    h = r.health()
    assert h["ok"] is True
    assert h["block"] == "02-configuracion"
    assert h["chunk_count"] > 0
