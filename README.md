# Zara AI Retail Assistant & Tool Gateway

An enterprise-grade, omnichannel AI retail assistant platform built upon the live Zara US product catalogue, a realistic synthetic operational layer, and a high-performance deterministic backend Tool Gateway API.

## Project Architecture & Current State

- **Current Status**: Phase 2C Complete (Backend Domain Services & AI Tool Gateway API).
- **Next Phase**: Phase 2D (Official Zara US Policy Knowledge Corpus, Supabase pgvector RAG, and Business Rules Discrepancy Audit).
- **Test Baseline**: 83 / 83 unit and integration tests passing (`python -m unittest discover tests`).

## Autonomous Agent & Developer Handoff

For autonomous coding agents (such as Codex) or engineers continuing development, refer directly to the authoritative handoff documentation:

- 📖 **[docs/CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md)**: Comprehensive human-readable technical handoff specification.
- ⚙️ **[docs/codex_handoff.json](docs/codex_handoff.json)**: Machine-readable architecture, schema, tool catalog, and database metadata.
- 🛠️ **[docs/tool_gateway_architecture.md](docs/tool_gateway_architecture.md)**: Deep-dive Tool Gateway architecture and representative tool flow specifications.

## Quick Start & Verification

```bash
# 1. Run complete regression test suite
python -m unittest discover tests

# 2. Start FastAPI Tool Gateway server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Test Tool Gateway flows and latency benchmarks
python scripts/supabase/test_tool_gateway_flows.py
```
