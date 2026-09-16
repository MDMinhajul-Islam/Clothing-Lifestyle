"""Offline regressions for conversational search, without production DB writes."""
import unittest
from unittest.mock import MagicMock

from backend.app.repositories.catalogue_repo import CatalogueRepository
from backend.app.schemas.catalogue import SearchProductsInput
from backend.app.services.catalogue_service import CatalogueService
from backend.app.voice.executor import VoiceCapabilityExecutor
from backend.app.voice.schemas import CreateVoiceSessionRequest, VoiceTurnRequest
from backend.app.voice.service import VoiceService
from test_search_quality import FakeEmbedding, FakeRepo, EmptyRepo, ROW
from test_voice_phase_2g1 import CapturingBackend


class SemanticRepo(EmptyRepo):
    def search_products(self, **kwargs):
        super().search_products(**kwargs)
        return (1, [ROW]) if kwargs.get('semantic_only') else (0, [])


class SemanticRecoveryTests(unittest.TestCase):
    def service(self, repo=None, embedding=True):
        service = CatalogueService.__new__(CatalogueService)
        service.repo = repo or SemanticRepo()
        service.embedding_client = FakeEmbedding() if embedding else None
        return service

    def test_unrecognized_names_use_semantics_without_a_known_product_type(self):
        for query in ('something cozy for a chilly commute', 'athletic kicks',
                      'a carryall for travel', 'a breezy beach coverup'):
            with self.subTest(query=query):
                service = self.service()
                result = service.search_products(SearchProductsInput(query=query))
                self.assertEqual(result.products[0].product_id, ROW['product_id'])
                self.assertTrue(service.repo.calls[-1]['semantic_only'])
                self.assertIsNone(service.repo.calls[-1]['query'])
                self.assertEqual(service.embedding_client.texts, [query])
                self.assertIn('closest', result.fallback_message)

    def test_fallback_preserves_all_authoritative_facets(self):
        service = self.service()
        service.search_products(SearchProductsInput(
            query='unusual tailored shirt for office', department='MAN', category='Shirts',
            category_id='cat-1', color='navy', size='M', material='linen', brand='Zara',
            min_price=20, max_price=100, on_sale=True, limit=3))
        first, fallback = service.repo.calls
        for key in ('department', 'category', 'category_id', 'product_type', 'color', 'size',
                    'material', 'brand', 'min_price', 'max_price', 'on_sale', 'limit'):
            self.assertEqual(first[key], fallback[key], key)
        self.assertIsNone(fallback['occasion'])

    def test_no_semantic_candidates_does_not_invent_recommendations(self):
        result = self.service(EmptyRepo()).search_products(SearchProductsInput(query='moon boots'))
        self.assertEqual(result.products, [])
        self.assertNotIn('I found', result.fallback_message)
        self.assertNotIn('color or budget', result.fallback_message)

    def test_exact_results_keep_original_behavior_without_extra_queries(self):
        service = self.service(FakeRepo())
        result = service.search_products(SearchProductsInput(query='black dress'))
        self.assertEqual(len(service.repo.calls), 1)
        self.assertIsNone(result.fallback_message)
        self.assertEqual(result.products[0].matched_variant.color, 'Black')

    def test_lexical_sql_remains_unchanged_for_normal_search(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {'cnt': 0}
        cursor.fetchall.return_value = []
        CatalogueRepository(conn).search_products(query='ribbed', semantic_vector=[0.01]*384)
        for call in cursor.execute.call_args_list:
            sql, params = call.args
            self.assertIn('websearch_to_tsquery', sql)
            self.assertNotIn('candidate.embedding', sql)
            self.assertEqual(sql.count('%s'), len(params))

    def test_no_embeddings_does_not_return_random_products_for_unknown_name(self):
        service = self.service(embedding=False)
        result = service.search_products(SearchProductsInput(query='athletic kicks'))
        self.assertEqual(result.products, [])
        self.assertEqual(len(service.repo.calls), 1)

    def test_conversational_fillers_do_not_block_occasion_search(self):
        for query in ("I'm looking for products for my office", 'I want to buy a new product for my office outfit',
                      'Is there any available products for an office outfit?'):
            facets = CatalogueService._extract_facets(SearchProductsInput(query=query))
            self.assertIsNone(facets.query)
            self.assertEqual(facets.occasion, 'office')

    def test_semantic_sql_retrieves_without_lexical_gate_and_keeps_filters(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {'cnt': 0}
        cursor.fetchall.return_value = []
        CatalogueRepository(conn).search_products(query='athletic kicks', semantic_vector=[0.01]*384,
            semantic_only=True, color='black', size='M', max_price=100, department='MAN')
        for call in cursor.execute.call_args_list:
            sql, params = call.args
            self.assertNotIn('websearch_to_tsquery', sql)
            self.assertIn('candidate.embedding <=>', sql)
            self.assertIn('>= 0.30', sql)
            self.assertIn("lifecycle_status = 'ACTIVE'", sql)
            self.assertIn('p.current_price <= %s', sql)
            self.assertIn('v.size_name ILIKE %s', sql)
            self.assertEqual(sql.count('%s'), len(params))

    def test_retry_retains_search_context_end_to_end(self):
        backend = CapturingBackend()
        service = VoiceService(executor=VoiceCapabilityExecutor(backend))
        session = service.create_session(CreateVoiceSessionRequest()).session_id
        service.process_voice_turn(VoiceTurnRequest(session_id=session,
            transcript='Show me black shirts for office under 100 dollars'))
        first = backend.calls[-1]
        for retry in ('Please try.', 'Try again.'):
            result = service.process_voice_turn(VoiceTurnRequest(session_id=session, transcript=retry))
            self.assertNotEqual(result.execution_status, 'LLM_NOT_CONFIGURED')
            self.assertEqual(backend.calls[-1].tool_name, 'search_products')
            for key in ('color', 'max_price', 'occasion'):
                self.assertEqual(backend.calls[-1].tool_arguments.get(key), first.tool_arguments.get(key))


if __name__ == '__main__':
    unittest.main()
