"""Offline health/lifecycle regression checks; never connect to a live database."""
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.deps import get_db
from backend.app.api.routes_meta import router
from backend.app.main import app, lifespan


class TestProductionHealth(unittest.TestCase):
    def setUp(self):
        self.web = FastAPI()
        self.web.include_router(router)

    def test_liveness_does_not_acquire_database(self):
        def unavailable():
            raise RuntimeError("database unavailable")

        self.web.dependency_overrides[get_db] = unavailable
        with TestClient(self.web, raise_server_exceptions=False) as client:
            self.assertEqual(client.get("/livez").json(), {"status": "alive"})
            self.assertEqual(client.get("/livez").status_code, 200)
            self.assertEqual(client.get("/health").status_code, 500)

    def test_existing_readiness_contract_still_checks_database(self):
        conn = MagicMock()
        self.web.dependency_overrides[get_db] = lambda: conn
        with TestClient(self.web) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(response.json()["database"], "connected")
        conn.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1;")


class TestStartupLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_failed_model_startup_closes_pool_and_identifies_stage(self):
        with patch("backend.app.main.init_db_pool"), \
             patch("backend.app.main.close_db_pool") as close, \
             patch("backend.app.main.initialize_embedding_client", side_effect=RuntimeError("private detail")):
            with self.assertLogs("tool_gateway.main", level="INFO") as captured:
                with self.assertRaises(RuntimeError):
                    async with lifespan(app):
                        self.fail("Failed initialization must not yield readiness")
            close.assert_called_once_with()
        output = "\n".join(captured.output)
        self.assertIn("Startup failed stage=embedding_model error_type=RuntimeError", output)
        self.assertNotIn("private detail", output)

    async def test_successful_startup_preserves_warmup_and_cleanup(self):
        encoder = MagicMock(provider="local", model="test", device="cpu")
        with patch("backend.app.main.init_db_pool") as init, \
             patch("backend.app.main.close_db_pool") as close, \
             patch("backend.app.main.initialize_embedding_client", return_value=encoder):
            async with lifespan(app):
                init.assert_called_once_with()
                encoder.embed.assert_called_once_with(["NexGen voice commerce startup warmup"])
                close.assert_not_called()
            close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
