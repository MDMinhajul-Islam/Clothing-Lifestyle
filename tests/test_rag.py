"""Offline regression tests: provenance, abstention, model isolation, and safety."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from backend.app.rag.embeddings import EmbeddingClient, EmbeddingUnavailable, validate_vector
from backend.app.rag.retriever import fuse
from backend.app.rag.schemas import PolicyQuery
from backend.app.rag.service import retrieve_policy_knowledge, select_evidence
from scripts.zara_knowledge.common import CORPUS, clean_extraction, official_url, read, write
from scripts.zara_knowledge.chunk_knowledge import chunk_document
from scripts.zara_knowledge.validate_knowledge import validate

class TestPolicyRag(unittest.TestCase):
    def test_corpus_provenance(self):
        self.assertGreater(validate()['chunks'], 0)

    def test_cross_market_and_host_rejection(self):
        for url in ['https://www.zara.com/uk/en/help', 'https://zara.com.evil/us/en/help',
                    'http://www.zara.com/us/en/help', 'https://u:p@www.zara.com/us/en/help']:
            self.assertFalse(official_url(url))
        with self.assertRaises(ValidationError):
            PolicyQuery(query='returns', market='GB')

    def test_immutable_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'capture.json'
            write(p, {'text':'original'}, immutable=True)
            write(p, {'text':'original'}, immutable=True)
            with self.assertRaises(FileExistsError):
                write(p, {'text':'changed'}, immutable=True)

    def test_truncated_capture_rejected(self):
        with self.assertRaises(ValueError):
            clean_extraction('L1: # POLICY\nL2: missing remainder')

    def test_chunk_deterministic_and_preserves_exceptions(self):
        doc = next(d for d in read(CORPUS/'documents.json') if d['source_id']=='ReturnSpecialConditions')
        self.assertEqual(chunk_document(doc), chunk_document(doc))
        self.assertEqual(chunk_document(doc)[0]['chunk_text'],doc['clean_text'])

    def test_missing_embedding_config(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(EmbeddingUnavailable):
                EmbeddingClient.from_environment()

    def test_invalid_vectors(self):
        for vector in [[0,0], [1,float('nan')], [1], [True,2], [1,float('inf')]]:
            with self.assertRaises(ValueError):
                validate_vector(vector,2)

    def test_rank_fusion_deduplicates(self):
        rows = fuse([{'chunk_id':'a'},{'chunk_id':'b'}],[{'chunk_id':'b'}])
        self.assertEqual(rows[0]['chunk_id'],'b')
        self.assertEqual(rows[0]['retrieval_method'],'hybrid')
        self.assertEqual(len(rows),2)

    def test_insufficient_evidence(self):
        with patch('backend.app.rag.service.PolicyRetriever.retrieve', return_value=[]), patch.dict('os.environ',{},clear=True):
            result = retrieve_policy_knowledge('lunar delivery guarantee', conn=object())
        self.assertEqual(result.status,'INSUFFICIENT_EVIDENCE')
        self.assertFalse(result.evidence)

    def test_retrieval_failure_is_distinct(self):
        with patch('backend.app.rag.service.PolicyRetriever.retrieve', side_effect=RuntimeError('private error')), patch.dict('os.environ',{},clear=True):
            result = retrieve_policy_knowledge('return',conn=object())
        self.assertEqual(result.status,'RETRIEVAL_UNAVAILABLE')
        self.assertNotIn('private error',result.model_dump_json())

    def test_semantic_score_alone_is_not_evidence(self):
        row = dict(read(CORPUS/'chunks.json')[0],score=0.99,retrieval_method='semantic')
        self.assertEqual(select_evidence([row],PolicyQuery(query='return')),[])

    def test_query_bounds(self):
        with self.assertRaises(ValidationError):
            PolicyQuery(query='x'*1001)
        with self.assertRaises(ValidationError):
            PolicyQuery(query='return',limit=100)

    def test_unsupported_qualifier_abstains(self):
        doc = next(d for d in read(CORPUS/'chunks.json') if d['source_id']=='Refund')
        row = dict(doc,score=0.1,retrieval_method='text')
        self.assertEqual(select_evidence([row],PolicyQuery(query='cryptocurrency refund reimbursement')),[])

    def test_whitespace_query_rejected(self):
        with self.assertRaises(ValidationError):
            PolicyQuery(query='   ')
