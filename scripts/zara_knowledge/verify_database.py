"""Verify migration and corpus import transactionally; --apply commits only Phase 2D.

All existing catalogue/operational table counts are compared before and after.
No original gateway mutation tests are invoked. Logs contain no connection details.
"""
import argparse
import psycopg2
from backend.app.config import settings
from .common import ROOT, CORPUS, read, write
from .import_knowledge import import_corpus
from .validate_knowledge import validate

def run(apply=False):
    validate()
    conn = psycopg2.connect(settings.supabase_db_url, connect_timeout=15)
    report = {'mode':'COMMIT' if apply else 'ROLLBACK', 'embedding_generation':'NOT_CONFIGURED'}
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='5s'")
            cur.execute("SET LOCAL statement_timeout='30s'")
            cur.execute("SELECT to_regclass('public.knowledge_documents') IS NOT NULL")
            report['schema_preexisting'] = cur.fetchone()[0]
            tables = ['products','product_variants','orders','order_items','returns','return_items',
                      'inventory_levels','tool_audit_log','tool_idempotency_keys']
            before = {}
            for table in tables:
                cur.execute('SELECT count(*) FROM public.' + table)
                before[table] = cur.fetchone()[0]
            cur.execute((ROOT/'supabase/migrations/008_knowledge_rag_schema.sql').read_text(encoding='utf-8'))
            # A second execution verifies rerunnable DDL inside the same transaction.
            cur.execute((ROOT/'supabase/migrations/008_knowledge_rag_schema.sql').read_text(encoding='utf-8'))
        docs, chunks = read(CORPUS/'documents.json'), read(CORPUS/'chunks.json')
        import_corpus(conn,docs,chunks)
        import_corpus(conn,docs,chunks)
        with conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM public.knowledge_documents WHERE active')
            report['active_documents'] = cur.fetchone()[0]
            cur.execute('SELECT count(*),count(embedding) FROM public.knowledge_chunks')
            report['chunks'],report['embeddings'] = cur.fetchone()
            assert report['active_documents'] == len(docs)
            assert report['chunks'] == len(chunks)
            cur.execute("SELECT relname,relrowsecurity FROM pg_class WHERE oid IN ('public.knowledge_documents'::regclass,'public.knowledge_chunks'::regclass)")
            assert all(r[1] for r in cur.fetchall())
            cur.execute("SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename IN ('knowledge_documents','knowledge_chunks')")
            assert cur.fetchone()[0] == 0
            for role in ('anon','authenticated'):
                for table in ('knowledge_documents','knowledge_chunks'):
                    cur.execute('SELECT has_table_privilege(%s,%s,%s)',(role,'public.'+table,'SELECT,INSERT,UPDATE,DELETE'))
                    assert not cur.fetchone()[0], 'Unexpected client privilege'
            for table in tables:
                cur.execute('SELECT count(*) FROM public.'+table)
                assert cur.fetchone()[0] == before[table], 'Existing domain count changed'
            report['existing_domain_counts_unchanged'] = True
            report['rls_and_client_privileges'] = 'PASS'
        if apply:
            conn.commit()
        else:
            conn.rollback()
        report['status'] = 'PASS'
        write(ROOT/('reports/phase_2d_database_'+('applied' if apply else 'rollback')+'.json'),report)
        print(report)
    finally:
        conn.rollback()
        conn.close()

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply',action='store_true')
    args = p.parse_args()
    try:
        run(args.apply)
    except Exception as exc:
        print({'status':'FAILED','error_type':type(exc).__name__, 'sqlstate':getattr(exc,'pgcode',None)})
        raise SystemExit(1)
