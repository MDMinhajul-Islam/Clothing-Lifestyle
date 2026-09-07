"""Apply, seed, or verify Phase 2F.1 without exposing database credentials."""
import argparse
from pathlib import Path
import psycopg2
from backend.app.config import settings

ROOT=Path(__file__).resolve().parents[2]

def execute_file(conn,path):
    with conn.cursor() as cur: cur.execute(path.read_text(encoding='utf-8'))
    conn.commit()

def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply-migration',action='store_true')
    group.add_argument('--seed',action='store_true')
    group.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    if not settings.supabase_db_url: raise SystemExit('SUPABASE_DB_URL is not configured.')
    conn=psycopg2.connect(settings.supabase_db_url,connect_timeout=15)
    try:
        if args.apply_migration:
            execute_file(conn,ROOT/'supabase/migrations/010_retail_capabilities.sql')
            print({'migration':'010_retail_capabilities.sql','status':'APPLIED'})
        elif args.seed:
            execute_file(conn,ROOT/'scripts/backend_capabilities/seed_phase_2f1.sql')
            print({'seed':'phase_2f1','status':'APPLIED'})
        else:
            conn.set_session(readonly=True)
            with conn.cursor() as cur:
                cur.execute("""SELECT
                  (SELECT count(*) FROM loyalty_accounts),
                  (SELECT count(*) FROM promotions),
                  (SELECT count(*) FROM customer_auth_sessions),
                  (SELECT count(*) FROM incidents),
                  (SELECT count(*) FROM support_cases),
                  (SELECT count(*) FROM loyalty_accounts WHERE NOT is_synthetic OR data_origin<>'synthetic_operational_layer'),
                  (SELECT count(*) FROM promotions WHERE NOT is_synthetic OR data_origin<>'synthetic_operational_layer'),
                  (SELECT count(*) FROM loyalty_accounts l LEFT JOIN customers c USING(customer_id) WHERE c.customer_id IS NULL),
                  (SELECT count(*) FROM incidents i LEFT JOIN orders o USING(order_id) WHERE o.order_id IS NULL),
                  (SELECT count(*) FROM support_cases s LEFT JOIN customers c USING(customer_id) WHERE s.customer_id IS NOT NULL AND c.customer_id IS NULL)""")
                row=cur.fetchone()
            print({'loyalty_accounts':row[0],'promotions':row[1],'auth_sessions':row[2],
                   'incidents':row[3],'support_cases':row[4],
                   'invalid_loyalty_provenance':row[5],'invalid_promotion_provenance':row[6],
                   'orphan_loyalty':row[7],'orphan_incidents':row[8],'orphan_support_cases':row[9]})
    finally:
        conn.rollback(); conn.close()
if __name__=='__main__': main()
