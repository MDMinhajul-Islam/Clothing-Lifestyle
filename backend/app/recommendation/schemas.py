from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator

ProductId = Annotated[str, Field(pattern=r'^zara-us:\d{8}$')]

class RecommendationFilters(BaseModel):
    target_category: str | None = Field(None, max_length=120)
    department: str | None = Field(None, max_length=40)
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    size: str | None = Field(None, max_length=40)
    color: str | None = Field(None, max_length=80)
    limit: int = Field(8, ge=1, le=20)

    @field_validator('target_category', 'department', 'size', 'color')
    @classmethod
    def strip_optional(cls, value):
        return value.strip() if value and value.strip() else None

    @field_validator('max_price')
    @classmethod
    def ordered_prices(cls, value, info):
        minimum = info.data.get('min_price')
        if value is not None and minimum is not None and value < minimum:
            raise ValueError('max_price must be greater than or equal to min_price')
        return value

class SemanticProductSearchInput(RecommendationFilters):
    query: str = Field(min_length=1, max_length=500)

    @field_validator('query')
    @classmethod
    def nonblank_query(cls, value):
        if not value.strip():
            raise ValueError('query cannot be blank')
        return value.strip()

class ReferenceRecommendationInput(RecommendationFilters):
    reference_product_id: ProductId

class FindSimilarProductsInput(ReferenceRecommendationInput):
    pass

class RecommendMatchingProductsInput(ReferenceRecommendationInput):
    pass

class RecommendationItem(BaseModel):
    product_id: ProductId
    name: str
    department: str
    price: float
    currency: str
    categories: list[str]
    colors: list[str]
    sizes: list[str]
    is_on_sale: bool
    primary_image_url: str | None = None
    semantic_score: float = Field(ge=-1, le=1)
    recommendation_score: float = Field(ge=0, le=1)
    availability_verified: bool
    availability_status: str
    availability_origin: Literal['synthetic_operational_layer']
    reason_codes: list[str]

class RecommendationOutput(BaseModel):
    reference_product_id: ProductId | None = None
    total_results: int
    results: list[RecommendationItem]
    embedding_provider: Literal['local_sentence_transformers'] = 'local_sentence_transformers'
    embedding_model: Literal['sentence-transformers/all-MiniLM-L6-v2'] = 'sentence-transformers/all-MiniLM-L6-v2'
    embedding_version: Literal['v1'] = 'v1'
    availability_is_synthetic: Literal[True] = True
