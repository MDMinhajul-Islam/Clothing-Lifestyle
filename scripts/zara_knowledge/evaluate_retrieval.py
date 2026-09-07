"""Read-only retrieval evaluation; no LLM, no operational tool calls or audit writes."""
import psycopg2
from backend.app.config import settings
from backend.app.rag.service import retrieve_policy_knowledge
from backend.app.rag.embeddings import get_embedding_client
from backend.app.rag.retriever import PolicyRetriever
from backend.app.rag.schemas import PolicyQuery
from backend.app.rag.service import select_evidence
from .common import CORPUS, ROOT, read, write

def evaluate(conn):
    embedding_client=get_embedding_client()
    retriever=PolicyRetriever(conn)
    results=[]
    for case in read(CORPUS/'retrieval_eval.json'):
        request=PolicyQuery(query=case['question'])
        lexical=select_evidence(retriever.retrieve(request),request)
        result=retrieve_policy_knowledge(case['question'],conn=conn,embedding_client=embedding_client)
        relevant=[e for e in result.evidence if e.source_url==case['expected_source']]
        results.append(dict(**case,status=result.status,source_correct_at_5=bool(relevant),
            policy_type_correct=any(e.policy_type==case['expected_policy_type'] for e in relevant),
            section_relevant=any(e.section_title==case['expected_section'] for e in relevant),
            provenance_complete=bool(result.evidence) and all(e.source_hash and e.retrieved_at and e.source_url for e in result.evidence),
            lexical_top_source=lexical[0].source_url if lexical else None,
            hybrid_top_source=result.evidence[0].source_url if result.evidence else None,
            comparison_result='PASS' if result.evidence and result.evidence[0].source_url==case['expected_source'] else 'EXPECTED_IN_TOP_5',
            retrieved=[{'source_url':e.source_url,'section':e.section_title,'method':e.retrieval_method,'score':e.score} for e in result.evidence]))
    negatives=[]
    for query in ['lunar delivery guarantee','cryptocurrency refund reimbursement','employee pension contributions']:
        result=retrieve_policy_knowledge(query,conn=conn,embedding_client=embedding_client)
        negatives.append(dict(query=query,status=result.status,passed=result.status=='INSUFFICIENT_EVIDENCE'))
    methods={r['method'] for case in results for r in case['retrieved']}
    return dict(mode='LIVE_POSTGRES_HYBRID' if 'hybrid' in methods else 'LIVE_POSTGRES_TEXT_ONLY',
                semantic_evaluation='HYBRID_RESULTS_PRESENT_REVIEW_REQUIRED' if 'hybrid' in methods else 'NOT_RUN_NO_REAL_SEMANTIC_RESULTS',
                cases=results,negative_cases=negatives,source_correct_at_5=sum(r['source_correct_at_5'] for r in results),total=len(results))

if __name__ == '__main__':
    conn=psycopg2.connect(settings.supabase_db_url,connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        report=evaluate(conn)
        write(ROOT/'reports/phase_2d_retrieval_evaluation.json',report)
        print({k:v for k,v in report.items() if k not in ('cases','negative_cases')})
        print([{'query':c['question'],'found':c['source_correct_at_5']} for c in report['cases']])
        print(report['negative_cases'])
    finally:
        conn.rollback(); conn.close()
