"""Catalogue Domain Service."""

import re
from dataclasses import dataclass
from typing import List, Optional
import psycopg2.extensions
from backend.app.schemas.catalogue import (
    SearchProductsInput,
    SearchProductsOutput,
    ProductCard,
    GetProductDetailsInput,
    ProductDetailsOutput,
    CompareProductsInput,
    CompareProductsOutput,
    ProductComparisonItem,
)
from backend.app.schemas.common import ErrorCode, ToolError
from backend.app.repositories.catalogue_repo import CatalogueRepository


SEARCH_FILLER = {
    "a", "an", "find", "for", "i", "looking", "me", "need", "please",
    "search", "show", "some", "up", "to", "occasion", "wear",
}

PRODUCT_TYPES = {
    "blazer": ("blazer", "blazers"),
    "coat": ("coat", "coats", "overcoat", "overcoats"),
    "dress": ("dress", "dresses", "gown", "gowns"),
    "hoodie": ("hoodie", "hoodies", "hooded sweatshirt", "hooded sweatshirts"),
    "jacket": ("jacket", "jackets"),
    "jeans": ("jean", "jeans", "denim jeans"),
    "pants": ("pant", "pants", "trouser", "trousers", "slacks"),
    "shirt": ("shirt", "shirts", "blouse", "blouses"),
    "shoes": ("shoe", "shoes", "sneaker", "sneakers", "trainer", "trainers", "loafer", "loafers"),
    "skirt": ("skirt", "skirts"),
    "top": ("top", "tops", "tee", "tees", "t-shirt", "t-shirts"),
}
MATERIALS = ("cashmere", "cotton", "denim", "leather", "linen", "silk", "suede", "wool")
OCCASIONS = ("date night", "wedding", "bridal", "office", "business", "formal", "evening",
             "party", "casual", "vacation", "festival", "eid", "winter", "summer", "gym")
OCCASION_ALTERNATIVES = {
    "wedding": "elegant formal dresses that may suit a wedding",
    "bridal": "elegant white dresses that may suit a bridal occasion",
    "office": "polished tailoring for work",
    "business": "polished tailoring for work",
    "formal": "elegant occasion pieces",
    "evening": "elegant occasion pieces",
    "party": "statement styles for going out",
    "casual": "relaxed everyday pieces",
    "vacation": "lightweight seasonal pieces",
    "date night": "elegant going-out styles",
    "festival": "expressive casual styles",
    "eid": "elegant modest styles",
    "winter": "warm layered pieces",
    "summer": "lightweight seasonal pieces",
    "gym": "comfortable active styles",
}
GENDERS = {"woman": "WOMAN", "women": "WOMAN", "womens": "WOMAN", "female": "WOMAN",
           "man": "MAN", "men": "MAN", "mens": "MAN", "male": "MAN",
           "kid": "KIDS", "kids": "KIDS", "child": "KIDS", "children": "KIDS"}


@dataclass(frozen=True)
class SearchFacets:
    query: Optional[str]
    color: Optional[str]
    product_type: Optional[str]
    department: Optional[str]
    material: Optional[str]
    brand: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    occasion: Optional[str]
SEARCH_PLURALS = {
    "dresses": "dress", "shirts": "shirt", "jackets": "jacket",
    "tops": "top", "skirts": "skirt", "shoes": "shoe", "coats": "coat",
    "blazers": "blazer", "pants": "pant", "trousers": "trouser", "jeans": "jean",
}
SEARCH_COLORS = {
    "black", "white", "navy", "blue", "red", "green", "beige", "brown",
    "gray", "grey", "pink", "yellow", "orange", "purple",
}


class CatalogueService:
    """Domain service managing catalogue queries, faceted search, and comparisons."""

    def __init__(self, conn: psycopg2.extensions.connection):
        self.repo = CatalogueRepository(conn)
        from backend.app.rag.embeddings import get_embedding_client
        self.embedding_client = get_embedding_client()

    def search_products(self, input_data: SearchProductsInput) -> SearchProductsOutput:
        facets = self._extract_facets(input_data)
        semantic_vector = None
        if input_data.query and getattr(self, "embedding_client", None):
            semantic_vector = self.embedding_client.embed([input_data.query])[0]
        total, rows = self.repo.search_products(
            query=facets.query,
            semantic_vector=semantic_vector,
            department=facets.department,
            category_id=input_data.category_id,
            category=input_data.category,
            product_type=facets.product_type,
            min_price=facets.min_price,
            max_price=facets.max_price,
            color=facets.color,
            size=input_data.size,
            material=facets.material,
            brand=facets.brand,
            occasion=facets.occasion,
            on_sale=input_data.on_sale,
            limit=input_data.limit,
        )
        cards = [ProductCard(**r) for r in rows]
        fallback = None
        if facets.occasion and not cards:
            alternative = OCCASION_ALTERNATIVES[facets.occasion]
            requested = f"{facets.occasion}-specific"
            fallback = f"I couldn't find {requested} pieces in our current collection. I can show {alternative}."
        return SearchProductsOutput(
            total_matching=total,
            returned_count=len(cards),
            products=cards,
            occasion=facets.occasion,
            fallback_message=fallback,
        )

    @staticmethod
    def _normalize_search(query: Optional[str], color: Optional[str]):
        """Separate authoritative facets from conversational catalogue text."""
        if not query or not query.strip():
            return query, color
        tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", query.casefold())
        normalized_color = color.strip() if color and color.strip() else next(
            (token for token in tokens if token in SEARCH_COLORS), None
        )
        color_token = normalized_color.casefold() if normalized_color else None
        terms = [
            SEARCH_PLURALS.get(token, token)
            for token in tokens
            if token not in SEARCH_FILLER
            and token != color_token
            and not token.replace(".", "", 1).isdigit()
        ]
        return " ".join(terms) or None, normalized_color

    @classmethod
    def _extract_facets(cls, data: SearchProductsInput) -> SearchFacets:
        text = (data.query or "").casefold().replace("'", "")
        tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text)
        color = data.color.strip() if data.color and data.color.strip() else next(
            (token for token in tokens if token in SEARCH_COLORS), None)
        product_type = data.product_type.strip().casefold() if data.product_type else None
        matched_aliases = set()
        if not product_type:
            if re.search(r"\bdress\s+shoes?\b", text):
                product_type, matched_aliases = "shoes", {"shoe", "shoes"}
            else:
                matches = [(alias, canonical) for canonical, aliases in PRODUCT_TYPES.items()
                           for alias in aliases if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text)]
                if matches:
                    alias, product_type = max(matches, key=lambda item: len(item[0]))
                    matched_aliases.update(re.findall(r"[a-z]+", alias))
        department = data.department
        if not department:
            department = next((value for token, value in GENDERS.items()
                               if re.search(rf"(?<!\w){token}(?!\w)", text)), None)
        material = data.material.strip() if data.material else next(
            (value for value in MATERIALS if value in tokens), None)
        brand = data.brand.strip() if data.brand else next(
            (value for value in ("zara", "nexgen") if value in tokens), None)
        occasion = data.occasion.strip().casefold() if data.occasion else next(
            (value for value in OCCASIONS if re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text)), None)
        min_price, max_price = data.min_price, data.max_price
        between = re.search(r"(?:between|from)\s*\$?(\d+(?:\.\d+)?)\s*(?:and|to)\s*\$?(\d+(?:\.\d+)?)", text)
        under = re.search(r"(?:under|below|less than|max(?:imum)?(?: of)?)\s*\$?(\d+(?:\.\d+)?)", text)
        over = re.search(r"(?:over|above|more than|min(?:imum)?(?: of)?)\s*\$?(\d+(?:\.\d+)?)", text)
        if between:
            min_price = min_price if min_price is not None else float(between.group(1))
            max_price = max_price if max_price is not None else float(between.group(2))
        else:
            if under and max_price is None: max_price = float(under.group(1))
            if over and min_price is None: min_price = float(over.group(1))
        removed = set(SEARCH_FILLER) | matched_aliases | set(GENDERS) | set(MATERIALS)
        if color: removed.add(color.casefold())
        if brand: removed.add(brand.casefold())
        if occasion: removed.update(re.findall(r"[a-z]+", occasion))
        terms = [SEARCH_PLURALS.get(token, token) for token in tokens
                 if token not in removed and not token.replace(".", "", 1).isdigit()
                 and token not in {"between", "from", "and", "below", "less", "than", "max", "maximum",
                                   "of", "over", "above", "more", "min", "minimum"}]
        return SearchFacets(" ".join(terms) or None, color, product_type, department,
                            material, brand, min_price, max_price, occasion)

    def get_product_details(self, input_data: GetProductDetailsInput) -> ProductDetailsOutput:
        prod = self.repo.get_product_details(input_data.product_id)
        if not prod:
            raise ValueError(f"Product '{input_data.product_id}' not found.")
        return ProductDetailsOutput(**prod)

    def compare_products(self, input_data: CompareProductsInput) -> CompareProductsOutput:
        products = self.repo.get_products_by_ids(input_data.product_ids)
        items = [ProductComparisonItem(**p) for p in products]
        return CompareProductsOutput(
            compared_count=len(items),
            products=items
        )

