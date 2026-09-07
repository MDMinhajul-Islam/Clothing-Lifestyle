"""Internal evidence-based product recommendation service."""
import json
from backend.app.rag.embeddings import get_embedding_client, validate_vector
from backend.app.schemas.inventory import CheckInventoryInput
from backend.app.services.inventory_service import InventoryService
from .retriever import ProductSemanticRetriever
from .schemas import RecommendationItem, RecommendationOutput

class RecommendationService:
    def __init__(self, conn, *, embedding_client=None, retriever=None, inventory_service=None):
        self.embedding_client = embedding_client or get_embedding_client()
        self.retriever = retriever or ProductSemanticRetriever(conn)
        self.inventory_service = inventory_service or InventoryService(conn)

    @staticmethod
    def _filters(input_data):
        return {name:getattr(input_data,name) for name in
                ('target_category','department','min_price','max_price','size','color','limit')}

    def _finalize(self, rows, input_data, reference_product_id=None):
        results=[]
        for row in rows:
            if row['product_id'] == reference_product_id:
                continue
            if input_data.min_price is not None and row['price'] < input_data.min_price: continue
            if input_data.max_price is not None and row['price'] > input_data.max_price: continue
            if input_data.department and row['department'].casefold() != input_data.department.casefold(): continue
            if input_data.target_category and not (input_data.target_category.casefold() in row['name'].casefold()
                    or any(input_data.target_category.casefold() in value.casefold() for value in row['categories'])): continue
            if input_data.color and not any(input_data.color.casefold() == value.casefold() for value in row['colors']): continue
            if input_data.size and not any(input_data.size.casefold() == value.casefold() for value in row['sizes']): continue
            inventory = self.inventory_service.check_inventory(CheckInventoryInput(
                product_id=row['product_id'], size=input_data.size, color=input_data.color))
            available = inventory.total_network_available > 0
            reasons=['SEMANTIC_SIMILARITY']
            if input_data.target_category: reasons.append('CATEGORY_FILTER_MATCH')
            if input_data.color: reasons.append('COLOR_FILTER_MATCH')
            if row['is_on_sale']: reasons.append('ON_SALE')
            reasons.append('SYNTHETIC_AVAILABILITY_VERIFIED')
            score=max(0.0,min(1.0,float(row['semantic_score']) + (0.05 if available else 0) + (0.01 if row['is_on_sale'] else 0)))
            results.append(RecommendationItem(**row, recommendation_score=score,
                availability_verified=True, availability_status=inventory.overall_status,
                availability_origin='synthetic_operational_layer', reason_codes=reasons))
        results.sort(key=lambda item:(-item.recommendation_score, item.product_id))
        results=results[:input_data.limit]
        return RecommendationOutput(reference_product_id=reference_product_id,
            total_results=len(results),results=results)

    def semantic_product_search(self, input_data):
        vector=self.embedding_client.embed([input_data.query])[0]
        validate_vector(vector,384)
        return self._finalize(self.retriever.search(vector,**self._filters(input_data)),input_data)

    def find_similar_products(self, input_data):
        reference=self.retriever.get_reference(input_data.reference_product_id)
        if not reference:
            raise ValueError('Reference product is invalid, inactive, or not embedded.')
        vector=json.loads(reference['embedding']) if isinstance(reference['embedding'],str) else list(reference['embedding'])
        validate_vector(vector,384)
        rows=self.retriever.search(vector,exclude_product_id=input_data.reference_product_id,
                                   **{**self._filters(input_data),'limit':min(60,input_data.limit*3)})
        return self._finalize(rows,input_data,input_data.reference_product_id)

    def recommend_matching_products(self, input_data):
        return self.find_similar_products(input_data)
