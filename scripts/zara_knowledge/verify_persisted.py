"""Read-only verification of persisted Phase 2D content against local manifests."""
import psycopg2
from backend.app.config import settings
from .common import CORPUS, ROOT, read, write

def main():
    conn=psycopg2.connect(settings.supabase_db_url,connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        docs,chunks=read(CORPUS/'documents.json'),read(CORPUS/'chunks.json')
        with conn.cursor() as cur:
            for d in docs:
                cur.execute('SELECT source_hash,raw_text,clean_text,active FROM public.knowledge_documents WHERE knowledge_id=%s',(d['knowledge_id'],))
                assert cur.fetchone()==(d['source_hash'],d['raw_text'],d['clean_text'],True)
            for c in chunks:
                cur.execute('SELECT knowledge_id,chunk_text FROM public.knowledge_chunks WHERE chunk_id=%s',(c['chunk_id'],))
                assert cur.fetchone()==(c['knowledge_id'],c['chunk_text'])
            cur.execute('SELECT count(embedding) FROM public.knowledge_chunks')
            embeddings=cur.fetchone()[0]
        result=dict(status='PASS',transaction='READ_ONLY',documents=len(docs),chunks=len(chunks),
                    embeddings=embeddings,source_and_content_parity='PASS')
        write(ROOT/'reports/phase_2d_persisted_validation.json',result)
        print(result)
    finally:
        conn.rollback();conn.close()

if __name__=='__main__':
    main()
