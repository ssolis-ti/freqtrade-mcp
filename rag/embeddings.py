"""Embeddings para el RAG por bloque.

Backend primario: gateway LiteLLM/Bifrost (API compatible OpenAI) configurable por env.
Si el gateway falla (401, red, timeout), degrada automaticamente a un embedding
local determinista ("local-hash"): bag-of-words hasheado (md5 de tokens -> indices)
normalizado L2, dimension fija. Es una aproximacion por palabras clave, NO semantica
real; suficiente para el MVP y siempre disponible sin dependencias pesadas.
"""
from __future__ import annotations

import hashlib
import math
import re
import warnings
from typing import Sequence

from .config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_BATCH_SIZE,
                     EMBED_MODEL, EMBED_TIMEOUT, LOCAL_EMBED_DIM, LOCAL_EMBED_NAME)

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


class Embedder:
    """Calcula embeddings de textos/queries con fallback local determinista."""

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None) -> None:
        self.base_url = base_url or EMBED_BASE_URL
        self.model = model or EMBED_MODEL
        self.api_key = api_key if api_key is not None else EMBED_API_KEY
        self._client = None
        self._local = False
        self._dim = LOCAL_EMBED_DIM
        self._gateway_error: str | None = None

    # --- API publica ---

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embebe una lista de textos (batching <= EMBED_BATCH_SIZE)."""
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = list(texts[i:i + EMBED_BATCH_SIZE])
            if self._local:
                out.extend(self._local_embed_many(batch))
                continue
            try:
                vecs = self._gateway_embed(batch)
                out.extend(vecs)
            except Exception as e:  # noqa: BLE001 - cualquier fallo degrada
                self._fallback_to_local(e)
                out.extend(self._local_embed_many(batch))
        return out

    def embed_query(self, query: str) -> list[float]:
        """Embebe una query (usa el mismo camino que embed_texts con lote de 1)."""
        return self.embed_texts([query])[0]

    def model_name(self) -> str:
        return LOCAL_EMBED_NAME if self._local else self.model

    def dim(self) -> int:
        return self._dim

    def is_local(self) -> bool:
        return self._local

    def gateway_error(self) -> str | None:
        return self._gateway_error

    # --- Gateway ---

    def _gateway_embed(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "no-need",
                timeout=EMBED_TIMEOUT,
            )
        resp = self._client.embeddings.create(model=self.model, input=texts)
        data = sorted(resp.data, key=lambda d: d.index)
        vecs = [list(d.embedding) for d in data]
        if vecs:
            self._dim = len(vecs[0])
        return vecs

    def _fallback_to_local(self, exc: Exception) -> None:
        self._local = True
        self._dim = LOCAL_EMBED_DIM
        self._gateway_error = f"{type(exc).__name__}: {exc}"
        warnings.warn(
            f"Embeddings por gateway ({self.base_url}) no disponibles "
            f"({self._gateway_error}); usando fallback local '{LOCAL_EMBED_NAME}'. "
            f"Recuperacion aproximada por palabras clave, no semantica real.",
            RuntimeWarning,
            stacklevel=3,
        )

    # --- Fallback local determinista ---

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return _TOKEN_RE.findall(text.lower())

    @classmethod
    def _local_embed(cls, text: str, dim: int) -> list[float]:
        vec = [0.0] * dim
        for tok in cls._tokens(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def _local_embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._local_embed(t, self._dim) for t in texts]
