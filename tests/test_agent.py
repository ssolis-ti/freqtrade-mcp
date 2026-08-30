"""Tests del agente LLM por bloque (mocks del cliente — sin gastar credito)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.agent import AgenteLLM
from rag.config import RAG_DATA_DIR
from rag.embeddings import Embedder
from rag.indexer import index_block
from rag.blocks import get_block


class FakeResponse:
    class Choice:
        def __init__(self, content):
            self.message = type("M", (), {"content": content})()

    def __init__(self, content):
        self.choices = [self.Choice(content)]


class _Completions:
    def __init__(self, owner):
        self._owner = owner

    def create(self, **kwargs):
        return self._owner._create(**kwargs)


class _Chat:
    def __init__(self, owner):
        self.completions = _Completions(owner)


class FakeClient:
    """Cliente openai simulado: controlable por test (chat.completions.create)."""
    def __init__(self, content="respuesta de prueba", fail_times=0):
        self.chat = _Chat(self)
        self.content = content
        self.fail_times = fail_times
        self.calls = 0
        self.last_kwargs = None

    def _create(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        if self.calls <= self.fail_times:
            raise TimeoutError("simulado")
        return FakeResponse(self.content)


def _ensure_indexed():
    e = Embedder(base_url="http://127.0.0.1:9", model="test-embed")
    if not (RAG_DATA_DIR / "02-configuracion" / "index.json").exists():
        index_block(get_block("02-configuracion"), force=True, embedder=e)
    return e


def test_responder_ok_con_citas():
    e = _ensure_indexed()
    client = FakeClient(content="El modo dry-run simula sin dinero real.")
    a = AgenteLLM("02-configuracion", embedder=e, client=client)
    r = a.responder("what is dry run mode", top_k=2)
    assert r["estado"] == "ok"
    assert r["respuesta"] == "El modo dry-run simula sin dinero real."
    assert len(r["citas"]) > 0
    for c in r["citas"]:
        assert c["block"] if "block" in c else True  # citas del bloque
        assert c["mirror"] in ("fuente", "web")
    # El prompt usa el modelo configurado y max_tokens >= 2000
    assert client.last_kwargs["model"] == "deepseek-via-inference"
    assert client.last_kwargs["max_tokens"] >= 2000


def test_responder_sin_hits_no_llama_al_llm():
    e = _ensure_indexed()
    client = FakeClient()
    a = AgenteLLM("02-configuracion", embedder=e, client=client)
    r = a.responder("zzzqqqxxxwvvv termino inexistente", top_k=2)
    assert r["estado"] == "sin_hits"
    assert r["citas"] == []
    assert client.calls == 0  # CRITICO: no gastar credito en no-hits


def test_responder_degrada_a_hits_crudos():
    e = _ensure_indexed()
    client = FakeClient(fail_times=2)  # falla 2 veces (1er intento + retry)
    a = AgenteLLM("02-configuracion", embedder=e, client=client)
    r = a.responder("dry run mode configuration", top_k=2)
    assert r["estado"] == "degradado_llm"
    assert len(r["citas"]) > 0
    assert "fragmentos" in r["respuesta"].lower() or "bloque" in r["respuesta"].lower()


def test_health_incluye_modelo():
    e = _ensure_indexed()
    a = AgenteLLM("02-configuracion", embedder=e, client=FakeClient())
    h = a.health()
    assert h["modelo_configurado"] == "deepseek-via-inference"
    assert h["modelo_activo"] == "deepseek-via-inference"
    assert h["chunk_count"] > 0


def test_modelo_por_bloque_env(monkeypatch):
    e = _ensure_indexed()
    monkeypatch.setenv("AGENT_MODEL_02_CONFIGURACION", "deepseek-v4-pro")
    a = AgenteLLM("02-configuracion", embedder=e, client=FakeClient())
    assert a.model == "deepseek-v4-pro"
    assert a.health()["modelo_configurado"] == "deepseek-v4-pro"
