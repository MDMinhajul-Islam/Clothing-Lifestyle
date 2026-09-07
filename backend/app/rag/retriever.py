"""Parameterized full-text + exact cosine candidates, fused using reciprocal ranks."""
import json
import re
from psycopg2.extras import RealDictCursor
from .embeddings import validate_vector

STOP = set('what where there is are the a an can i my how do does to from in of for with it be have has when me please tell zara us supported work processed'.split())
ALIASES = {'refunds':'refund', 'returns':'return', 'payments':'payment', 'cancelled':'cancel',
           'canceled':'cancel', 'modifications':'modify', 'modified':'change', 'exceptions':'conditions',
           'window':'days', 'delivery':'delivery'}

def query_terms(query):
    return sorted({ALIASES.get(t,t) for t in re.findall(r'[a-z0-9]+', query.lower()) if t not in STOP})

def fuse(text_rows, vector_rows):
    combined = {}
    for method, rows in [('text', text_rows), ('semantic', vector_rows)]:
        for rank, row in enumerate(rows, 1):
            key = row['chunk_id']
            entry = combined.setdefault(key, dict(row, score=0.0, methods=set()))
            entry['score'] += 1 / (60 + rank)
            entry['methods'].add(method)
    output = []
    for entry in combined.values():
        entry['retrieval_method'] = 'hybrid' if len(entry['methods']) == 2 else next(iter(entry['methods']))
        entry.pop('methods')
        output.append(entry)
    return sorted(output, key=lambda r:(-r['score'], r['chunk_id']))

class PolicyRetriever:
    def __init__(self, conn):
        self.conn = conn

    def retrieve(self, request, vector=None, embedding_client=None):
        terms = query_terms(request.query)
        if not terms:
            return []
        filters = (request.market, request.locale, request.policy_type, request.policy_type,
                   request.section_title, request.section_title)
        base = '''SELECT c.*, d.source_id, d.source_url, d.source_hash, d.policy_type,
                   d.market, d.locale, d.effective_date, d.retrieved_at
                   FROM public.knowledge_chunks c JOIN public.knowledge_documents d USING(knowledge_id)
                   WHERE d.active AND d.market=%s AND d.locale=%s
                   AND (%s IS NULL OR d.policy_type=%s)
                   AND (%s IS NULL OR c.section_title=%s)'''
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SET LOCAL search_path = public, extensions, pg_catalog')
            cur.execute('WITH candidates AS (' + base + ''')
                SELECT *, ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) AS text_score
                FROM candidates WHERE search_vector @@ websearch_to_tsquery('english', %s)
                ORDER BY text_score DESC, chunk_id LIMIT 40''', filters + (' OR '.join(terms),)*2)
            text_rows = [dict(r) for r in cur.fetchall()]
            vector_rows = []
            if vector is not None and embedding_client is not None:
                validate_vector(vector, embedding_client.dimension)
                cur.execute('WITH candidates AS MATERIALIZED (' + base + '''
                    AND c.embedding IS NOT NULL AND c.embedding_provider=%s AND c.embedding_model=%s
                    AND c.embedding_dimension=%s AND c.embedding_version=%s)
                    SELECT *, 1-(embedding <=> %s::vector) AS similarity FROM candidates
                    ORDER BY embedding <=> %s::vector, chunk_id LIMIT 40''', filters + (
                    embedding_client.provider, embedding_client.model, embedding_client.dimension,
                    embedding_client.version, json.dumps(vector), json.dumps(vector)))
                vector_rows = [dict(r) for r in cur.fetchall() if r['similarity'] >= 0.75]
        return fuse(text_rows, vector_rows)
