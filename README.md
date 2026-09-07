# Zara AI Retail Assistant & Tool Gateway

An enterprise-grade, omnichannel AI retail assistant platform built upon the live Zara US product catalogue, a realistic synthetic operational layer, and a high-performance deterministic backend Tool Gateway API.

## Project Architecture & Current State

- **Current Status**: Phase 2D.1 complete with 11 local MiniLM policy embeddings and validated hybrid retrieval. Existing business rules are unchanged.
- **Next Step**: Phase 2E orchestration after reviewing the documented policy/security discrepancies.
- **Fresh Safe Tests**: 85 passing (68 historical local + 17 RAG). The historical 83-test suite includes 15 database-writing gateway tests excluded from this run.
- **Phase 2D Documentation**: [Architecture, commands, validation and limitations](docs/phase_2d_rag_architecture.md).

## Autonomous Agent & Developer Handoff

For autonomous coding agents (such as Codex) or engineers continuing development, refer directly to the authoritative handoff documentation:

- 📖 **[docs/CODEX_HANDOFF.md](docs/CODEX_HANDOFF.md)**: Comprehensive human-readable technical handoff specification.
- ⚙️ **[docs/codex_handoff.json](docs/codex_handoff.json)**: Machine-readable architecture, schema, tool catalog, and database metadata.
- 🛠️ **[docs/tool_gateway_architecture.md](docs/tool_gateway_architecture.md)**: Deep-dive Tool Gateway architecture and representative tool flow specifications.

## Quick Start & Verification

```bash
# 1. Run safe local regression tests (excludes live gateway writes)
python -m scripts.zara_knowledge.run_safe_tests

# 2. Start FastAPI Tool Gateway server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Validate local policy evidence without database writes
python -m scripts.zara_knowledge.validate_knowledge
```
