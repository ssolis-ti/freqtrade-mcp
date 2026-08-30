"""Agente LLM por bloque documental.

Combina el RAG del bloque (Retriever, feature 001) con un LLM del gateway
LiteLLM/Bifrost para responder preguntas del dominio con citas estructuradas.

Reglas duras:
- El RAG es la UNICA fuente: sin hits suficientes -> rechazo explicito (sin llamar al LLM).
- Si el LLM falla (tras 1 retry) -> degrada a hits crudos (nunca inventa).
- Modelo configurable por bloque via env AGENT_MODEL_<BLOQUE> (default AGENT_MODEL_DEFAULT).
- Extrae SOLO message.content (ignora reasoning_content); max_tokens >= 2000.
"""
from __future__ import annotations

import json
import os
import re
import warnings

from .config import ROOT
from .embeddings import Embedder
from .retriever import Retriever

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:4000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
AGENT_MODEL_DEFAULT = os.getenv("AGENT_MODEL_DEFAULT", "deepseek-via-inference")
AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "2000"))
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

_SYSTEM_PROMPT = (
    "Eres el agente del bloque documental {block} de freqtrade. "
    "Responde SOLO con la informacion de los fragmentos proporcionados, en el idioma "
    "de la pregunta. Si la informacion no esta en los fragmentos, dilo explicitamente. "
    "No inventes parametros, valores ni comportamientos. Al final de la respuesta, "
    "cita cada fragmento usado en la forma [fuente: {{mirror}}/{{path}} - {{heading}}]."
)

_ENV_KEY_RE = re.compile(r"[^A-Z0-9]")


def _env_key(block_id: str) -> str:
    return f"AGENT_MODEL_{_ENV_KEY_RE.sub('_', block_id.upper())}"


class AgenteLLM:
    """Agente: RAG del bloque + LLM del gateway, con citas y degradacion."""

    def __init__(self, block_id: str, embedder: Embedder | None = None,
                 client=None) -> None:
        self.block_id = block_id
        self.retriever = Retriever(block_id, embedder=embedder)
        self.model = os.getenv(_env_key(block_id), AGENT_MODEL_DEFAULT)
        self.model_active = self.model
        self._client = client

    # --- Cliente LLM (lazy, inyectable para tests) ---

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY or "no-need",
                timeout=(5.0, 90.0),
            )
        return self._client

    def _chat(self, messages: list[dict]) -> str | None:
        """Una llamada de chat; devuelve content o None si falla."""
        try:
            resp = self._get_client().chat.completions.create(
                model=self.model_active,
                messages=messages,
                max_tokens=AGENT_MAX_TOKENS,
                temperature=AGENT_TEMPERATURE,
            )
            return resp.choices[0].message.content or None
        except Exception as e:  # noqa: BLE001
            warnings.warn(f"LLM fallo ({type(e).__name__}: {e}); retry 1", RuntimeWarning, stacklevel=3)
        try:
            resp = self._get_client().chat.completions.create(
                model=self.model_active,
                messages=messages,
                max_tokens=AGENT_MAX_TOKENS,
                temperature=AGENT_TEMPERATURE,
            )
            return resp.choices[0].message.content or None
        except Exception as e:  # noqa: BLE001
            warnings.warn(f"LLM fallo tras retry ({type(e).__name__}: {e})", RuntimeWarning, stacklevel=3)
            return None

    # --- API publica ---

    def responder(self, query: str, top_k: int = 3) -> dict:
        """Responde la pregunta usando el RAG del bloque + LLM.

        Returns:
            {"respuesta": str, "citas": list[dict], "estado": "ok"|"sin_hits"|"degradado_llm"}
        """
        hits = self.retriever.query(query, top_k=top_k)

        if not hits:
            return {
                "respuesta": (
                    f"No encontre informacion sobre eso en el bloque '{self.block_id}' "
                    "(ningun fragmento supera el umbral de similitud). No puedo responder "
                    "sin fundamento; intenta otra pregunta o consulta otro bloque."
                ),
                "citas": [],
                "estado": "sin_hits",
            }

        citas = [
            {"chunk_id": h["chunk_id"], "mirror": h["mirror"], "path": h["path"],
             "heading": h["heading"], "score": h["score"]}
            for h in hits
        ]

        fragmentos = "\n\n".join(
            f"{i+1}) (score {h['score']:.2f}) [{h['mirror']}] {h['path']} - {h['heading']}\n{h['text'][:1500]}"
            for i, h in enumerate(hits)
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT.format(block=self.block_id)},
            {"role": "user", "content": (
                f"FRAGMENTOS DEL BLOQUE {self.block_id}:\n{fragmentos}\n\n"
                f"PREGUNTA: {query}"
            )},
        ]

        texto = self._chat(messages)
        if texto is None:
            # Degradacion: hits crudos (nunca inventar)
            crudo = "\n\n".join(
                f"[{h['score']:.2f}] ({h['mirror']}) {h['path']} - {h['heading']}\n{h['text']}"
                for h in hits
            )
            return {
                "respuesta": (
                    f"El LLM no esta disponible; te dejo los fragmentos mas relevantes "
                    f"del bloque '{self.block_id}':\n\n{crudo}"
                ),
                "citas": citas,
                "estado": "degradado_llm",
            }

        return {"respuesta": texto, "citas": citas, "estado": "ok"}

    def health(self) -> dict:
        h = self.retriever.health()
        h.update({
            "modelo_configurado": self.model,
            "modelo_activo": self.model_active,
            "llm_base_url": LLM_BASE_URL,
        })
        return h
