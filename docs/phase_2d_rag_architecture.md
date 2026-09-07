# Phase 2D official Zara US policy knowledge

Status: structurally complete; real embedding generation and semantic quality validation pending explicit provider credentials/configuration. Existing backend policy rules are unchanged. No orchestrator, voice, frontend, recommendation embeddings or catalogue sync was implemented.

## Sources and evidence

`data/knowledge/zara_us/source_manifest.json` records 11 reviewed official US English help sources: HowToReturn, Refund, HowToExchange, PaymentMethods, DeliveryMethods, ReturnSpecialConditions, CareAndComposition, MySize, EditOrder, OrderStatus and FaultyItems.

Each source has its URL, topic, discovery timestamp, status and effective date (null unless explicitly published). The corpus covers the required policy topics. It is not exhaustive: the legal PDF, detailed garment-care guide and additional store/contact-service details remain coverage notes, not fabricated policies. These are optional coverage extensions, not new Phase 2D implementation work.

Evidence in `data/raw/zara/help/` is the unchanged official-page text returned by the research tool, including its extraction wrapper. It is **not** raw HTTP HTML. The tool's upstream fetch/crawl time is not independently verified. The local `retrieved_at` records receipt of the tool extract. A direct HowToReturn HTTP probe received 403, and direct access stopped. Append-only metadata files record hashes, page titles and clarify that this probe result was not observed individually for the other sources.

Capture versions are never overwritten. `source_hash` is SHA-256 of the exact raw-text UTF-8 string; `raw_artifact_hash` covers the saved capture envelope. Identical captures reuse their identity. Changed source text creates a new version. Metadata corrections are append-only sidecars.

## Normalization and chunking

Normalized JSON documents retain both raw and clean text plus full provenance. Companion Markdown files contain metadata and readable policy text. The cleaner removes tool line/citation markup, site navigation, the article table of contents and footer. It requires a recognizable article heading and ending, rejecting truncated extracts. It preserves wording, amounts, conditions and exceptions.

Document identity includes source ID, source hash and normalization version. `documents.json` is the current import manifest; immutable document versions remain under `documents/`.

The 11 articles form 11 semantic chunks. Keeping each article intact preserves cross-section conditions and exceptions, including special-category restrictions. Token counts are explicitly estimates (`ceil_characters_div_4`), not model-tokenizer measurements. Most articles are smaller than the 500–1000-token target; the shipping article is approximately 1130. These are documented soft-target exceptions. Articles above 2200 estimated tokens are rejected for reviewed segmentation rather than silently split. There is no unnecessary overlap. Section titles identify the full article; original subheadings remain in chunk text.

## PostgreSQL and ingestion

Migration `008_knowledge_rag_schema.sql` enables pgvector if needed and creates backend-only `knowledge_documents` and `knowledge_chunks`. Full-text GIN and metadata/foreign-key indexes support retrieval. Document versions are retained with at most one active version per source.

The vector column is dimension-flexible until a provider is selected. Embeddings require complete provider/model/dimension/version/timestamp metadata and a nonzero vector matching the recorded dimension. Queries filter all four identity fields before cosine comparison. With only 11 chunks, exact cosine search is appropriate; an approximate vector index is deferred until real corpus volume and dimensions justify one. PostgreSQL text search uses English linguistic normalization. See [pgvector documentation](https://github.com/pgvector/pgvector) and [PostgreSQL text search](https://www.postgresql.org/docs/current/textsearch-controls.html).

The importer validates provenance, serializes ingestion with a transaction-scoped advisory lock, inserts immutable document/chunk identities and activates the newest source version. Repeated imports do not duplicate rows. Old versions are retained; this is not a deletion/replacement pipeline. Imports touch only knowledge tables.

Migration 008 was executed twice and the corpus imported twice inside a successful rollback verification transaction. It was then applied with 11 documents and 11 chunks committed, with zero embeddings. Client privileges/RLS were checked. Counts for the checked existing catalogue, orders, returns, inventory and gateway tables stayed unchanged.

## Embeddings pending

No embedding provider/model credentials are configured. No vectors were fabricated or generated. Configure all of these backend-only environment variables before future generation:

```
RAG_EMBEDDING_PROVIDER
RAG_EMBEDDING_MODEL
RAG_EMBEDDING_DIMENSION
RAG_EMBEDDING_VERSION
RAG_EMBEDDING_URL
RAG_EMBEDDING_API_KEY
```

The adapter expects an explicitly selected HTTPS endpoint accepting JSON `{model, input: [text]}` and returning `{data: [{index, embedding}]}`. It has no default URL/provider. The operator must verify that the chosen provider implements this protocol and select its model/revision. Redirects are denied; failures do not expose provider bodies or credentials. Dimension, finiteness and nonzero magnitude are validated. Cached vectors are reused only when chunk hash and model identity match. Generating a new model version replaces a chunk's current vector on import; prior raw evidence/documents remain preserved.

The only completion blocker is real embedding configuration and the resulting generation/import/semantic evaluation. The current corpus and lexical retrieval are already usable as a backend evidence interface.

## Retrieval contract

```python
from backend.app.rag.service import retrieve_policy_knowledge

result = retrieve_policy_knowledge(
    query, policy_type=None, market="US", locale="en", section_title=None
)
```

This function returns `PolicyResult`, never a conversational answer. The interface is backend-only and is not added to the 14 operational tools.

Candidate generation combines English full-text ranking and, when configured, exact vector cosine similarity. Reciprocal-rank fusion merges results. Filters require US/en and active versions; topic and article title are optional. Results retain chunk/document/source IDs, source URL/hash, topic/title, effective/retrieval dates, score and method.

Without embeddings, text retrieval is explicitly used. Missing/failed embedding access is visible in `semantic_status`. Scores are ranking signals, not truth probabilities. Every meaningful normalized query term must be present in a returned article; this conservative check favors abstention and may reject paraphrases. Semantic-only admission is deliberately disabled until real embedding evaluation calibrates it. Hybrid candidates still undergo lexical grounding.

States:

- `EVIDENCE_FOUND`: relevant source excerpts, not a claim that every interpretation is resolved.
- `INSUFFICIENT_EVIDENCE`: empty evidence plus “I could not verify this from the current official Zara US policy corpus.”
- `RETRIEVAL_UNAVAILABLE`: infrastructure failure, distinguished from an empty corpus result.

`requires_policy_rule_reconciliation=true` prevents treating policy evidence as operational eligibility. Dynamic state and all mutations remain Tool Gateway responsibilities. Do not derive customer-specific eligibility from RAG. Retrieved source content is evidence, not executable instructions.

## Audits and evaluation

`policy_facts.json` contains 15 explicitly supported facts with exact evidence lines and source hashes. Exception fields are not a comprehensive policy engine; consult the complete article and special-condition source.

The JSON/Markdown rule discrepancy reports compare 11 current behaviors against captured evidence. They record 4 MISMATCH, 5 PARTIAL and 2 UNKNOWN findings; none justify a silent backend change. Return timing, condition/category checks, fee handling, exchanges and internal state mappings need separately reviewed proposals.

`phase_2d_security_reconciliation.md` records public stores/inventory reads, public tool definitions, development secret defaults, optional ownership verification, non-guaranteed audits and missing automatic redaction. No unrelated security redesign was made.

The nine grounded retrieval questions test expected source, topic, article relevance and citation completeness. Three negative questions test abstention. Latest live read-only text retrieval achieved 9/9 expected-source hits within five results and 3/3 abstentions. An initial unsupported-qualifier false positive was fixed and covered by regression testing. This small corpus smoke test is not a general quality claim. Real semantic/hybrid retrieval quality is pending embeddings.

Manual review of the returned articles confirmed: return questions retain method/condition clauses; refund evidence retains the processing/bank-time distinction; cancellation evidence does not invent numeric cutoffs; exchange and special-return evidence retain restrictions. Evaluation checks article-level relevance rather than narrower clause ranking.

## Repeatable commands and safe tests

Run from the repository root:

```powershell
python -m scripts.zara_knowledge.discover_sources
python -m scripts.zara_knowledge.normalize_sources
python -m scripts.zara_knowledge.chunk_knowledge
python -m scripts.zara_knowledge.build_audit_artifacts
python -m scripts.zara_knowledge.validate_knowledge
python -m scripts.zara_knowledge.import_knowledge
python -m scripts.zara_knowledge.run_safe_tests
```

The import command defaults to offline dry-run. `import_knowledge --apply` persists validated knowledge only. `verify_database` exercises migration/import under rollback; `--apply` commits. `evaluate_retrieval` runs in a read-only transaction. All connections use ignored backend environment configuration without displaying secrets.

Future embedding completion: configure the explicit provider contract, run `generate_embeddings`, then `import_knowledge --apply`, and rerun retrieval evaluation to inspect real hybrid results. Do not call generation while credentials are absent.

The historical baseline contains 83 tests. The safe runner excludes all 15 `TestToolGatewayAPI` tests because even GET-like tool operations can persist audit rows. It runs the remaining 68 historical local tests plus focused new RAG tests. Historical gateway tests remain intact. Use a separately configured isolated database for their future write tests; a caller-side rollback cannot undo commits on connections opened by gateway services. Windows sandbox temporary-directory permissions initially blocked local tests; the permitted unsandboxed offline run passed.

Scope ends here. Complete real embedding validation before starting Phase 2E orchestration; handle documented rule/security changes as explicit reviewed follow-ups.
