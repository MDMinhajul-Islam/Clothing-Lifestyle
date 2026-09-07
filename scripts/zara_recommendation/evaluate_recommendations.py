"""Small read-only Phase 2E recommendation smoke evaluation."""
import json
import psycopg2
from backend.app.config import settings
from backend.app.recommendation.schemas import SemanticProductSearchInput
from backend.app.recommendation.service import RecommendationService

CASES=[
    ('linen shirt','shirt',None),
    ('denim jeans','jean',75),
    ('black dress','dress',150),
    ('leather jacket','jacket',250),
]

def main():
    conn=psycopg2.connect(settings.supabase_db_url,connect_timeout=15)
    try:
        conn.set_session(readonly=True); service=RecommendationService(conn); results=[]
        for query,category,max_price in CASES:
            request=SemanticProductSearchInput(query=query,target_category=category,max_price=max_price,limit=5)
            output=service.semantic_product_search(request)
            passed=bool(output.results) and all((max_price is None or item.price<=max_price)
                and (category.casefold() in item.name.casefold()
                    or any(category.casefold() in name.casefold() for name in item.categories))
                and item.product_id.startswith('zara-us:') and item.availability_verified for item in output.results)
            results.append({'query':query,'results':len(output.results),'passed':passed,
                            'top_product_id':output.results[0].product_id if output.results else None})
        report={'cases':results,'passed':sum(r['passed'] for r in results),'total':len(results),'read_only':True}
        print(json.dumps(report,indent=2))
        if report['passed']!=report['total']: raise SystemExit(1)
    finally:
        conn.rollback(); conn.close()

if __name__=='__main__': main()
