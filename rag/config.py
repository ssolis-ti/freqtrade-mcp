"""Configuracion del framework RAG por bloque.

Toda configuracion proviene de variables de entorno (o .env en la raiz del proyecto).
Sin rutas absolutas hardcodeadas: la raiz se deriva de la ubicacion de este modulo.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv es dependencia declarada
    load_dotenv = None

# Raiz del proyecto = padre del paquete rag/
ROOT = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

# --- Embeddings (gateway LiteLLM/Bifrost compatible OpenAI) ---
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://localhost:4000")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_TIMEOUT = (5.0, 30.0)      # connect, read
EMBED_BATCH_SIZE = 16            # max textos por request

# --- Fallback local ---
LOCAL_EMBED_DIM = 384            # dimension fija del local-hash
LOCAL_EMBED_NAME = "local-hash"

# --- Vector store / RAG ---
RAG_DATA_DIR = Path(os.getenv("RAG_DATA_DIR", str(ROOT / "data" / "rag")))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.25"))

# --- Chunking ---
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "2000"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "200"))
