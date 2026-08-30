"""Tests del benchmark: golden set valido, metricas calculadas, reporte JSON."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.benchmark_rag import run_benchmark  # noqa: E402
from rag.config import RAG_DATA_DIR  # noqa: E402
from rag.embeddings import Embedder  # noqa: E402
from rag.indexer import index_block  # noqa: E402
from rag.blocks import get_block  # noqa: E402


def _ensure_indexed():
    e = Embedder(base_url="http://127.0.0.1:9", model="test-embed", gemini_key="")
    if not (RAG_DATA_DIR / "02-configuracion" / "index.json").exists():
        index_block(get_block("02-configuracion"), force=True, embedder=e)
    return e


def test_golden_set_valido():
    gp = Path(__file__).resolve().parent.parent / "tools" / "golden_set.json"
    assert gp.exists()
    items = json.loads(gp.read_text(encoding="utf-8"))
    assert len(items) >= 20
    for g in items:
        assert g["block"]
        assert g["query"]
        assert g["expected_chunk_id"]


def test_benchmark_metricas():
    _ensure_indexed()
    m = run_benchmark("02-configuracion", top_k=3)
    assert m["n_preguntas"] > 0
    assert 0.0 <= m["recall@1"] <= 1.0
    assert 0.0 <= m["recall@3"] <= 1.0
    assert 0.0 <= m["mrr"] <= 1.0
    assert m["recall@3"] >= m["recall@1"]


def test_benchmark_reporte_json():
    _ensure_indexed()
    run_benchmark("02-configuracion", top_k=3)
    rp = RAG_DATA_DIR.parent / "benchmark" / "02-configuracion.json"
    assert rp.exists()
    data = json.loads(rp.read_text(encoding="utf-8"))
    assert "recall@1" in data and "mrr" in data and "detalle" in data
