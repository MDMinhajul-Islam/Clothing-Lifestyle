"""Transactional additive knowledge importer. Default dry-run; --apply persists only knowledge.

Migration is managed separately. Old versions are retained, with one active version
per source. Advisory locking serializes imports and prevents stale activation.
"""
import argparse
import json
import psycopg2
from backend.app.config import settings
from .common import CORPUS, read
from .validate_knowledge import validate

def import_corpus(conn, docs, chunks, embeddings=()):
    with conn.cursor() as cur:
        cur.execute('SET LOCAL search_path = public, extensions, pg_catalog')
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('zara_us_knowledge_ingestion'))")
        for d in docs:
            cur.execute('''INSERT INTO public.knowledge_documents
                (knowledge_id,source_id,source_url,source_name,market,locale,policy_type,document_title,
                 effective_date,retrieved_at,source_hash,raw_text,clean_text,normalization_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (knowledge_id) DO NOTHING''', tuple(d[k] for k in (
                'knowledge_id','source_id','source_url','source','market','locale','policy_type',
                'document_title','effective_date','retrieved_at','source_hash','raw_text','clean_text','normalization_version')))
        for c in chunks:
            cur.execute('''INSERT INTO public.knowledge_chunks
                (chunk_id,knowledge_id,section_title,chunk_index,chunk_text,token_count,token_count_method,chunking_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (chunk_id) DO NOTHING''', tuple(c[k] for k in (
                'chunk_id','knowledge_id','section_title','chunk_index','chunk_text','token_count','token_count_method','chunking_version')))
        for r in embeddings:
            cur.execute('''UPDATE public.knowledge_chunks SET embedding=%s::vector,
                embedding_provider=%s,embedding_model=%s,embedding_dimension=%s,embedding_version=%s,generated_at=%s
                WHERE chunk_id=%s''', (json.dumps(r['embedding']), r['embedding_provider'],r['embedding_model'],
                r['embedding_dimension'],r['embedding_version'],r['generated_at'],r['chunk_id']))
        for d in docs:
            cur.execute('''SELECT knowledge_id FROM public.knowledge_documents WHERE source_id=%s
                ORDER BY retrieved_at DESC, normalization_version DESC, knowledge_id DESC LIMIT 1''', (d['source_id'],))
            newest = cur.fetchone()[0]
            cur.execute('''UPDATE public.knowledge_documents SET active=false,updated_at=now()
                WHERE source_id=%s AND active AND knowledge_id<>%s''', (d['source_id'],newest))
            cur.execute('''UPDATE public.knowledge_documents SET active=true,updated_at=now()
                WHERE knowledge_id=%s AND NOT active''', (newest,))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    print(validate())
    if not args.apply:
        print('DRY_RUN: no database connection or writes')
        return
    conn = psycopg2.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn:
            import_corpus(conn, read(CORPUS/'documents.json'), read(CORPUS/'chunks.json'),
                          read(CORPUS/'embeddings.json') if (CORPUS/'embeddings.json').exists() else ())
        print('KNOWLEDGE_IMPORT_COMMITTED')
    finally:
        conn.close()

if __name__ == '__main__':
    main()
