"""Configuracion global de pytest: indice RAG temporal para tests.

pytest_configure corre ANTES de la coleccion/imports de tests: parchea
RAG_DATA_DIR (en todos los modulos que lo importan) hacia un directorio
temporal y reindexa el bloque piloto con local-hash (sin red, sin gasto).

Asi los tests nunca tocan data/rag/ real (indice de produccion con Gemini).
"""
import tempfile
from pathlib import Path


def pytest_configure(config):
    tmp = Path(tempfile.mkdtemp(prefix="rag_test_"))

    import rag.config as cfg
    import rag.indexer as idx
    import rag.retriever as rtr
    import tools.benchmark_rag as bench

    for mod in (cfg, idx, rtr, bench):
        mod.RAG_DATA_DIR = tmp

    from rag.blocks import get_block
    from rag.embeddings import Embedder
    from rag.indexer import index_block

    index_block(get_block("02-configuracion"), force=True,
                embedder=Embedder(gemini_key=""))
