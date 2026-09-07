"""Generate and import the separate local product semantic index.

Default mode is --dry-run. Heavy --generate and --import modes are manual only.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from backend.app.config import settings
from backend.app.rag.embeddings import LocalSentenceTransformerClient, validate_vector

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT=ROOT/'data/generated/zara_product_embeddings.jsonl'
EXPECTED_PRODUCTS=6018
PROVIDER='local_sentence_transformers'
MODEL='sentence-transformers/all-MiniLM-L6-v2'
DIMENSION=384
VERSION='v1'

def normalize(value):
    return ' '.join(str(value or '').split())

def unique_sorted(values):
    return sorted({normalize(value) for value in values or [] if normalize(value)},key=str.casefold)

def build_embedding_text(product):
    fields=[('Product',product.get('exact_product_name')),('Department',product.get('department')),
            ('Categories',', '.join(unique_sorted(product.get('categories')))),
            ('Colors',', '.join(unique_sorted(product.get('colors')))),
            ('Composition',product.get('composition_text')),('Material',product.get('material_text')),
            ('Description',product.get('long_description') or product.get('short_description')),
            ('Fit',product.get('fit_information'))]
    return '\n'.join(f'{label}: {normalize(value)}' for label,value in fields if normalize(value))

def content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def fetch_products(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''SELECT p.product_id,p.exact_product_name,p.department,p.short_description,
            p.long_description,p.fit_information,p.composition_text,p.material_text,
            COALESCE((SELECT array_agg(DISTINCT cat.name) FROM product_categories pc
                JOIN categories cat USING(category_id) WHERE pc.product_id=p.product_id),ARRAY[]::text[]) categories,
            COALESCE((SELECT array_agg(DISTINCT c.color_name) FROM product_colors c
                WHERE c.product_id=p.product_id),ARRAY[]::text[]) colors
            FROM products p ORDER BY p.product_id''')
        products=[dict(row) for row in cur.fetchall()]
    if len(products)!=EXPECTED_PRODUCTS:
        raise RuntimeError(f'Expected {EXPECTED_PRODUCTS} products, found {len(products)}; stop and reconcile catalogue state.')
    return products

def load_output(path):
    if not path.exists(): return {}
    records={}
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            record=json.loads(line)
            if record['product_id'] in records: raise ValueError('Duplicate product_id in output')
            records[record['product_id']]=record
    return records

def write_output(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8',newline='\n') as stream:
        for product_id in sorted(records):
            stream.write(json.dumps(records[product_id],ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
    temporary.replace(path)

def generate(conn,path,batch_size):
    products=fetch_products(conn); existing=load_output(path); output={}; pending=[]; skipped=failed=0
    for product in products:
        text=build_embedding_text(product); source_hash=content_hash(text); old=existing.get(product['product_id'])
        if old and old.get('source_content_hash')==source_hash and old.get('embedding_model')==MODEL and old.get('embedding_version')==VERSION:
            validate_vector(old['embedding'],DIMENSION); output[product['product_id']]=old; skipped+=1
        else: pending.append((product['product_id'],text,source_hash))
    client=LocalSentenceTransformerClient()
    for offset in range(0,len(pending),batch_size):
        batch=pending[offset:offset+batch_size]
        try:
            vectors=client.embed([item[1] for item in batch])
            stamp=datetime.now(timezone.utc).isoformat()
            for (product_id,text,source_hash),vector in zip(batch,vectors):
                output[product_id]=dict(product_id=product_id,embedding_text=text,embedding=vector,
                    embedding_provider=PROVIDER,embedding_model=MODEL,embedding_dimension=DIMENSION,
                    embedding_version=VERSION,source_content_hash=source_hash,embedded_at=stamp)
        except Exception as exc:
            failed+=len(batch); print(f'FAILED batch {offset//batch_size+1}: {type(exc).__name__}')
        print(f'progress={min(offset+len(batch),len(pending))}/{len(pending)}')
    write_output(path,output)
    embedded=len(pending)-failed
    print({'expected':EXPECTED_PRODUCTS,'embedded':embedded,'skipped':skipped,'failed':failed,'output_records':len(output),'device':client.device})
    if failed or len(output)!=EXPECTED_PRODUCTS: raise SystemExit(1)

def import_records(conn,path,batch_size):
    records=load_output(path)
    if len(records)!=EXPECTED_PRODUCTS: raise RuntimeError(f'Expected {EXPECTED_PRODUCTS} output records, found {len(records)}')
    with conn.cursor() as cur:
        cur.execute('''SELECT product_id,source_content_hash,embedding_provider,embedding_model,embedding_version
            FROM product_embeddings''')
        existing={row[0]:row[1:] for row in cur.fetchall()}
        changed=[record for record in records.values() if existing.get(record['product_id']) !=
                 (record['source_content_hash'],PROVIDER,MODEL,VERSION)]
        sql='''INSERT INTO product_embeddings (product_id,embedding_text,embedding,embedding_provider,
            embedding_model,embedding_dimension,embedding_version,source_content_hash,embedded_at)
            VALUES %s ON CONFLICT(product_id) DO UPDATE SET embedding_text=EXCLUDED.embedding_text,
            embedding=EXCLUDED.embedding,embedding_provider=EXCLUDED.embedding_provider,
            embedding_model=EXCLUDED.embedding_model,embedding_dimension=EXCLUDED.embedding_dimension,
            embedding_version=EXCLUDED.embedding_version,source_content_hash=EXCLUDED.source_content_hash,
            embedded_at=EXCLUDED.embedded_at,updated_at=now()'''
        for offset in range(0,len(changed),batch_size):
            batch=changed[offset:offset+batch_size]
            values=[(r['product_id'],r['embedding_text'],json.dumps(r['embedding']),PROVIDER,MODEL,DIMENSION,
                     VERSION,r['source_content_hash'],r['embedded_at']) for r in batch]
            execute_values(cur,sql,values,template='(%s,%s,%s::vector,%s,%s,%s,%s,%s,%s)')
            print(f'upserted={min(offset+len(batch),len(changed))}/{len(changed)}')
    conn.commit(); print({'upserted':len(changed),'skipped':len(records)-len(changed),'failed':0})

def verify_db(conn):
    with conn.cursor() as cur:
        cur.execute('''SELECT count(*),count(embedding),min(vector_dims(embedding)),max(vector_dims(embedding))
            FROM product_embeddings WHERE embedding_provider=%s AND embedding_model=%s
            AND embedding_version=%s AND embedding_dimension=%s''',(PROVIDER,MODEL,VERSION,DIMENSION))
        row=cur.fetchone()
    print({'product_embeddings':row[0],'embedded_chunks':row[1],'min_dimension':row[2],'max_dimension':row[3]})
    if row!=(EXPECTED_PRODUCTS,EXPECTED_PRODUCTS,DIMENSION,DIMENSION): raise SystemExit(1)

def verify_output(path):
    records=load_output(path)
    for record in records.values():
        if (record.get('embedding_provider'),record.get('embedding_model'),record.get('embedding_dimension'),record.get('embedding_version')) != (PROVIDER,MODEL,DIMENSION,VERSION):
            raise ValueError('Embedding metadata mismatch')
        if content_hash(record['embedding_text'])!=record['source_content_hash']:
            raise ValueError('Embedding text hash mismatch')
        validate_vector(record['embedding'],DIMENSION)
    print({'output_records':len(records),'valid_embeddings':len(records),'dimension':DIMENSION})
    if len(records)!=EXPECTED_PRODUCTS: raise SystemExit(1)

def apply_migration(conn):
    migration=ROOT/'supabase/migrations/009_product_semantic_schema.sql'
    with conn.cursor() as cur: cur.execute(migration.read_text(encoding='utf-8'))
    conn.commit(); print({'migration':'009_product_semantic_schema.sql','status':'APPLIED'})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true'); mode.add_argument('--generate',action='store_true')
    mode.add_argument('--import',dest='do_import',action='store_true'); mode.add_argument('--verify-db',action='store_true')
    mode.add_argument('--apply-migration',action='store_true')
    mode.add_argument('--verify-output',action='store_true')
    parser.add_argument('--batch-size',type=int,default=64); parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    if not 1<=args.batch_size<=1000: parser.error('--batch-size must be between 1 and 1000')
    if args.verify_output:
        verify_output(args.output)
        return
    conn=psycopg2.connect(settings.supabase_db_url,connect_timeout=15)
    try:
        with conn.cursor() as cur: cur.execute('SET LOCAL search_path = public, extensions, pg_catalog')
        if args.apply_migration: apply_migration(conn)
        elif args.generate: generate(conn,args.output,args.batch_size)
        elif args.do_import: import_records(conn,args.output,args.batch_size)
        elif args.verify_db: verify_db(conn)
        else:
            products=fetch_products(conn); samples=[build_embedding_text(p) for p in products[:3]]
            print({'mode':'DRY_RUN','products':len(products),'unique_hashes':len({content_hash(build_embedding_text(p)) for p in products}),
                   'sample_text_lengths':[len(text) for text in samples],'model_not_loaded':True,'database_writes':False})
    finally:
        conn.rollback(); conn.close()

if __name__=='__main__': main()
