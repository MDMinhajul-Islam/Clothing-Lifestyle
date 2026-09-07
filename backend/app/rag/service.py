"""Future orchestrator contract returning evidence only, never a policy answer."""
from .embeddings import EmbeddingUnavailable, get_embedding_client
from .retriever import PolicyRetriever, query_terms
from .schemas import PolicyEvidence, PolicyQuery, PolicyResult

INSUFFICIENT = 'I could not verify this from the current official Zara US policy corpus.'

def select_evidence(rows, request):
    terms = set(query_terms(request.query))
    evidence = []
    for row in rows:
        text_terms = set(query_terms(row['chunk_text']))
        coverage = len(terms & text_terms) / max(1, len(terms))
        # Semantic-only admission awaits calibration against real embeddings.
        # Conservative lexical grounding also applies to hybrid candidates.
        if coverage < 1.0 or row['retrieval_method'] == 'semantic':
            continue
        evidence.append(PolicyEvidence(**{k:row[k] for k in PolicyEvidence.model_fields if k in row}))
    return evidence[:request.limit]

def retrieve_policy_knowledge(query, policy_type=None, market='US', locale='en',
                             section_title=None, *, conn=None, embedding_client=None, limit=5):
    request = PolicyQuery(query=query, policy_type=policy_type, market=market, locale=locale,
                          section_title=section_title, limit=limit)
    semantic_status = 'NOT_CONFIGURED'
    vector = None
    try:
        embedding_client = embedding_client or get_embedding_client()
        vector = embedding_client.embed([query])[0]
        semantic_status = 'ENABLED'
    except EmbeddingUnavailable:
        semantic_status = 'UNAVAILABLE_OR_NOT_CONFIGURED'
    try:
        if conn is None:
            from backend.app.db import get_db_connection
            with get_db_connection() as connection:
                try:
                    rows = PolicyRetriever(connection).retrieve(request, vector, embedding_client)
                finally:
                    connection.rollback()  # read transaction; no gateway audit or writes
        else:
            rows = PolicyRetriever(conn).retrieve(request, vector, embedding_client)
        evidence = select_evidence(rows, request)
        return PolicyResult(status='EVIDENCE_FOUND' if evidence else 'INSUFFICIENT_EVIDENCE',
            evidence=evidence, message=None if evidence else INSUFFICIENT, semantic_status=semantic_status)
    except Exception:
        return PolicyResult(status='RETRIEVAL_UNAVAILABLE', message='Policy retrieval is temporarily unavailable.',
                            semantic_status=semantic_status)
