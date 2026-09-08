import unittest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.app.api.deps import verify_tool_secret
from backend.app.api.routes_catalogue import get_public_catalogue, router
from backend.app.schemas.public_catalogue import CatalogueFacets, PublicProduct, PublicProductList, StyledEditResponse
from backend.app.services.public_catalogue_service import PublicCatalogueService


PRODUCT = {
    "product_id": "product-1", "name": "BLACK MIDI DRESS", "department": "WOMAN",
    "category": "Dresses", "description": "Evening dress", "price": 79.9,
    "currency": "USD", "colors": ["Black"], "sizes": ["M"],
    "image_urls": ["https://example.test/dress.jpg"], "available": True,
    "is_on_sale": False, "source": "catalogue",
}


class FakeRepo:
    def list_public_products(self, **kwargs):
        self.arguments = kwargs
        return 1, [PRODUCT]


class FakeService:
    def products(self, **kwargs):
        return PublicProductList(items=[PublicProduct(**PRODUCT)], total=1, limit=kwargs["limit"], offset=kwargs["offset"], has_more=False)

    def product(self, product_id):
        return PublicProduct(**PRODUCT) if product_id == "product-1" else None

    def facets(self):
        return CatalogueFacets(departments=["WOMAN"], categories=["Dresses"], colors=["Black"], price_min=79.9, price_max=79.9, total_products=1)

    def styled_edit(self, limit=8):
        return StyledEditResponse(items=[PublicProduct(**PRODUCT)])


class PublicCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_public_catalogue] = lambda: FakeService()
        cls.client = TestClient(app)

    def test_public_products_need_no_secret(self):
        response = self.client.get("/v1/catalogue/products?q=black%20dresses")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["name"], "BLACK MIDI DRESS")

    def test_limit_is_capped(self):
        self.assertEqual(self.client.get("/v1/catalogue/products?limit=61").status_code, 422)

    def test_detail_facets_and_styled_edit_are_public(self):
        self.assertEqual(self.client.get("/v1/catalogue/products/product-1").status_code, 200)
        self.assertEqual(self.client.get("/v1/catalogue/facets").json()["total_products"], 1)
        self.assertEqual(len(self.client.get("/v1/catalogue/styled-edit").json()["items"]), 1)

    def test_search_normalizes_plural_color_and_price(self):
        repo = FakeRepo()
        service = PublicCatalogueService(None, repo=repo)
        result = service.products(query="black party dresses under 100")
        self.assertEqual(result.total, 1)
        self.assertIsNone(repo.arguments["query"])
        self.assertEqual(repo.arguments["color"], "black")
        self.assertEqual(repo.arguments["product_type"], "dress")
        self.assertEqual(repo.arguments["occasion"], "party")
        self.assertEqual(repo.arguments["max_price"], 100.0)

    def test_private_gateway_auth_still_rejects_missing_secret(self):
        with self.assertRaises(HTTPException) as error:
            verify_tool_secret(None)
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
