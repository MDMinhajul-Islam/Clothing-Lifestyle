"""Small offline tests for product semantic recommendation boundaries."""
import unittest
from pydantic import ValidationError
from backend.app.recommendation.schemas import (
    FindSimilarProductsInput, RecommendationItem, SemanticProductSearchInput)
from backend.app.recommendation.service import RecommendationService
from scripts.zara_recommendation.generate_product_embeddings import build_embedding_text, content_hash

def row(product_id='zara-us:00000002',price=40.0,categories=None):
    return dict(product_id=product_id,name='LINEN SHIRT',department='MAN',price=price,
        currency='USD',categories=categories or ['Shirts'],colors=['White'],sizes=['M'],
        is_on_sale=False,primary_image_url=None,semantic_score=0.75)

class FakeEmbedding:
    def embed(self,texts): return [[0.1]*384 for _ in texts]

class FakeInventoryResult:
    total_network_available=12
    overall_status='IN_STOCK'

class FakeInventory:
    def __init__(self): self.calls=[]
    def check_inventory(self,request): self.calls.append(request); return FakeInventoryResult()

class FakeRetriever:
    def __init__(self,rows=None,reference=True): self.rows=rows or [row()]; self.reference=reference; self.filters=None
    def get_reference(self,product_id):
        return {'embedding':'['+','.join(['0.1']*384)+']'} if self.reference else None
    def search(self,vector,**filters): self.filters=filters; return self.rows

class TestProductRecommendation(unittest.TestCase):
    def service(self,retriever,inventory=None):
        return RecommendationService(object(),embedding_client=FakeEmbedding(),retriever=retriever,
                                     inventory_service=inventory or FakeInventory())

    def test_embedding_text_and_hash_are_deterministic(self):
        product=dict(exact_product_name='  LINEN  SHIRT ',department='MAN',categories=['Shirts','Shirts'],
            colors=['White','Beige'],composition_text='100% linen',material_text='linen',
            long_description='Regular shirt.',fit_information='Regular fit')
        text=build_embedding_text(product)
        self.assertEqual(text,build_embedding_text(product))
        self.assertEqual(content_hash(text),content_hash(build_embedding_text(product)))
        self.assertIn('Categories: Shirts',text); self.assertIn('Colors: Beige, White',text)

    def test_category_and_price_filters(self):
        retriever=FakeRetriever([row(price=90,categories=['Trousers']),row(price=45,categories=['Trousers'])])
        request=SemanticProductSearchInput(query='matching pants',target_category='trouser',max_price=50)
        output=self.service(retriever).semantic_product_search(request)
        self.assertEqual([item.price for item in output.results],[45])
        self.assertEqual(retriever.filters['target_category'],'trouser')
        self.assertEqual(retriever.filters['max_price'],50)

    def test_self_match_excluded(self):
        reference='zara-us:00000001'; retriever=FakeRetriever([row(reference),row()])
        output=self.service(retriever).find_similar_products(FindSimilarProductsInput(reference_product_id=reference))
        self.assertEqual([item.product_id for item in output.results],['zara-us:00000002'])
        self.assertEqual(retriever.filters['exclude_product_id'],reference)

    def test_invalid_reference_product(self):
        with self.assertRaises(ValidationError): FindSimilarProductsInput(reference_product_id='bad-id')
        with self.assertRaises(ValueError):
            self.service(FakeRetriever(reference=False)).find_similar_products(
                FindSimilarProductsInput(reference_product_id='zara-us:00000001'))

    def test_recommendation_schema_and_availability_boundary(self):
        inventory=FakeInventory(); output=self.service(FakeRetriever(),inventory).semantic_product_search(
            SemanticProductSearchInput(query='linen shirt'))
        self.assertEqual(len(inventory.calls),1)
        item=RecommendationItem.model_validate(output.results[0])
        self.assertTrue(item.availability_verified)
        self.assertEqual(item.availability_origin,'synthetic_operational_layer')
        self.assertIn('SYNTHETIC_AVAILABILITY_VERIFIED',item.reason_codes)

if __name__=='__main__': unittest.main()
