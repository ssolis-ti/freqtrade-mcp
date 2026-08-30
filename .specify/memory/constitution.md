# Freqtrade Multi-Agent Framework Constitution

## Core Principles

### I. Documentation-as-Org-Chart (source of truth)
Freqtrade's official documentation IS the organizational structure. Each agent owns a
documentary block (RAG over its docs) as its domain of reference. No agent generalizes
across blocks; the chapter/block is the agent's source of truth. Density of a block
dictates how many agents it gets. RAG-por-bloque con ambos mirrors (fuente `develop`
+ web stable) + embeddings es la arquitectura base.

### II. RAG-Block Isolation
Each block = one vector store + one MCP server (FastMCP) exposing retrieval tools over
that block only. Blocks do not share embeddings or context. A block's RAG answers only
from its own corpus — never from another block, never from prompt-borne guesswork.

### III. Safe-Operation Gate (NON-NEGOTIABLE)
Never risk real capital, publish, delete, or read a live trading surface without explicit
user OK. Dry-run → Live only with explicit user authorization. The `stoploss`/`leverage`
domain governs risk; no agent overrides it. Secrets only in `.env`, never hardcoded.

### IV. Portability & Config-from-Env
Every external dependency (LiteLLM/Bifrost embeddings, freqtrade API, model endpoints)
degrades gracefully when absent. Zero hardcoded absolute paths or machine-specific
assumptions; config comes from env vars with sane defaults. The MCP protocol is the
universal surface.

### V. Spec-Driven, Idea-First
The spec is the source of truth for development. Development starts only after the idea
is depurada and the user says go. When the user asks for idea/prototype, deliver exactly
that and stop — nothing more. Tests written → approve → implement (Red-Green-Refactor).

## Architecture Constraints

- Python 3.11/3.14, `mcp>=1.27,<2.0` (2.x removed `mcp.server.fastmcp`).
- `unset PYTHONPATH` before running project venvs (global Hermes venv contaminates).
- Embebidos vía LiteLLM/Bifrost `:4000` configurable en `.env`; sentence-transformers
  local como fallback determinista.
- Windows: run scripts as files (`python tools/x.py`), `python -c` blocked by approval
  gate; `/tmp` de MSYS falla para curl → `$LOCALAPPDATA/Temp`.
- Corpus: `docs-freqtrade/` (fuente develop) + `docs-freqtrade-web/` (web stable).
  12 bloques documentales. Un MCP server por bloque.

## Development Workflow & Quality Gates

- SDD: `/speckit.constitution → specify → plan → tasks → implement`. Sequential feature
  numbering.
- Each block's MCP server must pass a smoke test (FastMCP tool list + a retrieval call).
- Every public deliverable: no emojis, no internal docs, no real trading data, no
  internal links. README + code + tests per repo.

## Governance

This constitution supersedes ad-hoc practices. Amendments require documentation and user
approval. Blocks are merged/refactored only via the spec pipeline, never ad-hoc.

**Version**: 1.0.0 | **Ratified**: 2026-08-30 | **Last Amended**: 2026-08-30
