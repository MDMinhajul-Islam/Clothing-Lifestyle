from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class PolicyQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    policy_type: str | None = Field(None, max_length=80)
    section_title: str | None = Field(None, max_length=300)
    market: Literal['US'] = 'US'
    locale: Literal['en'] = 'en'
    limit: int = Field(5, ge=1, le=20)

    @field_validator('query')
    @classmethod
    def nonempty_query(cls, value):
        if not value.strip():
            raise ValueError('Query cannot be blank')
        return value.strip()

class PolicyEvidence(BaseModel):
    chunk_id: str
    knowledge_id: str
    source_id: str
    chunk_text: str
    source_url: str
    source_hash: str
    policy_type: str
    section_title: str
    market: Literal['US'] = 'US'
    locale: Literal['en'] = 'en'
    score: float
    retrieval_method: Literal['text', 'hybrid', 'semantic']
    effective_date: datetime | None
    retrieved_at: datetime

class PolicyResult(BaseModel):
    status: Literal['EVIDENCE_FOUND', 'INSUFFICIENT_EVIDENCE', 'RETRIEVAL_UNAVAILABLE']
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    message: str | None = None
    semantic_status: str
    requires_policy_rule_reconciliation: bool = True
