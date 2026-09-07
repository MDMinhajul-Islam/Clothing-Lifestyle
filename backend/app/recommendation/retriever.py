"""Parameterized cosine retrieval over the separate product semantic table."""
import json
from psycopg2.extras import RealDictCursor

PROVIDER = 'local_sentence_transformers'
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
VERSION = 'v1'
DIMENSION = 384

class ProductSemanticRetriever:
    def __init__(self, conn):
        self.conn = conn

    def get_reference(self, product_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SET LOCAL search_path = public, extensions, pg_catalog')
            cur.execute('''SELECT pe.embedding::text AS embedding, p.product_id, p.exact_product_name AS name,
                p.department, p.current_price AS price, p.currency, p.is_on_sale
                FROM public.product_embeddings pe JOIN public.products p USING(product_id)
                WHERE p.product_id=%s AND p.lifecycle_status='ACTIVE'
                AND pe.embedding_provider=%s AND pe.embedding_model=%s
                AND pe.embedding_version=%s AND pe.embedding_dimension=%s''',
                (product_id, PROVIDER, MODEL, VERSION, DIMENSION))
            row = cur.fetchone()
            return dict(row) if row else None

    def search(self, vector, *, target_category=None, department=None, min_price=None,
               max_price=None, size=None, color=None, exclude_product_id=None, limit=8):
        clauses = ["p.lifecycle_status='ACTIVE'", 'pe.embedding_provider=%s',
                   'pe.embedding_model=%s', 'pe.embedding_version=%s',
                   'pe.embedding_dimension=%s']
        params = [PROVIDER, MODEL, VERSION, DIMENSION]
        if exclude_product_id:
            clauses.append('p.product_id<>%s'); params.append(exclude_product_id)
        if department:
            clauses.append('p.department ILIKE %s'); params.append(department)
        if min_price is not None:
            clauses.append('p.current_price>=%s'); params.append(min_price)
        if max_price is not None:
            clauses.append('p.current_price<=%s'); params.append(max_price)
        if target_category:
            clauses.append('''(p.exact_product_name ILIKE %s OR EXISTS
                (SELECT 1 FROM product_categories pc JOIN categories cat USING(category_id)
                WHERE pc.product_id=p.product_id AND (cat.name ILIKE %s OR cat.slug ILIKE %s)))''')
            pattern=f'%{target_category}%'
            params.extend([pattern, pattern, pattern])
        if color:
            clauses.append('''EXISTS (SELECT 1 FROM product_colors c WHERE c.product_id=p.product_id
                AND c.color_name ILIKE %s)'''); params.append(color)
        if size:
            clauses.append('''EXISTS (SELECT 1 FROM product_variants v WHERE v.product_id=p.product_id
                AND v.size_name ILIKE %s)'''); params.append(size)
        params=[json.dumps(vector),*params,json.dumps(vector),limit]
        sql = f'''SELECT p.product_id, p.exact_product_name AS name, p.department,
            p.current_price::float AS price, p.currency, p.is_on_sale,
            COALESCE((SELECT array_agg(DISTINCT cat.name ORDER BY cat.name)
                FROM product_categories pc JOIN categories cat USING(category_id)
                WHERE pc.product_id=p.product_id), ARRAY[]::text[]) AS categories,
            COALESCE((SELECT array_agg(DISTINCT c.color_name ORDER BY c.color_name)
                FROM product_colors c WHERE c.product_id=p.product_id), ARRAY[]::text[]) AS colors,
            COALESCE((SELECT array_agg(DISTINCT v.size_name ORDER BY v.size_name)
                FROM product_variants v WHERE v.product_id=p.product_id), ARRAY[]::text[]) AS sizes,
            (SELECT i.source_image_url FROM product_images i WHERE i.product_id=p.product_id
                ORDER BY (i.image_role='PRIMARY') DESC, i.display_order LIMIT 1) AS primary_image_url,
            1-(pe.embedding <=> %s::vector) AS semantic_score
            FROM public.product_embeddings pe JOIN public.products p USING(product_id)
            WHERE {' AND '.join(clauses)}
            ORDER BY pe.embedding <=> %s::vector, p.product_id LIMIT %s'''
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SET LOCAL search_path = public, extensions, pg_catalog')
            cur.execute(sql, tuple(params))
            return [dict(row) for row in cur.fetchall()]
